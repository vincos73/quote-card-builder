"""Hybrid artwork must survive rendering, editor edits and portable reuse."""
import base64
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import mcp_quote_card as adapter
import portable_projects
import render_quote_card as renderer
from urban_artwork import XEROX_ARTWORK_ID, xerox_font
from urban_grammar import xerox_composition
from visual_grammars import demo_compositions, normalize_composition, variation_compositions

NS = {"s": "http://www.w3.org/2000/svg"}


class UrbanArtworkTests(unittest.TestCase):
    def test_only_registered_artwork_can_enter_a_scene(self):
        for reference in ("../secret.png", "https://example.com/a.png", "data:image/png;base64,eA==", {}, None):
            with self.subTest(reference=reference), self.assertRaises(ValueError):
                normalize_composition({**xerox_composition(), "artwork_id": reference})
        self.assertEqual(xerox_composition(), normalize_composition(xerox_composition()))
        self.assertNotIn("artwork_id", demo_compositions(grammar="urban")[0])

    def test_default_urban_embeds_original_image_and_keeps_source_offsets(self):
        text = "Le idee migliori nascono dalle persone."
        result = adapter.preview_quote_card({"text": text, "visual_grammar": "urban"})
        self.assertTrue(result["rendered"], result["errors"])
        root = ET.fromstring(result["svg"])
        image = root.find("s:image[@class='urban-artwork']", NS)
        self.assertIsNotNone(image)
        self.assertEqual((ROOT / "assets/urban/urban-xerox-lime-v1.png").read_bytes(),
                         base64.b64decode(image.get("href").split(",", 1)[1]))
        quote = root.findall("s:text[@class='quote']", NS)
        self.assertEqual(text.upper(), " ".join(node.text for node in quote))
        for node in quote:
            start, end = int(node.get("data-start")), int(node.get("data-end"))
            self.assertEqual(text[start:end].upper(), node.text)
        self.assertLess(len(json.dumps(result["composition"])), 2000)
        self.assertNotIn("base64", json.dumps(result["composition"]))

    def test_new_quotes_fit_all_formats_and_manual_size_is_preserved(self):
        texts = ["Le idee migliori nascono dalle persone.",
                 "Le idee crescono quando le persone si incontrano."]
        for text in texts:
            for fmt in ("4x5", "1x1", "9x16"):
                with self.subTest(text=text, fmt=fmt):
                    payload = {"text": text, "visual_grammar": "urban", "format": fmt,
                               "attribution": "Nome fornito"}
                    manifest, errors = adapter.build_manifest(payload, ROOT)
                    self.assertFalse(errors)
                    layout = renderer.urban_layout(manifest, ROOT)
                    self.assertTrue(layout["valid"], layout["warnings"])
                    self.assertEqual(text, " ".join(row["text"] for row in layout["rows"]))
                    manual = renderer.urban_layout(manifest, ROOT, render_options={"quote_font_size": 480})
                    self.assertEqual(480, manual["font_size"])
                    self.assertTrue(any(w["code"] == "quote_overflow" for w in manual["warnings"]))

    def test_uppercase_expansion_and_inline_size_preserve_editor_ranges(self):
        text = "Straße e città creano idee condivise."
        payload = {"text": text, "visual_grammar": "urban",
                   "styles": [{"start": 0, "end": 6, "type": "size", "scale": .8}]}
        result = adapter.preview_quote_card(payload)
        self.assertTrue(result["rendered"], result["errors"])
        rows = result["ribbon_layout"]["rows"]
        fragments = [fragment for row in rows for fragment in row["fragments"]]
        self.assertEqual("STRASSE", fragments[0]["text"])
        self.assertEqual((0, 6), (fragments[0]["start"], fragments[0]["end"]))
        self.assertAlmostEqual(result["ribbon_layout"]["font_size"] * .8, fragments[0]["font_size"])

    def test_portable_project_and_base_restore_the_same_artwork_font_and_content(self):
        text = "Le idee migliori nascono dalle persone."
        manifest, errors = adapter.build_manifest({"text": text, "visual_grammar": "urban"}, ROOT)
        self.assertFalse(errors)
        manifest["formats"] = [{"id": "4x5", **manifest["canvas"], "lines": [text],
                                "text_scale": 1.0, "vertical_position": "center"}]
        with tempfile.TemporaryDirectory() as directory:
            for is_project in (False, True):
                export = portable_projects.export_project if is_project else portable_projects.export_base
                portable = export("Xerox", manifest, ROOT)
                imported = portable_projects.import_design(portable, Path(directory), manifest, project=is_project)
                self.assertEqual(manifest["presentation"]["composition"], imported["presentation"]["composition"])
                self.assertEqual(XEROX_ARTWORK_ID, imported["presentation"]["composition"]["artwork_id"])
                self.assertEqual(Path(xerox_font()["regular_path"]).read_bytes(),
                                 Path(imported["brand"]["font"]["regular_path"]).read_bytes())
                self.assertEqual(text, imported["content"]["text"])
        reused = variation_compositions(xerox_composition(), "Una nuova frase da impaginare.")
        self.assertEqual([xerox_composition()], reused)

    def test_local_approval_persists_only_the_registered_default_font(self):
        from tests.test_apply_card_review import APPLIER, manifest as local_manifest
        original = local_manifest()
        original["brand"]["font"] = {"family": "Arial"}
        feedback = {"feedback_id": "xerox-1", "submitted_at": "2026-10-15T06:00:00Z",
                    "base_revision": 3, "action": "feedback", "editorial_responsibility": "user",
                    "content": {}, "formats": [], "overall_note": "",
                    "brand": {"colors": original["brand"]["colors"], "font": xerox_font()},
                    "presentation": {"visual_grammar": "urban", "composition": xerox_composition()}}
        APPLIER.validate_feedback(feedback, original)
        result = APPLIER.expected_manifest_after_feedback(original, feedback)
        self.assertEqual(xerox_font(), result["brand"]["font"])
        self.assertEqual("Arial", original["brand"]["font"]["family"])
        feedback["brand"]["font"] = {"family": "Xerox", "regular_path": "/tmp/arbitrary.ttf"}
        with self.assertRaises(APPLIER.ReviewError):
            APPLIER.validate_feedback(feedback, original)
        feedback["brand"]["font"] = xerox_font()
        original["brand"]["font"] = {"family": "Existing custom font"}
        with self.assertRaises(APPLIER.ReviewError):
            APPLIER.validate_feedback(feedback, original)


if __name__ == "__main__":
    unittest.main()
