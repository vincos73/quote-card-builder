"""Portable files keep the local/web wire contract and exclude base content."""
import copy
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
TESTS_DIR = ROOT / "tests"
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from tests.test_card_review_server import manifest
from tests.test_ribbon_sessions import ribbon_manifest
import portable_projects
import card_review_server
import mcp_quote_card


class PortableProjectsTests(unittest.TestCase):
    def setUp(self):
        self.native = manifest()
        self.native["brand"]["font"] = {
            "family": "Barlow",
            "regular_path": str(ROOT / "assets/card-editor/fonts/Barlow-Regular.ttf"),
        }

    def test_personal_base_and_project_share_web_schemas_and_content_boundary(self):
        base = portable_projects.export_base("Test base", self.native, ROOT)
        self.assertEqual({"schema", "schemaVersion", "name", "design"}, set(base))
        self.assertEqual("qcb-personal-base", base["schema"])
        self.assertEqual(2, base["schemaVersion"])
        wire = str(base)
        self.assertNotIn(self.native["content"]["text"], wire)
        label = self.native["content"].get("attribution", {}).get("label", "")
        if label:
            self.assertNotIn(label, wire)
        for forbidden in ("ranges", "evidence_status", "source", "alt_text"):
            self.assertNotIn(forbidden, wire)
        project = portable_projects.export_project("Test project", self.native, ROOT)
        self.assertEqual("qcb-card-project", project["schema"])
        self.assertEqual(1, project["schemaVersion"])
        self.assertIn("text", project["draft"])
        self.assertIn("styles", project["draft"])

    def test_import_base_and_project_materialize_font_and_roundtrip_editor_fields(self):
        project = portable_projects.export_project("Test", self.native, ROOT)
        with tempfile.TemporaryDirectory() as directory:
            restored = portable_projects.import_design(project, Path(directory), copy.deepcopy(self.native), project=True)
            self.assertTrue(Path(restored["brand"]["font"]["regular_path"]).is_file())
            self.assertEqual(self.native["content"]["text"], restored["content"]["text"])
            self.assertEqual(self.native["formats"][0]["lines"], restored["formats"][0]["lines"])
            base = portable_projects.export_base("Base", self.native, ROOT)
            reused = portable_projects.import_design(base, Path(directory), copy.deepcopy(self.native), project=False)
            self.assertEqual(self.native["content"], reused["content"])

    def test_export_uses_unsaved_editor_payload_and_active_format(self):
        draft = {
            "base_revision": self.native["revision"], "text": "Edited quote before generate",
            "transformation": "EDITED", "evidence_status": "UNVERIFIED",
            "attribution": {"label": "Current author", "role": "author"},
            "alt_text": "Current alt", "styles": [{"start": 0, "end": 6, "type": "bold"}], "emphasis": "",
            "presentation": {**self.native["presentation"], "logo_mode": "hidden"},
            "formats": copy.deepcopy(self.native["formats"]), "palette": self.native["brand"]["colors"],
        }
        draft["formats"][0]["text_scale"] = .84
        draft["formats"][0]["lines"] = [draft["text"]]
        draft["formats"].append({"id": "1x1", "width": 1440, "height": 1440, "lines": [draft["text"]],
                                 "text_scale": .91, "vertical_position": "upper"})
        edited = card_review_server.validate_draft(draft, self.native)
        project = portable_projects.export_project("Current", edited, ROOT, "1x1")
        self.assertEqual("Edited quote before generate", project["draft"]["text"])
        self.assertEqual("Current author", project["draft"]["attribution"])
        self.assertEqual("Current alt", project["draft"]["alt_text"])
        self.assertEqual(.91, project["draft"]["text_scale"])
        base = portable_projects.export_base("Current", edited, ROOT, "1x1")
        self.assertEqual("1x1", base["design"]["format"])
        self.assertEqual("hidden", base["design"]["logo_mode"])

    def test_web_project_without_kit_roundtrips_through_local_and_renders_identically(self):
        source = ribbon_manifest()
        source["source"] = {"title": "Reviewed source", "locator": "section 3"}
        raw_text = "🌱 Uno\n\nidee crescono."
        source["content"].update(text="🌱 Uno idee crescono.", styles=[
            {"start": 6, "end": 10, "type": "highlight"},
            {"start": 6, "end": 10, "type": "size", "scale": 1.35}],
                                 attribution={"label": "Autrice", "role": "author"}, alt_text="Testo a capo")
        source["formats"][0]["lines"] = ["🌱 Uno", "", "idee crescono."]
        source["presentation"].update(quote_font_size=80, author_font_size=26)
        web_draft = {
            "text": raw_text, "lines": ["🌱 Uno", "", "idee crescono."], "attribution": "Autrice",
            "format": "4x5", "direction": source["direction"], "graphic_mode": "auto",
            "graphic_variant": "default", "graphic_seed": 41, "logo_mode": "hidden", "text_scale": 1,
            "vertical_position": "center", "palette": {"name": "Test", "colors": source["brand"]["colors"]},
            "brand_kit": None, "visual_grammar": "ribbons", "composition": source["presentation"]["composition"],
            "quote_font_size": 80, "author_font_size": 26,
            "styles": [{"start": 7, "end": 11, "type": "highlight"},
                       {"start": 7, "end": 11, "type": "size", "scale": 1.35}], "alt_text": "Testo a capo",
            "transformation": "EDITED", "evidence_status": "UNVERIFIED",
        }
        web_render = mcp_quote_card.preview_quote_card(web_draft, ROOT)
        self.assertTrue(web_render["rendered"], web_render["errors"])
        portable = {"schema": "qcb-card-project", "schemaVersion": 1, "name": "Web project", "draft": web_draft}
        with tempfile.TemporaryDirectory() as directory:
            imported = portable_projects.import_design(portable, Path(directory), source, project=True)
            self.assertEqual("Barlow", imported["brand"]["font"]["family"])
            self.assertIn("/assets/card-editor/fonts/Barlow-Regular.ttf", imported["brand"]["font"]["regular_path"])
            self.assertEqual("🌱 Uno idee crescono.", imported["content"]["text"])
            self.assertEqual([{"start": 6, "end": 10, "type": "highlight"},
                              {"start": 6, "end": 10, "type": "size", "scale": 1.35}], imported["content"]["styles"])
            local_project = portable_projects.export_project("Local export", imported, ROOT)
            self.assertEqual(raw_text, local_project["draft"]["text"])
            self.assertEqual(web_draft["styles"], local_project["draft"]["styles"])
            self.assertEqual({"title": "Portable project", "locator": "user-supplied"}, local_project["editorial"]["source"])
            reimported = portable_projects.import_design(local_project, Path(directory) / "again", imported, project=True)
            self.assertEqual(local_project["editorial"]["source"], reimported["source"])
            local_render = mcp_quote_card.preview_quote_card(local_project["draft"], ROOT)
            local_manifest_render = card_review_server.render_preview(imported, ROOT)[0]["svg"]
        self.assertTrue(local_render["rendered"], local_render["errors"])
        self.assertEqual(web_render["svg"], local_render["svg"])
        self.assertEqual(web_render["svg"], local_manifest_render)
        self.assertEqual(web_render["palette"], local_render["palette"])
        self.assertEqual(web_render["composition"], local_render["composition"])
        self.assertEqual(80, local_render["quote_font_size"])
        self.assertEqual(26, local_render["author_font_size"])

        design_fields = {key: value for key, value in web_draft.items()
                         if key not in {"text", "lines", "attribution", "styles", "alt_text", "transformation", "evidence_status"}}
        web_base = {"schema": "qcb-personal-base", "schemaVersion": 2, "name": "Web base",
                    "design": {**design_fields, "brand_kit": None}}
        base_web_draft = {**design_fields, "text": raw_text, "lines": web_draft["lines"],
                          "styles": [], "attribution": "Autrice"}
        base_web_render = mcp_quote_card.preview_quote_card(base_web_draft, ROOT)
        with tempfile.TemporaryDirectory() as directory:
            imported_base = portable_projects.import_design(web_base, Path(directory), source, project=False)
            exported_base = portable_projects.export_base("Local base", imported_base, ROOT)
            base_roundtrip_draft = {**exported_base["design"], "text": raw_text, "lines": web_draft["lines"],
                                    "styles": [], "attribution": "Autrice"}
            base_local_render = mcp_quote_card.preview_quote_card(base_roundtrip_draft, ROOT)
        self.assertTrue(base_web_render["rendered"], base_web_render["errors"])
        self.assertTrue(base_local_render["rendered"], base_local_render["errors"])
        self.assertEqual(base_web_render["svg"], base_local_render["svg"])

    def test_custom_kit_with_svg_logo_survives_local_import_and_export(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            native = copy.deepcopy(self.native)
            logo = root / "logo.svg"
            logo.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><circle cx="5" cy="5" r="4"/></svg>')
            native["brand"]["logo"] = {"dark_path": str(logo), "light_path": str(logo)}
            font = root / "Barlow-Regular.ttf"
            shutil.copy2(ROOT / "assets/card-editor/fonts/Barlow-Regular.ttf", font)
            native["brand"]["font"] = {"family": "Barlow", "regular_path": str(font)}
            base = portable_projects.export_base("Custom", native, root)
            restored = portable_projects.import_design(base, root / "assets", self.native, project=False)
            exported = portable_projects.export_base("Custom", restored, root)
        self.assertEqual("image/svg+xml", exported["design"]["brand_kit"]["logo"]["mime_type"])
        self.assertIn("regular", exported["design"]["brand_kit"]["font"])


if __name__ == "__main__":
    unittest.main()
