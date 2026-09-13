"""Cover's saved variants must survive editing and remain readable on export."""

import copy
import importlib.util
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PACK_FIXTURES = load_module("cover_pack_fixtures", ROOT / "tests/test_render_quote_card_pack.py")
REVIEW_FIXTURES = load_module("cover_review_fixtures", ROOT / "tests/test_apply_card_review.py")
PACK = PACK_FIXTURES.PACK
RENDER = PACK.proof
INSPECT = PACK.inspector
APPLIER = REVIEW_FIXTURES.APPLIER
SIZES = ((1440, 1800), (1080, 1080), (1080, 1920))
COLORS = PACK_FIXTURES.production_manifest("proof.png")["brand"]["colors"]


class CoverMotifTests(unittest.TestCase):
    def test_seed_reproduces_the_chosen_drawing_and_changes_other_variants(self):
        original = RENDER.cover_graphic(1440, 1800, COLORS, 1842)
        other = RENDER.cover_graphic(1440, 1800, COLORS, 72)
        # Ignore the seed metadata: actual painted shapes must differ.
        self.assertNotEqual(list(ET.fromstring(original))[1].attrib,
                            list(ET.fromstring(other))[1].attrib)
        self.assertEqual(original, RENDER.cover_graphic(1440, 1800, COLORS, 1842))

    def test_bands_use_nine_percent_and_tiles_keep_normalized_geometry(self):
        for seed in (0, 72, 1842, 999999):
            reference = None
            for width, height in SIZES:
                with self.subTest(seed=seed, size=(width, height)):
                    root = ET.fromstring(RENDER.cover_graphic(width, height, COLORS, seed))
                    bands = [node for node in root if node.get("class") == "cover-band"]
                    self.assertEqual(2, len(bands))
                    self.assertAlmostEqual(0.0, float(bands[0].get("y")))
                    self.assertAlmostEqual(height * .91, float(bands[1].get("y")))
                    for band in bands:
                        self.assertAlmostEqual(height * .09, float(band.get("height")))
                    geometry = []
                    for node in root:
                        values = [float(node.get(key)) / dimension
                                  for key, dimension in (("x", width), ("y", height),
                                                         ("width", width), ("height", height))]
                        self.assertLessEqual(values[0] + values[2], 1.000002)
                        self.assertLessEqual(values[1] + values[3], 1.000002)
                        self.assertTrue(values[1] + values[3] <= .090002 or values[1] >= .909998)
                        geometry.append((node.get("fill"), values))
                    if reference is None:
                        reference = geometry
                    else:
                        self.assertEqual(len(reference), len(geometry))
                        for (fill, expected), (actual_fill, actual) in zip(reference, geometry):
                            self.assertEqual(fill, actual_fill)
                            for a, b in zip(expected, actual):
                                self.assertAlmostEqual(a, b, places=5)

    def test_fitted_quote_and_attribution_stay_between_bands(self):
        contents = [
            ["Breve."],
            ["La tecnologia cambia", "il modo in cui lavoriamo.",
             "Le domande che scegliamo", "di porre determinano", "il valore delle risposte.",
             "Serve tempo per capire", "e spazio per immaginare", "nuove possibilità."],
        ]
        for lines in contents:
            for width, height in SIZES:
                for position in ("upper", "center", "lower"):
                    with self.subTest(lines=len(lines), size=(width, height), position=position):
                        manifest = PACK_FIXTURES.production_manifest("proof.png")
                        manifest["approval"]["direction"] = "editorial"
                        manifest["content"].update(text=" ".join(lines), emphasis="")
                        manifest["presentation"].update(graphic_variant="cover", graphic_seed=1842)
                        item = {"lines": lines, "width": width, "height": height}
                        adapted = PACK.proof_manifest_for_format(manifest, item)
                        adapted["canvas"] = {"width": width, "height": height}
                        size, *_ = PACK.resolve_font_size(lines, adapted, ROOT, "editorial",
                                                         width, height, 1.0, position)
                        svg = RENDER.render_svg(adapted, ROOT, "editorial", font_size_override=size,
                                                render_options={"vertical_position": position})
                        self.assertEqual([], INSPECT.inspect_render(svg, "editorial", width, height,
                                                                    vertical_position=position))
                        boxes = INSPECT.text_boxes(ET.fromstring(svg))
                        self.assertTrue(any("attribution" in box["classes"] for box in boxes))
                        for box in boxes:
                            self.assertGreater(box["box"][1], height * .09)
                            self.assertLess(box["box"][3], height * .91)

    def test_square_logo_preserves_readable_quote_and_matches_fitting_reservation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            logo = path / "square.svg"
            logo.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
                            '<rect width="100" height="100" fill="#072743"/></svg>', encoding="utf-8")
            manifest = PACK_FIXTURES.production_manifest("proof.png")
            manifest["approval"]["direction"] = "editorial"
            manifest["brand"]["logo"] = {"dark_path": str(logo)}
            manifest["presentation"].update(graphic_variant="cover", graphic_seed=1842)
            lines = ["Una frase verificata."]
            manifest["content"].update(text=lines[0], emphasis="")
            adapted = PACK.proof_manifest_for_format(manifest, {"lines": lines})
            adapted["canvas"] = {"width": 1080, "height": 1080}
            size, *_ = PACK.resolve_font_size(lines, adapted, path, "editorial", 1080, 1080, 1.0)
            self.assertGreater(size, 60)
            svg = RENDER.render_svg(adapted, path, "editorial", font_size_override=size)
            root = ET.fromstring(svg)
            image = root.find("{http://www.w3.org/2000/svg}image")
            self.assertIsNotNone(image)
            self.assertAlmostEqual(1080 * .08, float(image.get("height")))
            upper, _ = PACK.vertical_limits(adapted, path, "editorial", 1080, 1080)
            logo_bottom = float(image.get("y")) + float(image.get("height"))
            self.assertAlmostEqual(logo_bottom + 1080 * .025, upper)
            quote_boxes = [box["box"] for box in INSPECT.text_boxes(root) if "quote" in box["classes"]]
            self.assertTrue(quote_boxes)
            self.assertTrue(all(box[1] >= upper - 1 for box in quote_boxes))
            self.assertEqual([], INSPECT.inspect_render(svg, "editorial", 1080, 1080))

    def test_seed_does_not_change_legacy_motifs(self):
        generative = {("editorial", "cutouts"), ("contextual", "constellations")}
        for direction, variants in RENDER.GRAPHIC_VARIANTS.items():
            for variant in variants - {"cover"} - {item[1] for item in generative}:
                with self.subTest(direction=direction, variant=variant):
                    args = dict(width=1440, height=1800, colors=COLORS, enabled=True, variant=variant)
                    self.assertEqual(RENDER.direction_graphic(direction, **args),
                                     RENDER.direction_graphic(direction, **args, seed=0))
        self.assertEqual("", RENDER.direction_graphic("editorial", width=1440, height=1800,
                                                     colors=COLORS, enabled=False, variant="cover", seed=1842))

    def test_review_roundtrip_preserves_seed_through_production(self):
        reviewed = REVIEW_FIXTURES.manifest()
        reviewed["direction"] = "editorial"
        feedback = {"feedback_id": "cover-1", "base_revision": 3, "action": "feedback",
                    "presentation": {"graphic_variant": "cover", "graphic_seed": 1842}}
        APPLIER.validate_feedback(feedback, reviewed)
        self.assertTrue(APPLIER._apply_patch(reviewed, feedback))
        saved = json.loads(json.dumps(reviewed))
        self.assertEqual(1842, saved["presentation"]["graphic_seed"])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            proof = path / "proof.png"
            proof.write_bytes(b"approved-proof")
            manifest = PACK_FIXTURES.production_manifest(proof)
            manifest["approval"]["direction"] = "editorial"
            manifest["presentation"] = saved["presentation"]
            self.assertEqual([], PACK.validate_production_manifest(manifest, path))
            manifest_path = path / "manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = PACK.render_pack(manifest, manifest_path, path / "output", "never", None, None, "keep")
            self.assertEqual(3, len(result["formats"]))
            for item in result["formats"]:
                self.assertEqual(1842, item["graphic_seed"])
                svg = (path / "output" / item["svg"]["path"]).read_text(encoding="utf-8")
                self.assertIn('data-seed="1842"', svg)
                self.assertIn('data-generator="cover-v1"', svg)

    def test_review_rejects_unreproducible_seed_values(self):
        manifest = REVIEW_FIXTURES.manifest()
        manifest["direction"] = "editorial"
        for seed in (-1, 1000000, 1.5, True, "1842", None):
            with self.subTest(seed=seed):
                feedback = {"base_revision": 3, "action": "feedback",
                            "presentation": {"graphic_variant": "cover", "graphic_seed": seed}}
                with self.assertRaisesRegex(APPLIER.ReviewError, "graphic_seed"):
                    APPLIER.validate_feedback(feedback, copy.deepcopy(manifest))


if __name__ == "__main__":
    unittest.main()
