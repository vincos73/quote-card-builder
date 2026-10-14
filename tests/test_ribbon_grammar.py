"""Editable ribbons: content integrity, explicit typography and safe geometry."""

import copy
import json
import math
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import render_quote_card as renderer
from visual_grammars import cubic_point, variation_compositions

NS = "{http://www.w3.org/2000/svg}"


def manifest(text="Le idee crescono quando incontrano prospettive diverse."):
    return {
        "schema_version": "0.2", "state": "contenuto_approvato", "direction": "editorial",
        "content": {"text": text, "lines": [text], "transformation": "AI_GENERATED",
                    "evidence_status": "USER_SUPPLIED", "styles": [], "styles_customized": True,
                    "attribution": {"label": "Autore dimostrativo", "role": "author"}},
        "canvas": {"width": 1440, "height": 1800},
        "brand": {"name": "Prova", "font": {
            "family": "Barlow", "regular_path": str(ROOT / "assets/card-editor/fonts/Barlow-Regular.ttf"),
            "bold_path": str(ROOT / "assets/card-editor/fonts/Barlow-Bold.ttf"),
        }, "colors": {"primary": "#1800FF", "accent": "#EE45DA", "background": "#DFFF00", "text": "#072743"}},
        "presentation": {"visual_grammar": "ribbons", "composition": renderer.demo_compositions(text)[0]},
        "output": {"basename": "ribbon-test"},
    }


