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
    def test_repeated_style_apply_keeps_the_first_session_palette_for_reset(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); manifest_path = root / "manifest.json"; store = root / "styles.json"
            current = manifest(); original_palette = copy.deepcopy(current["brand"]["colors"])
            style_b = copy.deepcopy(current); style_b["brand"]["colors"]["primary"] = "#123456"
            style_c = copy.deepcopy(current); style_c["brand"]["colors"]["primary"] = "#654321"
            saved_b = STYLES.save_style("Bosco", style_b, path=store)
            saved_c = STYLES.save_style("Notte", style_c, path=store)
            manifest_path.write_text(json.dumps(current), encoding="utf-8")
            server, token = SERVER.create_server(manifest_path, root / "session", style_store=store)
            thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
            try:
                endpoint = f"http://127.0.0.1:{server.server_address[1]}"
                def post(path, body):
                    request = Request(f"{endpoint}{path}?token={token}", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}, method="POST")
                    with urlopen(request) as response: return json.loads(response.read().decode())
                def draft(item):
                    return {"base_revision": item["revision"], "text": item["content"]["text"], "transformation": item["content"]["transformation"], "evidence_status": item["content"]["evidence_status"], "attribution": item["content"]["attribution"], "emphasis": item["content"]["emphasis"], "styles": item["content"]["styles"], "styles_customized": True, "presentation": item["presentation"], "formats": item["formats"], "alt_text": item["content"]["alt_text"]}
                after_b = post("/api/styles/apply", {"id": saved_b["id"], "draft": draft(current)})
                after_c = post("/api/styles/apply", {"id": saved_c["id"], "draft": draft(after_b)})
                self.assertEqual("#654321", after_c["brand"]["colors"]["primary"])
                self.assertEqual(original_palette, after_c["palette_initial"])
                with urlopen(f"{endpoint}/api/session?token={token}") as response: reopened = json.loads(response.read().decode())
                self.assertEqual("#654321", reopened["brand"]["colors"]["primary"])
                self.assertEqual(original_palette, reopened["palette_initial"])
            finally:
                server.shutdown(); server.server_close(); thread.join(timeout=2)

    def test_style_application_reapplies_saved_palette_and_keeps_reset_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); store = root / "styles.json"
            source = manifest()
            style = copy.deepcopy(source)
            style["brand"]["name"] = "Style identity"
            style["brand"]["colors"]["primary"] = "#654321"
            saved = STYLES.save_style("Identity", style, path=store)
            draft = copy.deepcopy(source)
            draft["brand"]["colors"] = {"primary": "#123456", "accent": "#E3F4FF", "background": "#FEFDFB", "text": "#323232"}
            draft["palette_initial"] = copy.deepcopy(source["brand"]["colors"])
            applied = STYLES.apply_style(saved["id"], draft, source, store, root)
            self.assertEqual("Style identity", applied["brand"]["name"])
            self.assertEqual(style["brand"]["colors"], applied["brand"]["colors"])
            self.assertEqual(draft["palette_initial"], applied["palette_initial"])
            self.assertEqual(draft["content"], applied["content"])
            self.assertEqual(draft["formats"], applied["formats"])

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

    def test_gradient_save_apply_and_reopen_preserves_content_across_three_formats(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); manifest_path = root / "manifest.json"; style_store = root / "styles.json"
            current = manifest()
            current["direction"] = "editorial"
            current["presentation"]["graphic_variant"] = "gradient"
            current["presentation"]["graphic_seed"] = 999999
            text = current["content"]["text"]
            current["formats"] = [
                {"id": "4x5", "width": 1440, "height": 1800, "lines": [text], "text_scale": 1.0, "vertical_position": "center"},
                {"id": "1x1", "width": 1440, "height": 1440, "lines": [text], "text_scale": 0.94, "vertical_position": "upper"},
                {"id": "9x16", "width": 1080, "height": 1920, "lines": [text], "text_scale": 0.88, "vertical_position": "lower"},
            ]
            manifest_path.write_text(json.dumps(current), encoding="utf-8")
            server, token = SERVER.create_server(manifest_path, root / "session", style_store=style_store)
            thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
            try:
                endpoint = f"http://127.0.0.1:{server.server_address[1]}"

                def post(path, body):
                    request = Request(f"{endpoint}{path}?token={token}", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}, method="POST")
                    with urlopen(request) as response: return json.loads(response.read().decode())

                draft = {
                    "base_revision": 1,
                    "text": text,
                    "transformation": current["content"]["transformation"],
                    "evidence_status": current["content"]["evidence_status"],
                    "attribution": current["content"]["attribution"],
                    "emphasis": current["content"]["emphasis"],
                    "styles": current["content"]["styles"],
                    "styles_customized": True,
                    "presentation": current["presentation"],
                    "formats": current["formats"],
                    "alt_text": current["content"]["alt_text"],
                }
                saved_response = post("/api/styles", {"name": "Gradient Editorial", "draft": draft})
                saved_id = saved_response["saved_style_id"]

                # Apply the saved visual identity to a genuinely changed draft.
                text = "Nuove parole da preservare."
                draft = copy.deepcopy(draft)
                draft.update(text=text, emphasis="", attribution={"label": "Nuova fonte", "role": "author"},
                             styles=[{"start": 0, "end": 5, "type": "italic"}])
                for item in draft["formats"]:
                    item["lines"] = ["Nuove parole", "da preservare."]
                draft["presentation"].update(graphic_variant="cutouts", graphic_seed=7)
                applied = post("/api/styles/apply", {"id": saved_id, "draft": draft})
                self.assertEqual("gradient", applied["presentation"]["graphic_variant"])
                self.assertEqual(999999, applied["presentation"]["graphic_seed"])
                self.assertEqual(text, applied["content"]["text"])
                self.assertEqual(draft["attribution"], applied["content"]["attribution"])
                self.assertEqual(draft["styles"], applied["content"]["styles"])
                self.assertEqual(draft["formats"], applied["formats"])

                with urlopen(f"{endpoint}/api/session?token={token}") as response:
                    reopened = json.loads(response.read().decode())
                self.assertEqual(2, reopened["revision"])
                self.assertEqual("gradient", reopened["presentation"]["graphic_variant"])
                self.assertEqual(999999, reopened["presentation"]["graphic_seed"])
                self.assertEqual(text, reopened["content"]["text"])
                self.assertEqual(draft["attribution"], reopened["content"]["attribution"])
                self.assertEqual(draft["styles"], reopened["content"]["styles"])
                self.assertEqual(draft["formats"], reopened["formats"])
            finally:
                server.shutdown(); server.server_close(); thread.join(timeout=2)


if __name__ == "__main__": unittest.main()
