import sys
import unittest
import xml.etree.ElementTree as ET
import copy
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import render_quote_card as renderer
from visual_grammars import demo_compositions, normalize_composition


def card(text):
    return {
        "canvas": {"width": 1440, "height": 1800},
        "content": {
            "text": text,
            "lines": [text],
            "styles": [],
            "attribution": {"role": "author", "label": "Reserved author"},
        },
        "brand": {
            "name": "Test",
            "font": {
                "family": "Barlow",
                "regular_path": str(
                    ROOT / "assets/card-editor/fonts/Barlow-Regular.ttf"
                ),
                "bold_path": str(ROOT / "assets/card-editor/fonts/Barlow-Bold.ttf"),
            },
            "colors": {
                "primary": "#1800FF",
                "accent": "#EE45DA",
                "background": "#DFFF00",
                "text": "#072743",
            },
        },
        "presentation": {
            "visual_grammar": "urban",
            "composition": demo_compositions(text, grammar="urban")[0],
        },
    }


class UrbanGrammarTests(unittest.TestCase):
    def test_rejects_invalid_block_geometry_identifiers_names_and_roles(self):
        base = demo_compositions("Valid scene", grammar="urban")[0]
        invalid = []
        for field, value in (("width", -0.1), ("height", 0), ("width", 1.01)):
            scene = copy.deepcopy(base)
            scene["blocks"][0][field] = value
            invalid.append(scene)
        scene = copy.deepcopy(base)
        scene["blocks"][0]["id"] = []
        invalid.append(scene)
        scene = copy.deepcopy(base)
        scene["blocks"][1]["id"] = scene["blocks"][0]["id"]
        invalid.append(scene)
        scene = copy.deepcopy(base)
        scene["strips"] = [
            {
                "id": {},
                "color_role": "text",
                "x1": 0,
                "y1": 0,
                "x2": 1,
                "y2": 1,
                "width": 0.01,
            }
        ]
        invalid.append(scene)
        scene = copy.deepcopy(base)
        scene["name"] = 123
        invalid.append(scene)
        scene = copy.deepcopy(base)
        scene["text_role"] = {}
        invalid.append(scene)
        scene = copy.deepcopy(base)
        scene["texture"]["color_role"] = []
        invalid.append(scene)
        for scene in invalid:
            with self.subTest(scene=scene):
                with self.assertRaises(ValueError):
                    normalize_composition(scene)

    def test_long_unicode_quote_author_and_absolute_size_keep_shared_metrics_across_formats(
        self,
    ):
        text = ("Città, naïveté, 東京, русский текст — " * 5).strip()
        attribution = "Équipe internationale — 東京 " * 4
        for width, height in ((1440, 1800), (1440, 1440), (1440, 2560)):
            data = card(text)
            data["canvas"] = {"width": width, "height": height}
            data["content"]["attribution"] = {"role": "author", "label": attribution}
            data["presentation"]["quote_font_size"] = 54
            data["presentation"]["author_font_size"] = 24
            layout = renderer.urban_layout(data, ROOT)
            self.assertEqual(54, layout["font_size"])
            self.assertEqual(24, layout["author_font_size"])
            self.assertTrue(
                layout["metric"] in {"font_metrics_ttf", "deterministic_heuristic"}
            )
            self.assertTrue(any("東京" in row["text"] for row in layout["rows"]))
            self.assertTrue(
                any("Équipe" in row["text"] for row in layout["author_rows"])
            )

    def test_neutral_profile_demos_keep_readable_text_in_every_production_format(self):
        text = "Le idee migliori nascono dalle persone."
        colors = {
            "primary": "#072743",
            "accent": "#E3F4FF",
            "background": "#FEFDFB",
            "text": "#323232",
        }
        for width, height in ((1440, 1800), (1440, 1440), (1440, 2560)):
            for scene in demo_compositions(text, grammar="urban"):
                data = {
                    "canvas": {"width": width, "height": height},
                    "content": {
                        "text": text,
                        "lines": [text],
                        "styles": [],
                        "attribution": {"role": "none", "label": ""},
                    },
                    "brand": {
                        "name": "Neutral",
                        "font": {"family": "Arial"},
                        "colors": colors,
                    },
                    "presentation": {"visual_grammar": "urban", "composition": scene},
                }
                layout = renderer.urban_layout(data, ROOT)
                self.assertNotIn(
                    "text_contrast",
                    {warning["code"] for warning in layout["warnings"]},
                    scene["id"],
                )
                svg = renderer.render_svg(data, ROOT, "editorial")
                self.assertIn('class="quote-backing"', svg)

    def test_three_bounded_native_scenes_and_render_metadata(self):
        scenes = demo_compositions("A concise urban quote", seed=42, grammar="urban")
        self.assertEqual(3, len({s["id"] for s in scenes}))
        for scene in scenes:
            self.assertEqual(scene, normalize_composition(scene))
            self.assertIn("author_box", scene)
        data = card("A concise urban quote")
        data["presentation"]["composition"] = scenes[1]
        svg = renderer.render_svg(data, ROOT, "editorial")
        root = ET.fromstring(svg)
        self.assertEqual("urban", root.get("data-visual-grammar"))
        self.assertIsNotNone(root.get("data-quote-box"))
        self.assertTrue(any(el.tag.endswith("polygon") for el in root.iter()))

    def test_texture_seed_is_deterministic_and_text_has_nonblocking_overflow_metadata(
        self,
    ):
        data = card("Readable text")
        a = renderer.render_svg(data, ROOT, "editorial")
        b = renderer.render_svg(data, ROOT, "editorial")
        self.assertEqual(a, b)
        data["presentation"]["quote_font_size"] = 180
        layout = renderer.urban_layout(data, ROOT)
        self.assertIn("warnings", layout)


if __name__ == "__main__":
    unittest.main()
