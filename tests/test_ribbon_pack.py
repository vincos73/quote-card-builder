"""Ribbon export keeps selected sizes and checks its own composition areas."""

import copy
import html
import json
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import inspect_render as INSPECT
import render_quote_card_pack as PACK
from visual_grammars import demo_compositions


def manifest(proof_path: Path) -> dict:
    text = "L’IA amplia le possibilità. Il giudizio resta umano."
    return {
        "schema_version": "0.3", "state": "prova_visuale_approvata",
        "approval": {
            "direction": "editorial", "proof_path": str(proof_path),
            "content_sha256": PACK.sha256_text(text),
            "approved_by": "user", "approved_at": "2026-10-13",
        },
        "content": {
            "text": text, "transformation": "VERBATIM", "evidence_status": "VERIFIED",
            "emphasis": "", "styles": [{"start": text.index("giudizio"), "end": text.index("giudizio") + len("giudizio"), "type": "size", "scale": 1.4}],
            "styles_customized": True, "attribution": {"label": "Autore di prova", "role": "publisher"},
        },
        "formats": [{"id": "4x5", "width": 1440, "height": 1800,
                     "lines": [text], "text_scale": 0.8, "vertical_position": "center"}],
        "brand": {
            "name": "Test", "colors": {"primary": "#072743", "accent": "#E3F4FF",
                                        "background": "#FEFDFB", "text": "#323232"},
            "font": {"family": "Barlow", "regular_path": str(ROOT / "assets/card-editor/fonts/Barlow-Regular.ttf"),
                     "bold_path": str(ROOT / "assets/card-editor/fonts/Barlow-Bold.ttf")},
        },
        "source": {"title": "Test", "locator": "test://source"},
        "presentation": {"logo_mode": "hidden", "graphic_mode": "auto", "graphic_variant": "default",
                         "output_mode": "4x5", "visual_grammar": "ribbons",
                         "composition": demo_compositions(text, 4)[0],
                         "quote_font_size": 80, "author_font_size": 35},
        "output": {"basename": "ribbon-test"},
    }


def synthetic_svg(*, x=1300, width=100, author_x=1000, author_width=200, valid=True):
    boxes = {
        "quote": {"x": 1250, "y": 100, "width": 150, "height": 400},
        "author": {"x": 1000, "y": 800, "width": 300, "height": 150},
        "logo": None,
    }
    attributes = " ".join(f'data-{name}-box="{html.escape(json.dumps(box), quote=True)}"' for name, box in boxes.items())
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="1800" '
        f'data-visual-grammar="ribbons" data-layout-valid="{str(valid).lower()}" {attributes}>'
        '<rect width="1440" height="1800" fill="#FEFDFB"/>'
        '<defs><mask id="test"><rect width="1440" height="1800" fill="#072743"/></mask></defs>'
        f'<text class="quote" x="{x}" y="250" font-size="80" fill="#072743" data-measured-width="{width}">Testo</text>'
        f'<text class="attribution" x="{author_x}" y="870" font-size="40" fill="#323232" data-measured-width="{author_width}">Autore</text>'
        '</svg>'
    )


