"""Local-editor proof and reusable-base coverage for Urban Xerox."""

import copy
import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import Request, urlopen

from tests.test_card_review_server import SERVER, manifest as legacy_manifest
import saved_styles
from urban_artwork import xerox_font
from grammar_sessions import complete_ribbon_formats
from urban_grammar import demo_urban_compositions

ROOT = Path(__file__).parents[1]


def urban_manifest():
    value = legacy_manifest()
    value["state"] = "candidato_selezionato"
    value["direction"] = "editorial"
    value["brand"]["font"] = {"family": "Arial"}
    value["presentation"] = {
        "logo_mode": "auto", "graphic_mode": "auto", "graphic_variant": "default",
        "graphic_seed": 0, "output_mode": "4x5", "visual_grammar": "urban",
        "composition": demo_urban_compositions(value["content"]["text"])[0],
    }
    value["formats"] = complete_ribbon_formats(value["formats"], value["content"]["text"])
    return value


class LocalUrbanXeroxTests(unittest.TestCase):
    def test_preset_preview_keeps_geometric_gallery_and_xerox_base_reuses(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = urban_manifest()
            self.assertEqual([], SERVER.validate_manifest(source))
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(source), encoding="utf-8")
            server, token = SERVER.create_server(manifest_path, root / "session")
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                endpoint = f"http://127.0.0.1:{server.server_address[1]}"

                def compositions(preset=None):
                    draft = {
                        "base_revision": 1,
                        "direction": "editorial",
                        "presentation": {
                            **copy.deepcopy(source["presentation"]),
                            "visual_grammar": "urban",
                        },
                    }
                    body = {"draft": draft}
                    if preset:
                        body["preset"] = preset
                    request = Request(
                        f"{endpoint}/api/compositions?token={token}",
                        data=json.dumps(body).encode("utf-8"),
                        headers={"Content-Type": "application/json"},
                        method="POST",
                    )
                    with urlopen(request) as response:
                        return json.loads(response.read().decode("utf-8"))

                geometric = compositions()
                self.assertEqual(3, len(geometric["model"]["composition_candidates"]))
                self.assertTrue(all("artwork_id" not in item for item in geometric["model"]["composition_candidates"]))

                xerox = compositions("xerox")
                model = xerox["model"]
                composition = model["presentation"]["composition"]
                self.assertEqual("urban-xerox-lime-v1", composition["artwork_id"])
                self.assertEqual(xerox_font(), model["brand"]["font"])
                self.assertEqual(1, len(model["composition_candidates"]))
                self.assertIn("data:image/png;base64,", xerox["previews"][0]["svg"])
                feedback = SERVER.approval_feedback(model, 1)
                self.assertEqual(xerox_font(), feedback["brand"]["font"])

                approved_manifest = root / "approved-manifest.json"
                approved_manifest.write_text(json.dumps(source), encoding="utf-8")
                approval_session = root / "approval-session"
                approval_session.mkdir()
                feedback_path = approval_session / "feedback.json"
                (approval_session / "session-state.json").write_text(json.dumps({
                    "manifest": str(approved_manifest.resolve()),
                    "feedback_path": str(feedback_path.resolve()),
                    "last_feedback_id": None,
                    "applied_feedback_id": None,
                }), encoding="utf-8")
                SERVER.record_and_apply_feedback(approved_manifest, approval_session, feedback)
                approved = json.loads(approved_manifest.read_text(encoding="utf-8"))
                self.assertEqual(xerox_font(), approved["brand"]["font"])

                branded = copy.deepcopy(source)
                branded["brand"]["font"] = {"family": "Brand Display"}
                branded_presentation = copy.deepcopy(model["presentation"])
                branded_draft = SERVER.validate_draft({
                    "base_revision": 1,
                    "presentation": branded_presentation,
                }, branded)
                self.assertEqual({"family": "Brand Display"}, branded_draft["brand"]["font"])
                self.assertNotIn("font", SERVER.approval_feedback(branded_draft, 1)["brand"])

                style_store = root / "styles.json"
                saved = saved_styles.save_style(
                    "Urban Xerox", model, path=style_store, base_dir=ROOT,
                )
                reopened = saved_styles.get_style(saved["id"], style_store)
                reused = saved_styles.apply_style(
                    saved["id"], model, model, path=style_store, base_dir=ROOT,
                    reuse_mode="card", text=model["content"]["text"],
                )
                self.assertEqual(composition, reopened["presentation"]["composition"])
                self.assertEqual(xerox_font(), reopened["brand"]["font"])
                self.assertEqual(composition, reused["presentation"]["composition"])
                self.assertEqual(xerox_font(), reused["brand"]["font"])
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

    def test_editor_exposes_a_separate_urban_xerox_choice(self):
        html = (ROOT / "assets/card-editor/index.html").read_text(encoding="utf-8")
        app = (ROOT / "assets/card-editor/app.js").read_text(encoding="utf-8")
        self.assertIn('id="urban-xerox-choice"', html)
        self.assertIn("Lo sfondo Xerox mantiene i colori fissi", html)
        self.assertIn("requestCompositions('xerox')", app)
        self.assertIn("urban-xerox-lime-v1", app)
        self.assertIn("els.compositionRefresh.addEventListener('click', () => requestCompositions());", app)
        self.assertIn("xeroxChoice.hidden = !urban", app)
        self.assertIn("xeroxHelp.hidden = !urban", app)


if __name__ == "__main__":
    unittest.main()