class RibbonContractTests(unittest.TestCase):
    def test_arbitrary_authored_curve_is_preserved_and_not_replaced_by_demo(self):
        data = manifest()
        edited = data["presentation"]["composition"]
        edited["ribbons"][0]["points"][1] = [.42, .22]
        result = renderer.normalize_composition(edited)
        self.assertEqual([.42, .22], result["ribbons"][0]["points"][1])
        svg = renderer.render_svg(data, ROOT, "editorial")
        self.assertIn("C 604.80 396.00", svg)
        self.assertNotEqual(renderer.demo_compositions(data["content"]["text"])[0], result)

    def test_rejects_non_numeric_paths_nonfinite_values_and_invalid_crossings(self):
        mutations = [
            lambda composition: composition["ribbons"][0].update(points="M 0 0<script/>"),
            lambda composition: composition["ribbons"][0].update(width_ratio=math.nan),
            lambda composition: composition["ribbons"][0]["points"][0].__setitem__(0, math.inf),
            lambda composition: composition["crossings"][0].update(over="missing"),
            lambda composition: composition["crossings"][0].update(segment=99),
            lambda composition: composition["quote_box"].update(x=.9),
        ]
        for mutation in mutations:
            value = renderer.demo_compositions()[0]
            mutation(value)
            with self.subTest(value=value), self.assertRaises(ValueError):
                renderer.normalize_composition(value)

    def test_demo_choices_change_topology_and_reading_area(self):
        items = renderer.demo_compositions("Un testo di prova", seed=14)
        self.assertEqual(3, len(items))
        self.assertEqual(3, len({json.dumps(item["quote_box"], sort_keys=True) for item in items}))
        self.assertEqual(3, len({json.dumps(item["ribbons"], sort_keys=True) for item in items}))

    def test_demo_strokes_avoid_text_author_and_logo_before_protective_masks(self):
        # A mask must remain a safety net, not cut the demonstration artwork
        # into disconnected pieces. Check thick paths and the mask clearance.
        for length in (1, 200, 400):
            for seed in (0, 8, 16):
                for composition in renderer.demo_compositions("x" * length, seed):
                    for ribbon in composition["ribbons"]:
                        dx = ribbon["width_ratio"] / 2 + .012
                        dy = dx * .8  # The pilot canvas is 1440 x 1800.
                        for segment in range((len(ribbon["points"]) - 1) // 3):
                            for sample in range(101):
                                x, y = cubic_point(ribbon["points"], segment, sample / 100)
                                for key in ("quote_box", "author_box", "logo_box"):
                                    box = composition[key]
                                    overlap = (box["x"] - dx < x < box["x"] + box["width"] + dx
                                               and box["y"] - dy < y < box["y"] + box["height"] + dy)
                                    self.assertFalse(overlap, (length, seed, composition["id"], ribbon["id"], key, x, y))

    def test_style_recomposition_keeps_saved_palette_roles_widths_and_extra_ribbons(self):
        base = renderer.demo_compositions()[0]
        base.update(background_role="primary", text_role="background", highlight_role="text")
        base["ribbons"][0].update(id="base-wide", color_role="accent", width_ratio=.18)
        base["ribbons"][1].update(id="base-thin", color_role="text", width_ratio=.04)
        extra = copy.deepcopy(base["ribbons"][0])
        extra.update(id="base-third", color_role="primary", width_ratio=.065)
        base["ribbons"].append(extra)
        base["crossings"] = []
        before = copy.deepcopy(base)
        variants = variation_compositions(base, "Una nuova citazione più lunga per il riuso della base.", seed=21)
        self.assertEqual(before, base)
        expected = [(path["id"], path["color_role"], path["width_ratio"]) for path in base["ribbons"]]
        for variant in variants:
            self.assertEqual(expected, [(path["id"], path["color_role"], path["width_ratio"])
                                        for path in variant["ribbons"]])
            for role in ("background_role", "text_role", "highlight_role"):
                self.assertEqual(base[role], variant[role])
            self.assertEqual(3, len({json.dumps(path["points"]) for path in variant["ribbons"]}))
            self.assertEqual(variant, renderer.normalize_composition(variant))
        self.assertEqual(3, len({json.dumps(variant["ribbons"]) for variant in variants}))

    def test_rejects_local_size_in_legacy_grammar_and_invalid_scale(self):
        data = manifest()
        data["content"]["styles"] = [{"start": 0, "end": 2, "type": "size", "scale": 1.4}]
        data.pop("presentation")
        self.assertTrue(any(error["code"] == "grammar" for error in renderer.validate_visual_manifest(data, ROOT)))
        data = manifest()
        data["content"]["styles"] = [{"start": 0, "end": 2, "type": "size", "scale": True}]
        self.assertTrue(any(error["code"] == "range" for error in renderer.validate_visual_manifest(data, ROOT)))


class RibbonLayoutTests(unittest.TestCase):
    def test_manual_hard_lines_wrap_each_paragraph_in_all_three_formats(self):
        paragraphs = ["La tecnologia apre nuove possibilità.",
                      "Il valore nasce dalle persone che sanno come trasformarle in qualcosa di utile."]
        text = " ".join(paragraphs)
        for height in (1800, 1440, 2560):
            with self.subTest(height=height):
                data = manifest(text)
                data["canvas"]["height"] = height
                data["content"]["lines"] = paragraphs
                start = text.index("persone")
                data["content"]["styles"] = [
                    {"start": start, "end": start + 7, "type": "highlight"},
                    {"start": start, "end": start + 7, "type": "size", "scale": 1.3},
                ]
                before = copy.deepcopy(data)
                layout = renderer.ribbon_layout(data, ROOT)
                self.assertTrue(layout["valid"], layout["warnings"])
                self.assertTrue(layout["geometry_valid"])
                boundary = len(paragraphs[0])
                self.assertTrue(all(row["end"] <= boundary or row["start"] > boundary for row in layout["rows"]))
                self.assertEqual(text, " ".join(layout["lines"]))
                selected = [fragment for row in layout["rows"] for fragment in row["fragments"]
                            if "highlight" in fragment["types"]]
                self.assertEqual("persone", "".join(fragment["text"] for fragment in selected))
                for fragment in selected:
                    self.assertEqual(text[fragment["start"]:fragment["end"]], fragment["text"])
                renderer.render_svg(data, ROOT, "editorial")
                self.assertEqual(before, data)

    def test_canonical_newlines_win_over_stale_lines_without_losing_style_offsets(self):
        text = "La tecnologia apre nuove possibilità.\nIl valore nasce dalle persone."
        data = manifest(text)
        data["content"]["lines"] = [text.replace("\n", " ")]
        start = text.index("persone")
        data["content"]["styles"] = [{"start": start, "end": start + 7, "type": "bold"}]
        layout = renderer.ribbon_layout(data, ROOT)
        boundary = text.index("\n")
        self.assertTrue(all(row["end"] <= boundary or row["start"] > boundary for row in layout["rows"]))
        self.assertTrue(all("\n" not in row["text"] for row in layout["rows"]))
        selected = [fragment for row in layout["rows"] for fragment in row["fragments"] if "bold" in fragment["types"]]
        self.assertEqual("persone", "".join(fragment["text"] for fragment in selected))
        self.assertTrue(all(fragment["start"] >= start for fragment in selected))

    def test_incomplete_stale_lines_cannot_discard_words(self):
        text = "La tecnologia apre nuove possibilità e il valore nasce dalle persone."
        data = manifest(text)
        data["content"]["lines"] = ["La tecnologia", "persone."]
        layout = renderer.ribbon_layout(data, ROOT)
        self.assertEqual(text, " ".join(layout["lines"]))

    def test_leading_blank_line_is_included_in_auto_fit_and_explicit_overflow(self):
        data = manifest("Parola.")
        data["content"]["lines"] = ["", "Parola."]
        data["presentation"]["composition"]["quote_box"]["height"] = .1
        auto = renderer.ribbon_layout(data, ROOT)
        self.assertTrue(auto["geometry_valid"], auto["warnings"])
        self.assertLess(auto["font_size"], 80)
        self.assertLessEqual(auto["bounds"]["quote"]["y"] + auto["bounds"]["quote"]["height"],
                             auto["quote_box"]["y"] + auto["quote_box"]["height"])
        data["presentation"]["quote_font_size"] = 100
        explicit = renderer.ribbon_layout(data, ROOT)
        self.assertEqual(100, explicit["font_size"])
        self.assertFalse(explicit["geometry_valid"])
        self.assertTrue(any(warning["code"] == "quote_overflow" for warning in explicit["warnings"]))

    def test_accent_contrast_warning_is_distinct_from_geometric_fit_in_svg(self):
        data = manifest("Una parola colorata.")
        data["brand"]["colors"]["accent"] = data["brand"]["colors"]["background"]
        start = data["content"]["text"].index("colorata")
        data["content"]["styles"] = [{"start": start, "end": start + 8, "type": "accent"}]
        layout = renderer.ribbon_layout(data, ROOT)
        self.assertFalse(layout["valid"])
        self.assertTrue(layout["geometry_valid"])
        self.assertEqual(["accent_contrast"], [warning["code"] for warning in layout["warnings"]])
        root = ET.fromstring(renderer.render_svg(data, ROOT, "editorial"))
        self.assertEqual("true", root.get("data-geometry-valid"))
        self.assertEqual(layout["warnings"], json.loads(root.get("data-layout-warnings")))
        accented = next(element for element in root.iter(f"{NS}text") if element.get("data-text-styles") == "accent")
        self.assertEqual("colorata", accented.text)

    def test_local_word_size_reflows_without_reducing_explicit_base_size(self):
        data = manifest("Le persone costruiscono insieme nuove possibilità.")
        data["presentation"]["quote_font_size"] = 80
        initial = renderer.ribbon_layout(data, ROOT)
        start = data["content"]["text"].index("persone")
        data["content"]["styles"] = [{"start": start, "end": start + 7, "type": "size", "scale": 2}]
        changed = renderer.ribbon_layout(data, ROOT)
        self.assertEqual(80, changed["font_size"])
        self.assertNotEqual(initial["lines"], changed["lines"])
        selected = [fragment for row in changed["rows"] for fragment in row["fragments"] if "size" in fragment["types"]]
        self.assertTrue(selected)
        self.assertTrue(all(fragment["font_size"] == 160 for fragment in selected))
        for previous, current in zip(changed["rows"], changed["rows"][1:]):
            self.assertGreater(current["y"] - current["font_size"] * .82,
                               previous["y"] + previous["font_size"] * .28)

    def test_oversize_request_survives_render_override_and_reports_overflow(self):
        data = manifest("Una parola lunghissima e molte altre parole per occupare tutto lo spazio.")
        data["presentation"]["quote_font_size"] = 600
        layout = renderer.ribbon_layout(data, ROOT, font_size_override=30, render_options={"text_scale": .8})
        self.assertEqual(600, layout["font_size"])
        self.assertFalse(layout["valid"])
        self.assertTrue(any(warning["code"] == "quote_overflow" for warning in layout["warnings"]))
        svg = renderer.render_svg(data, ROOT, "editorial", font_size_override=30)
        self.assertIn('font-size="600.00"', svg)
        self.assertIn('data-layout-valid="false"', svg)

    def test_geometry_warnings_describe_the_problem_without_changing_user_choices(self):
        data = manifest("Parola.")
        data["presentation"].update(quote_font_size=100, author_font_size=40)
        for key in ("quote_box", "author_box", "logo_box"):
            data["presentation"]["composition"][key] = {"x": .3, "y": .3, "width": .4, "height": .02}
        data["brand"]["logo"] = {"dark_path": str(ROOT / "assets/card-editor/quote-card-builder-wordmark.svg")}
        before = copy.deepcopy(data)
        layout = renderer.ribbon_layout(data, ROOT)
        self.assertEqual({
            "quote_overflow": "Il testo non entra nell'area assegnata.",
            "author_overflow": "L’attribuzione non entra nell’area assegnata.",
            "author_overlaps_quote": "L'autore si sovrappone alla citazione.",
            "logo_overlaps_text": "Il logo si sovrappone al testo.",
        }, {warning["code"]: warning["message"] for warning in layout["warnings"]})
        self.assertEqual((100, 40), (layout["font_size"], layout["author_font_size"]))
        self.assertEqual(before, data)

    def test_highlight_tracks_selected_words_across_reflow_and_size_changes(self):
        text = "Le idee incontrano prospettive diverse e diventano più forti."
        data = manifest(text)
        start, end = text.index("prospettive"), text.index(" e diventano")
        data["presentation"]["quote_font_size"] = 100
        data["presentation"]["composition"]["quote_box"]["width"] = .40
        data["content"]["styles"] = [
            {"start": start, "end": end, "type": "highlight"},
            {"start": start, "end": end, "type": "size", "scale": 1.35},
        ]
        layout = renderer.ribbon_layout(data, ROOT)
        selected = [fragment for row in layout["rows"] for fragment in row["fragments"] if "highlight" in fragment["types"]]
        self.assertGreaterEqual(len(selected), 2)
        self.assertEqual("prospettive diverse", " ".join(fragment["text"].strip() for fragment in selected))
        root = ET.fromstring(renderer.render_svg(data, ROOT, "editorial"))
        markers = [element for element in root.iter(f"{NS}rect") if element.get("class") == "highlight-marker"]
        self.assertEqual(len(selected), len(markers))
        for fragment, marker in zip(selected, markers):
            self.assertGreater(float(marker.get("width")), fragment["width"])
            self.assertAlmostEqual(fragment["font_size"] * .98, float(marker.get("height")), delta=.01)

    def test_spaces_at_style_fragment_edges_are_preserved_in_svg(self):
        text = "La tecnologia apre nuove possibilità. Il valore nasce dalle persone."
        data = manifest(text)
        start = text.index("tecnologia")
        value_start = text.index("valore")
        data["presentation"]["quote_font_size"] = 68
        data["content"]["styles"] = [
            {"start": start, "end": start + len("tecnologia"), "type": "size", "scale": 1.25},
            {"start": 0, "end": text.index(" Il"), "type": "highlight"},
            {"start": value_start, "end": value_start + len("valore"), "type": "bold"},
        ]
        layout = renderer.ribbon_layout(data, ROOT)
        root = ET.fromstring(renderer.render_svg(data, ROOT, "editorial"))
        elements = [element for element in root.iter(f"{NS}text") if element.get("class") == "quote"]
        expected = [fragment for row in layout["rows"] for fragment in row["fragments"]]
        self.assertEqual([fragment["text"] for fragment in expected], [element.text for element in elements])
        self.assertTrue(any((element.text or "").startswith(" ") or (element.text or "").endswith(" ")
                            for element in elements))
        for element, fragment in zip(elements, expected):
            self.assertEqual("preserve", element.get("{http://www.w3.org/XML/1998/namespace}space"))
            self.assertIn("white-space:pre", element.get("style"))
            self.assertEqual(text[fragment["start"]:fragment["end"]], element.text)

    def test_two_line_author_has_independent_size_and_does_not_move_quote(self):
        data = manifest()
        data["content"]["attribution"]["label"] = "Nome dell’autore\nRuolo dimostrativo"
        data["presentation"]["author_font_size"] = 40
        initial = renderer.ribbon_layout(data, ROOT)
        self.assertEqual(2, len(initial["author_rows"]))
        data["presentation"]["author_font_size"] = 48
        changed = renderer.ribbon_layout(data, ROOT)
        self.assertEqual(initial["font_size"], changed["font_size"])
        self.assertEqual(48, changed["author_font_size"])
        self.assertEqual(initial["rows"], changed["rows"])

    def test_absent_author_reserves_capacity_without_a_placeholder(self):
        data = manifest()
        data["content"]["attribution"] = {"role": "none", "label": "Non deve comparire"}
        layout = renderer.ribbon_layout(data, ROOT)
        self.assertEqual([], layout["author_rows"])
        svg = renderer.render_svg(data, ROOT, "editorial")
        self.assertNotIn("Non deve comparire", svg)
        self.assertIn('data-author-box=', svg)
        self.assertGreater(layout["author_box"]["height"], 0)

    def test_uses_real_brand_metrics_for_bold_and_does_not_mutate_card(self):
        data = manifest("WWWW WWWW")
        data["presentation"]["quote_font_size"] = 100
        before = copy.deepcopy(data)
        plain = renderer.ribbon_layout(data, ROOT)
        self.assertEqual("font_metrics_ttf", plain["metric"])
        renderer.render_svg(data, ROOT, "editorial")
        self.assertEqual(before, data)
        data["content"]["styles"] = [{"start": 0, "end": len(data["content"]["text"]), "type": "bold"}]
        bold = renderer.ribbon_layout(data, ROOT)
        # Bold is not universally wider (Barlow's W is slightly narrower).
        # The important guarantee is that it uses the actual distinct face.
        self.assertNotEqual(bold["bounds"]["quote"]["width"], plain["bounds"]["quote"]["width"])

    def test_bad_accent_contrast_is_reported_before_export(self):
        data = manifest()
        data["brand"]["colors"]["accent"] = data["brand"]["colors"]["background"]
        data["content"]["styles"] = [{"start": 0, "end": 2, "type": "accent"}]
        layout = renderer.ribbon_layout(data, ROOT)
        self.assertFalse(layout["valid"])
        self.assertTrue(any(warning["code"] == "accent_contrast" for warning in layout["warnings"]))

    def test_logo_is_embedded_without_distortion_and_inside_its_lane(self):
        data = manifest()
        with tempfile.TemporaryDirectory() as directory:
            asset = Path(directory) / "logo.svg"
            asset.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 20"><path fill="#072743" d="M0 0H200V20H0Z"/></svg>')
            data["brand"]["logo"] = {"dark_path": str(asset)}
            root = ET.fromstring(renderer.render_svg(data, ROOT, "editorial"))
            image = root.find(f"{NS}image")
            self.assertIsNotNone(image)
            self.assertAlmostEqual(10, float(image.get("width")) / float(image.get("height")), delta=.02)
            self.assertTrue(image.get("href").startswith("data:image/svg+xml;base64,"))


class RibbonCrossingTests(unittest.TestCase):
    def test_shallow_crossing_covers_full_overlap_instead_of_cutting_at_a_circle(self):
        over = {"id": "upper", "color_role": "primary", "width_ratio": .12,
                "points": [[.05,.20],[.35,.20],[.65,.20],[.95,.20]]}
        under = {"id": "lower", "color_role": "accent", "width_ratio": .12,
                 "points": [[.05,.15],[.35,.18],[.65,.22],[.95,.25]]}
        crossing = {"over": "upper", "under": "lower", "segment": 0, "t": .5}
        before = copy.deepcopy((over, under))
        portion = renderer._ribbon_crossing_path(over, under, crossing, 1440, 1800)
        self.assertIsNotNone(portion)
        # All of this nearly parallel pair overlaps. Restricting the repair
        # to a fixed central circle would leave visible colour steps.
        self.assertEqual(over["points"], portion["points"])
        self.assertEqual(before, (over, under))
        data = manifest()
        data["presentation"]["composition"]["ribbons"] = [over, under]
        data["presentation"]["composition"]["crossings"] = [crossing]
        root = ET.fromstring(renderer.render_svg(data, ROOT, "editorial"))
        repair = next(path for path in root.iter(f"{NS}path") if path.get("data-over") == "upper")
        self.assertEqual(renderer._ribbon_path(over, 1440, 1800), repair.get("d"))
        self.assertIsNone(repair.get("clip-path"))
        mask = next(mask for mask in root.iter(f"{NS}mask") if mask.get("id") == "ribbon-crossing-0")
        self.assertEqual(renderer._ribbon_path(under, 1440, 1800), mask.find(f"{NS}path").get("d"))

    def test_crossing_repair_does_not_reorder_a_separate_nearby_intersection(self):
        over = {"id": "upper", "color_role": "primary", "width_ratio": .03,
                "points": [[.05,.20],[.35,.20],[.65,.20],[.95,.20]]}
        under = {"id": "lower", "color_role": "accent", "width_ratio": .03,
                 "points": [[.20,-.10],[.20,.20],[.20,.35],[.20,.35],
                            [.38,.62],[.60,.62],[.80,.35],
                            [.80,.35],[.80,.20],[.80,-.10]]}
        left = renderer._ribbon_crossing_path(over, under,
            {"over": "upper", "under": "lower", "segment": 0, "t": 1/6}, 1440, 1800)
        right = renderer._ribbon_crossing_path(over, under,
            {"over": "upper", "under": "lower", "segment": 0, "t": 5/6}, 1440, 1800)
        self.assertIsNotNone(left)
        self.assertIsNotNone(right)
        self.assertLess(max(point[0] for point in left["points"]), .4)
        self.assertGreater(min(point[0] for point in right["points"]), .6)
        self.assertEqual(4, len(left["points"]))
        self.assertEqual(4, len(right["points"]))


if __name__ == "__main__":
    unittest.main()