class RibbonInspectionTests(unittest.TestCase):
    def test_low_contrast_accent_is_reported_without_inventing_overflow(self):
        data = manifest(Path("unused.svg"))
        data["canvas"] = {"width": 1440, "height": 1800}
        data["content"]["lines"] = [data["content"]["text"]]
        data["content"]["styles"] = [{"start": 0, "end": 4, "type": "accent"}]
        layout = PACK.proof.ribbon_layout(data, ROOT)
        self.assertFalse(layout["valid"])
        self.assertTrue(layout["geometry_valid"])
        svg = PACK.proof.render_svg(data, ROOT, "editorial")
        for options in ({}, {"ribbon_layout": layout}):
            with self.subTest(metadata_only=not options):
                codes = {item["code"] for item in INSPECT.inspect_render(svg, "editorial", 1440, 1800, **options)}
                self.assertEqual({"accent_contrast"}, codes)

    def test_accepts_measured_fragments_outside_legacy_horizontal_guide(self):
        self.assertEqual([], INSPECT.inspect_render(synthetic_svg(), "editorial", 1440, 1800))

    def test_quote_and_author_are_checked_against_different_frames(self):
        codes = {item["code"] for item in INSPECT.inspect_render(
            synthetic_svg(width=180, author_width=350), "editorial", 1440, 1800,
        )}
        self.assertIn("text_outside_safe_area", codes)
        self.assertIn("attribution_outside_safe_area", codes)

    def test_rendered_author_quote_collision_is_detected(self):
        svg = synthetic_svg().replace('y="870"', 'y="260"').replace('x="1000" y="260"', 'x="1300" y="260"')
        codes = {item["code"] for item in INSPECT.inspect_render(svg, "editorial", 1440, 1800)}
        self.assertIn("attribution_overlaps_quote", codes)

    def test_invalid_layout_marker_blocks_render_even_if_svg_text_fits(self):
        codes = {item["code"] for item in INSPECT.inspect_render(synthetic_svg(valid=False), "editorial", 1440, 1800)}
        self.assertIn("ribbon_layout_invalid", codes)

    def test_missing_quote_frame_is_not_certified(self):
        svg = synthetic_svg().replace('data-quote-box=', 'data-unknown-box=')
        codes = {item["code"] for item in INSPECT.inspect_render(svg, "editorial", 1440, 1800)}
        self.assertIn("ribbon_geometry_missing", codes)


