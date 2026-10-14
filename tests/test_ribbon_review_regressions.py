"""Regression coverage for user formatting, advisory colour and selectable output."""

import copy
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock
from urllib.request import Request, urlopen

from test_ribbon_sessions import ROOT, SERVER, ribbon_manifest
from grammar_sessions import complete_ribbon_formats


def edited_card():
    source = ribbon_manifest()
    text = "La tecnologia apre nuove possibilità. Il valore nasce dalle persone che sanno come trasformarle in qualcosa di utile."
    source["content"].update(text=text, emphasis="", styles=[
        {"start": 3, "end": 13, "type": "underline"},
        {"start": 60, "end": 67, "type": "bold"},
        {"start": 60, "end": 67, "type": "highlight"},
        {"start": 83, "end": 95, "type": "highlight"},
        {"start": 111, "end": 117, "type": "accent"},
    ], attribution={"label": "Autore dimostrativo", "role": "author"})
    source["brand"]["colors"].update(primary="#3B329F", accent="#F278D0", background="#D9FF00", text="#062037")
    source["presentation"].pop("quote_font_size", None)
    source["presentation"].pop("author_font_size", None)
    source["presentation"]["logo_mode"] = "hidden"
    source["formats"][0]["lines"] = ["La tecnologia apre nuove possibilità.", "Il valore nasce dalle persone che sanno come trasformarle in qualcosa di utile."]
    source["formats"] = complete_ribbon_formats(source["formats"], text)
    return source


class RibbonReviewRegressionTests(unittest.TestCase):
    def test_missing_formats_preserve_original_dimensions_breaks_and_manual_state(self):
        source = edited_card()
        original = copy.deepcopy(source["formats"][0])
        before = copy.deepcopy(source)
        completed = complete_ribbon_formats([original], source["content"]["text"])
        self.assertEqual(before, source)
        self.assertEqual(original, completed[0])
        self.assertEqual([(1440, 1800), (1440, 1440), (1440, 2560)], [(item["width"], item["height"]) for item in completed])
        self.assertTrue(all(item["lines"] == original["lines"] for item in completed))

    def test_existing_format_interventions_are_retained(self):
        source = edited_card()
        source["formats"][1]["text_scale"] = .9
        self.assertEqual(source["formats"], complete_ribbon_formats(source["formats"], source["content"]["text"]))

    def test_manual_accent_is_one_advisory_and_never_a_spurious_overflow(self):
        source = edited_card()
        before = copy.deepcopy(source)
        qa = SERVER.ensure_approvable(source, ROOT)
        self.assertTrue(qa["generation_allowed"])
        self.assertFalse(qa["passed"])
        self.assertEqual(["accent_contrast"], [item["code"] for item in qa["warnings"]])
        self.assertEqual("advisory", qa["warnings"][0]["severity"])
        self.assertNotIn("action_target", qa["warnings"][0])
        self.assertEqual(before, source)

    def test_all_outputs_keep_the_advisory_without_blocking_export(self):
        source = edited_card()
        source["presentation"]["output_mode"] = "all"
        result = SERVER.preview_response(source, ROOT, 1)
        self.assertTrue(result["qa"]["generation_allowed"])
        self.assertEqual({"4x5", "1x1", "9x16"}, {item["format"] for item in result["previews"]})
        self.assertEqual(3, len(result["warnings"]))
        self.assertTrue(all(item["code"] == "accent_contrast" for item in result["warnings"]))
        self.assertTrue(all(item["valid"] for item in result["composition_previews"]))

    def test_each_output_choice_checks_only_its_selected_format(self):
        source = edited_card()
        for format_id in ("4x5", "1x1", "9x16"):
            with self.subTest(format_id=format_id):
                source["presentation"]["output_mode"] = format_id
                qa = SERVER.ensure_approvable(source, ROOT)
                self.assertEqual([format_id], qa["checked_formats"])
                self.assertEqual({format_id}, {item["format"] for item in qa["warnings"]})
                self.assertEqual([format_id], [item["id"] for item in SERVER.production_formats(source)[1]])

    def test_overflow_warns_without_blocking_or_changing_explicit_size(self):
        source = edited_card()
        source["presentation"]["quote_font_size"] = 720
        before = copy.deepcopy(source)
        self.assertTrue(SERVER.ensure_approvable(source, ROOT)["generation_allowed"])
        qa = SERVER.preview_quality(source, SERVER.render_preview(source, ROOT), ROOT)
        self.assertFalse(qa["passed"])
        self.assertTrue(any(item["code"] == "quote_overflow" for item in qa["warnings"]))
        self.assertTrue(all(item["severity"] == "advisory" and "action_target" not in item for item in qa["warnings"]))
        self.assertEqual(before, source)

    def test_main_text_contrast_is_guidance_not_a_generation_block(self):
        source = edited_card()
        source["brand"]["colors"]["text"] = source["brand"]["colors"]["background"]
        qa = SERVER.ensure_approvable(source, ROOT)
        self.assertTrue(qa["generation_allowed"])
        self.assertFalse(qa["passed"])
        self.assertTrue(any("contrast" in item["code"] for item in qa["warnings"]))

    def test_reload_keeps_the_original_baseline_so_browser_edits_survive(self):
        source = edited_card()
        source["formats"] = source["formats"][:1]
        before = copy.deepcopy(source)
        model = SERVER.session_model(source, ROOT)
        self.assertEqual(source["formats"], model["formats"])
        self.assertEqual(["4x5", "1x1", "9x16"], [item["id"] for item in complete_ribbon_formats(model["formats"], model["content"]["text"])])
        self.assertEqual(before, source)

    def test_generate_route_exports_despite_contrast_and_size_warnings(self):
        source = edited_card()
        source["presentation"].update(quote_font_size=720, author_font_size=500)
        source["brand"]["colors"]["text"] = source["brand"]["colors"]["background"]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "review.json"
            SERVER.atomic_write_json(project, source)
            http_server, token = SERVER.create_server(project, root / "session")
            worker = threading.Thread(target=http_server.serve_forever, daemon=True)
            worker.start()
            try:
                payload = {"base_revision": 1}
                request = Request(f"http://127.0.0.1:{http_server.server_port}/api/generate?token={token}",
                                  data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
                def convert(_svg, png, _width, _height, **_options):
                    png.write_bytes(b"rasterizer-test-double")
                    return "chrome"
                with mock.patch.object(SERVER.pack.raster, "rasterize", side_effect=convert), \
                     mock.patch.object(SERVER, "chatbot_cli_path", return_value=None):
                    with urlopen(request) as response:
                        self.assertEqual(200, response.status)
                        result = json.load(response)
                self.assertTrue(result["applied"])
                generation = result["generation"]
                self.assertEqual("advisory", generation["quality_policy"])
                self.assertTrue(generation["outputs"])
                qa = SERVER.read_json(Path(generation["qa_report"]))
                codes = {warning["code"] for warning in qa["warnings"]}
                self.assertIn("quote_overflow", codes)
                self.assertIn("author_overflow", codes)
                self.assertTrue(any("contrast" in code for code in codes))
                self.assertTrue(all(warning["severity"] == "advisory" for warning in qa["warnings"]))
                generated = SERVER.read_json(Path(generation["production_manifest"]))
                self.assertEqual(720, generated["presentation"]["quote_font_size"])
                self.assertEqual(500, generated["presentation"]["author_font_size"])
                self.assertEqual(source["brand"], generated["brand"])
            finally:
                http_server.shutdown()
                http_server.server_close()
                worker.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
