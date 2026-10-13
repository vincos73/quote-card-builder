import copy
import importlib.util
import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("card_review_server", ROOT / "scripts" / "card_review_server.py")
SERVER = importlib.util.module_from_spec(spec); assert spec and spec.loader; spec.loader.exec_module(SERVER)
styles_spec = importlib.util.spec_from_file_location("saved_styles", ROOT / "scripts" / "saved_styles.py")
STYLES = importlib.util.module_from_spec(styles_spec); assert styles_spec and styles_spec.loader; styles_spec.loader.exec_module(STYLES)


def manifest():
    text = "Una frase verificata."
    return {"schema_version":"0.4", "state":"contenuto_approvato", "revision":1,
            "content":{"text":text,"styles":[{"start":4,"end":10,"type":"bold"}],"styles_customized":True,"emphasis":"frase","alt_text":"alt","transformation":"VERBATIM","evidence_status":"VERIFIED","attribution":{"label":"Fonte","role":"publisher"}},
            "direction":"statement", "presentation":{"logo_mode":"auto","graphic_mode":"auto","graphic_variant":"default","graphic_seed":42,"output_mode":"all"},
            "formats":[{"id":"4x5","width":1440,"height":1800,"lines":[text],"text_scale":1.0,"vertical_position":"center"}],
            "brand":{"name":"Palette A","colors":{"primary":"#072743","accent":"#E3F4FF","background":"#FEFDFB","text":"#323232"},"font":{"family":"Arial"}},
            "source":{"title":"private"},"output":{}}


class SavedStylesHTTPTests(unittest.TestCase):
    def test_apply_preview_save_and_reopen_preserves_current_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); manifest_path = root / "manifest.json"; style_store = root / "styles.json"
            current = manifest(); manifest_path.write_text(json.dumps(current), encoding="utf-8")
            saved = STYLES.save_style("Reusable", current, path=style_store)
            changed = copy.deepcopy(current); changed["brand"]["name"] = "Palette B"; changed["brand"]["colors"]["primary"] = "#123456"
            STYLES.save_style("Reusable", changed, path=style_store)
            server, token = SERVER.create_server(manifest_path, root / "session", style_store=style_store)
            thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
            try:
                endpoint = f"http://127.0.0.1:{server.server_address[1]}"
                draft = {"base_revision":1,"text":"Una frase verificata.","transformation":"VERBATIM","evidence_status":"VERIFIED","attribution":{"label":"Fonte","role":"publisher"},"emphasis":"frase","styles":current["content"]["styles"],"styles_customized":True,"presentation":current["presentation"],"formats":current["formats"],"alt_text":"alt"}
                def post(path, body):
                    request = Request(f"{endpoint}{path}?token={token}", data=json.dumps(body).encode(), headers={"Content-Type":"application/json"}, method="POST")
                    with urlopen(request) as response: return json.loads(response.read().decode())
                applied = post("/api/styles/apply", {"id":saved["id"],"draft":draft})
                self.assertEqual("Palette B", applied["brand"]["name"]); self.assertEqual(42, applied["presentation"]["graphic_seed"]); self.assertEqual(2, applied["revision"])
                self.assertEqual("#123456", applied["brand"]["colors"]["primary"])
                self.assertEqual(current["brand"]["colors"], applied["palette_initial"])
                self.assertEqual(current["content"]["text"], applied["content"]["text"]); self.assertEqual(current["formats"][0]["lines"], applied["formats"][0]["lines"]); self.assertEqual(current["content"]["styles"], applied["content"]["styles"])
                editor = {"base_revision": applied["revision"], "text":applied["content"]["text"], "transformation":applied["content"]["transformation"],"evidence_status":applied["content"]["evidence_status"],"attribution":applied["content"]["attribution"],"emphasis":applied["content"].get("emphasis",""),"styles":applied["content"]["styles"],"styles_customized":True,"presentation":applied["presentation"],"formats":applied["formats"],"alt_text":"alt"}
                preview = post("/api/preview", editor); self.assertIn("previews", preview)
                post("/api/styles", {"name":"Reusable","draft":editor})
                with urlopen(f"{endpoint}/api/session?token={token}") as response: reopened = json.loads(response.read().decode())
                self.assertEqual("Palette B", reopened["brand"]["name"]); self.assertEqual(42, reopened["presentation"]["graphic_seed"]); self.assertEqual(2, reopened["revision"]); self.assertEqual(current["content"]["styles"], reopened["content"]["styles"])
                self.assertEqual("#123456", reopened["brand"]["colors"]["primary"])
                self.assertEqual(current["brand"]["colors"], reopened["palette_initial"])
            finally:
                server.shutdown(); server.server_close(); thread.join(timeout=2)


if __name__ == "__main__": unittest.main()