class RibbonPackTests(unittest.TestCase):
    def test_low_contrast_accent_keeps_fitting_true_and_is_exported_as_advisory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); proof_path = root / "approved.svg"; proof_path.write_text("<svg/>")
            data = manifest(proof_path)
            data["quality_policy"] = "advisory"
            data["content"]["styles"] = [{"start": 0, "end": 4, "type": "accent"}]
            original = copy.deepcopy(data)
            fitted = PACK.layout_measurement([data["content"]["text"]], 80, data, ROOT,
                                             "editorial", 1440, 1800, "center")
            self.assertTrue(fitted["fits"])
            self.assertFalse(fitted["layout_valid"])
            result = PACK.render_pack(data, root / "manifest.json", root / "output", "never", None, None, "keep")
            self.assertEqual(original, data)
            self.assertTrue(result["valid"])
            qa = json.loads(Path(result["qa_report"]).read_text())
            self.assertEqual({"accent_contrast"}, {warning["code"] for warning in qa["warnings"]})
            self.assertTrue(all(warning["severity"] == "advisory" for warning in qa["warnings"]))
            self.assertEqual([], qa["checks"]["render_inspection"]["defects"])
            self.assertEqual({"text_on_background", "accent_on_background"}, set(qa["checks"]["contrast"]))

    def test_default_strict_refuses_low_contrast_accent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); proof_path = root / "approved.svg"; proof_path.write_text("<svg/>")
            data = manifest(proof_path)
            data["content"]["styles"] = [{"start": 0, "end": 4, "type": "accent"}]
            with self.assertRaises(RuntimeError):
                PACK.render_pack(data, root / "manifest.json", root / "output", "never", None, None, "keep")

    def test_advisory_exports_manual_sizes_and_bad_contrast_without_correction(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); proof_path = root / "approved.svg"; proof_path.write_text("<svg/>")
            data = manifest(proof_path); data["quality_policy"] = "advisory"
            data["presentation"]["quote_font_size"] = 500
            data["presentation"]["author_font_size"] = 200
            data["brand"]["colors"]["text"] = data["brand"]["colors"]["background"]
            original = copy.deepcopy(data)
            self.assertEqual([], PACK.validate_production_manifest(data, root))
            result = PACK.render_pack(data, root / "manifest.json", root / "output", "never", None, None, "keep")
            self.assertEqual(original, data)
            self.assertEqual(500, result["formats"][0]["font_size"])
            self.assertEqual(200, result["formats"][0]["author_font_size"])
            qa = json.loads(Path(result["qa_report"]).read_text())
            self.assertEqual("advisory", qa["quality_policy"])
            self.assertFalse(qa["checks"]["visual_checks_passed"])
            codes = {warning["code"] for warning in qa["warnings"]}
            self.assertTrue({"text_contrast", "quote_overflow", "author_overflow"}.issubset(codes))
            self.assertTrue(all(warning["severity"] == "advisory" for warning in qa["warnings"]))
            self.assertTrue(all("action_target" not in warning for warning in qa["warnings"]))
            self.assertEqual(qa["warnings"], result["visual_warnings"])
            self.assertEqual("automatic_checks_passed", qa["status"])

    def test_advisory_never_exports_a_malformed_svg(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); proof_path = root / "approved.svg"; proof_path.write_text("<svg/>")
            data = manifest(proof_path); data["quality_policy"] = "advisory"
            with mock.patch.object(PACK.proof, "render_svg", return_value="<svg>"):
                with self.assertRaisesRegex(RuntimeError, "SVG"):
                    PACK.render_pack(data, root / "manifest.json", root / "output", "never", None, None, "keep")
            self.assertEqual([], list((root / "output").glob("*.svg")))

    def test_main_text_and_unreadable_highlight_contrast_still_block(self):
        for treatment in ("main", "highlight"):
            with self.subTest(treatment=treatment), tempfile.TemporaryDirectory() as directory:
                root = Path(directory); proof_path = root / "approved.svg"; proof_path.write_text("<svg/>")
                data = manifest(proof_path)
                if treatment == "main":
                    data["brand"]["colors"]["text"] = data["brand"]["colors"]["background"]
                else:
                    data["brand"]["colors"] = {"background": "#FFFFFF", "text": "#767676",
                                               "primary": "#767676", "accent": "#888888"}
                    data["content"]["styles"] = [{"start": 0, "end": 4, "type": "highlight"}]
                    adapted = PACK.proof_manifest_for_format(data, data["formats"][0])
                    codes = {issue["code"] for issue in PACK.proof.ribbon_layout(adapted, root)["warnings"]}
                    self.assertEqual({"highlight_contrast"}, codes)
                with self.assertRaises(RuntimeError):
                    PACK.render_pack(data, root / "manifest.json", root / "output", "never", None, None, "keep")
                self.assertEqual([], list((root / "output").glob("*.svg")))

    def test_auto_multiline_reflows_for_all_three_output_ratios(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); proof_path = root / "approved.svg"; proof_path.write_text("<svg/>")
            data = manifest(proof_path)
            data["presentation"].pop("quote_font_size")
            data["presentation"]["output_mode"] = "all"
            data["content"]["styles"] = [{"start": 0, "end": 4, "type": "bold"}]
            lines = ["L’IA amplia le possibilità.", "Il giudizio resta umano."]
            data["formats"] = [{"id": key, "width": 1440, "height": height, "lines": lines,
                                "text_scale": 1.0, "vertical_position": "center"}
                               for key, height in (("4x5", 1800), ("1x1", 1440), ("9x16", 2560))]
            self.assertEqual([], PACK.validate_production_manifest(data, root))
            result = PACK.render_pack(data, root / "manifest.json", root / "output", "never", None, None, "keep")
            self.assertEqual({"4x5", "1x1", "9x16"}, {item["format"] for item in result["formats"]})
            sizes = set()
            for item in result["formats"]:
                sizes.add(item["font_size"])
                svg = (root / "output" / item["svg"]["path"]).read_text()
                self.assertEqual([], INSPECT.inspect_render(svg, "editorial", item["width"], item["height"]))
                self.assertEqual(data["content"]["text"], " ".join(item["lines"]))
                self.assertTrue(any("possibilità." in line for line in item["lines"]))
            self.assertGreater(len(sizes), 1)

    def test_resolve_and_measure_use_the_requested_hard_lines_without_mutating_data(self):
        data = manifest(Path("unused.svg"))
        data["presentation"].pop("quote_font_size")
        data["content"]["styles"] = []
        data["canvas"] = {"width": 1440, "height": 1800}
        hard_lines = ["L’IA", "amplia", "le possibilità.", "Il giudizio", "resta umano."]
        original = copy.deepcopy(data)
        size = PACK.resolve_font_size(hard_lines, data, ROOT, "editorial", 1440, 1800, 1.0)[0]
        expected = copy.deepcopy(data); expected["content"]["lines"] = hard_lines
        layout = PACK.proof.ribbon_layout(expected, ROOT)
        self.assertEqual(layout["font_size"], size)
        measurement = PACK.layout_measurement(hard_lines, size, data, ROOT, "editorial", 1440, 1800, "center")
        self.assertEqual(layout["bounds"], measurement["bounds"])
        self.assertTrue(measurement["fits"])
        self.assertEqual(original, data)

    def test_ribbon_export_requests_its_chrome_backend_without_a_substitute_warning(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); data = manifest(root / "approved.svg")
            (root / "approved.svg").write_text("<svg/>")
            def rasterize(_svg, png, _width, _height, **_options):
                png.write_bytes(b"verified-by-rasterizer")
                return "chrome"
            with mock.patch.object(PACK.raster, "rasterize", side_effect=rasterize) as convert:
                result = PACK.render_pack(data, root / "manifest.json", root / "output", "required", None, None, "keep")
            self.assertEqual("ribbons", convert.call_args.kwargs["visual_grammar"])
            self.assertEqual("chrome", result["formats"][0]["png_backend"])
            self.assertEqual([], result["warnings"])

    def test_preview_measurement_uses_ribbon_wrap_and_its_reserved_author_area(self):
        data = manifest(Path("unused.svg"))
        data["canvas"] = {"width": 1440, "height": 1800}
        fitted = PACK.layout_measurement([data["content"]["text"]], 80, data, ROOT,
                                         "editorial", 1440, 1800, "center")
        self.assertTrue(fitted["fits"], fitted["warnings"])
        self.assertEqual(data["presentation"]["composition"]["quote_box"]["width"] * 1440, fitted["available_width"])
        data["presentation"]["author_font_size"] = 500
        oversized = PACK.layout_measurement([data["content"]["text"]], 80, data, ROOT,
                                            "editorial", 1440, 1800, "center")
        self.assertFalse(oversized["fits"])
        self.assertTrue(any(warning["code"] == "author_overflow" for warning in oversized["warnings"]))

    def test_production_preserves_explicit_sizes_and_uses_measured_wrapping(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); proof_path = root / "approved.svg"; proof_path.write_text("<svg/>")
            data = manifest(proof_path)
            manifest_path = root / "manifest.json"; manifest_path.write_text(json.dumps(data))
            self.assertEqual([], PACK.validate_production_manifest(data, root))
            with mock.patch.object(PACK, "fit_font_size", side_effect=AssertionError("legacy fitter used")):
                result = PACK.render_pack(data, manifest_path, root / "output", "never", None, None, "keep")
            item = result["formats"][0]
            self.assertEqual(80, item["font_size"])
            self.assertEqual(35, item["author_font_size"])
            self.assertFalse(item["auto_fitted"])
            self.assertEqual(data["content"]["text"], " ".join(item["lines"]))
            svg = (root / "output" / item["svg"]["path"]).read_text()
            self.assertEqual([], INSPECT.inspect_render(svg, "editorial", 1440, 1800))
            selected_word = next(node for node in ET.fromstring(svg).iter()
                                 if node.tag.endswith("}text") and node.text == "giudizio")
            self.assertEqual(112, float(selected_word.attrib["font-size"]))
            qa = json.loads(Path(result["qa_report"]).read_text())
            self.assertTrue(qa["checks"]["visual_inspection_required"])

    def test_oversized_manual_quote_and_author_are_not_silently_reduced(self):
        for field in ("quote_font_size", "author_font_size"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                root = Path(directory); proof_path = root / "approved.svg"; proof_path.write_text("<svg/>")
                data = manifest(proof_path); data["presentation"][field] = 500
                selected = copy.deepcopy(data["presentation"])
                with self.assertRaises(RuntimeError):
                    PACK.render_pack(data, root / "manifest.json", root / "output", "never", None, None, "keep")
                self.assertEqual(selected, data["presentation"])
                self.assertEqual([], list((root / "output").glob("*.svg")))


if __name__ == "__main__":
    unittest.main()
