"""Focused geometry checks for the selectable generative styles."""

import importlib.util
import hashlib
import unittest
import xml.etree.ElementTree as ET
import tempfile
from pathlib import Path

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("render_quote_card", ROOT / "scripts/render_quote_card.py")
RENDER = importlib.util.module_from_spec(spec)
spec.loader.exec_module(RENDER)
pack_spec = importlib.util.spec_from_file_location("render_quote_card_pack", ROOT / "tests/test_render_quote_card_pack.py")
PACK_FIXTURES = importlib.util.module_from_spec(pack_spec)
pack_spec.loader.exec_module(PACK_FIXTURES)
PACK = PACK_FIXTURES.PACK
server_spec = importlib.util.spec_from_file_location("card_review_server", ROOT / "scripts/card_review_server.py")
SERVER = importlib.util.module_from_spec(server_spec)
server_spec.loader.exec_module(SERVER)
COLORS = {"background": "#f4efe6", "primary": "#072743", "accent": "#d95d39"}


class GenerativeStyleTests(unittest.TestCase):
    def test_variant_contract(self):
        self.assertTrue(RENDER.graphic_variant_allowed("editorial", "cover"))
        self.assertTrue(RENDER.graphic_variant_allowed("editorial", "cutouts"))
        self.assertTrue(RENDER.graphic_variant_allowed("contextual", "constellations"))

    def test_cutouts_are_flat_edge_polygons_and_seeded(self):
        first = RENDER.direction_graphic("editorial", width=1440, height=1800,
                                         colors=COLORS, enabled=True, variant="cutouts", seed=1)
        other = RENDER.direction_graphic("editorial", width=1440, height=1800,
                                         colors=COLORS, enabled=True, variant="cutouts", seed=2)
        self.assertNotEqual(first, other)
        root = ET.fromstring(first)
        self.assertEqual(3, len(root.findall("polygon")))
        self.assertTrue(all(node.get("fill") in {COLORS["primary"], COLORS["accent"]}
                            for node in root))
        self.assertEqual({COLORS["primary"], COLORS["accent"]}, {node.get("fill") for node in root})
        self.assertNotIn("shadow", first.lower())

    def test_constellations_have_two_diagonal_corner_networks(self):
        svg = RENDER.direction_graphic("contextual", width=1440, height=1800,
                                       colors=COLORS, enabled=True, variant="constellations", seed=42)
        root = ET.fromstring(svg)
        self.assertEqual(2, sum("constellation--" in node.get("class", "") for node in root))
        self.assertGreaterEqual(sum("constellation-node" in node.get("class", "") for node in root.iter()), 10)
        self.assertGreaterEqual(sum("constellation-line" in node.get("class", "") for node in root.iter()), 8)

    def test_constellations_vary_connections_and_keep_solid_nodes(self):
        import re
        signatures = set()
        for seed in range(16):
            root = ET.fromstring(RENDER.constellations_graphic(1440, 1800, COLORS, seed))
            group = list(root)[0]
            nodes = [node for node in group if node.tag == "circle"]
            degrees = [0] * len(nodes)
            centers = [(float(n.get("cx")), float(n.get("cy"))) for n in nodes]
            for node in nodes:
                self.assertEqual(COLORS["primary"], node.get("fill"))
            for edge in group.findall("path"):
                values = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", edge.get("d"))]
                for point in (tuple(values[:2]), tuple(values[2:])):
                    degrees[centers.index(point)] += 1
            signatures.add(tuple(sorted(degrees)))
        self.assertGreaterEqual(len(signatures), 3)

    def test_seed_zero_preserves_existing_contours_and_echo_rings(self):
        frozen = {("editorial", "default"): "d090b327a819e49d3cacd2829bd542b795ea21d5c4c742311dfd656476e63952",
                  ("statement", "default"): "d32c901605b67ac2bcfb82a5045913dbe94d06754054ef8ef3498899b004cd6a"}
        for direction, variant in (("editorial", "default"), ("statement", "default")):
            args = dict(width=1440, height=1800, colors=COLORS, enabled=True, variant=variant)
            legacy = RENDER.direction_graphic(direction, **args, seed=0)
            self.assertEqual(frozen[(direction, variant)], hashlib.sha256(legacy.encode()).hexdigest())
            self.assertNotEqual(RENDER.direction_graphic(direction, **args, seed=17),
                                RENDER.direction_graphic(direction, **args, seed=18))

    def test_new_families_render_cleanly_across_formats_positions_and_seeds(self):
        with tempfile.TemporaryDirectory() as tmp:
            logo = Path(tmp) / "square.svg"
            logo.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" fill="#072743"/></svg>', encoding="utf-8")
            for direction, variant in (("editorial", "cutouts"), ("contextual", "constellations")):
                for seed in (0, 1, 42, 999999):
                    data = PACK_FIXTURES.production_manifest("proof.png")
                    data["approval"]["direction"] = direction
                    data["brand"]["logo"] = {"dark_path": str(logo)}
                    data["content"]["attribution"]["label"] = "Fonte editoriale con attribuzione lunga verificata"
                    data["presentation"].update(graphic_variant=variant, graphic_seed=seed)
                    for item in data["formats"]:
                        for position in ("upper", "center", "lower"):
                            adapted = PACK.proof_manifest_for_format(data, item)
                            adapted["canvas"] = {"width": item["width"], "height": item["height"]}
                            size, *_ = PACK.resolve_font_size(item["lines"], adapted, ROOT, direction,
                                                               item["width"], item["height"], 1.0, position)
                            svg = RENDER.render_svg(adapted, ROOT, direction, font_size_override=size,
                                                    render_options={"vertical_position": position})
                            findings = PACK.inspector.inspect_render(svg, direction, item["width"], item["height"],
                                                                      vertical_position=position)
                            self.assertEqual([], findings, (direction, variant, seed, item["id"], position))

    def test_preview_quality_seed_six_cutouts_with_and_without_logo(self):
        for with_logo in (False, True):
            with self.subTest(with_logo=with_logo):
                data = PACK_FIXTURES.production_manifest("proof.png")
                data["approval"]["direction"] = "editorial"
                data["direction"] = "editorial"
                data["presentation"].update(graphic_variant="cutouts", graphic_seed=6)
                for item in data["formats"]:
                    item.update(text_scale=1.0, vertical_position="center")
                if with_logo:
                    with tempfile.TemporaryDirectory() as tmp:
                        logo = Path(tmp) / "square.svg"
                        logo.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" fill="#072743"/></svg>', encoding="utf-8")
                        data["brand"]["logo"] = {"dark_path": str(logo)}
                        previews = SERVER.render_preview(data, Path(tmp))
                        qa = SERVER.preview_quality(data, previews, Path(tmp))
                else:
                    previews = SERVER.render_preview(data, ROOT)
                    qa = SERVER.preview_quality(data, previews, ROOT)
                self.assertTrue(qa["passed"], qa)


if __name__ == "__main__":
    unittest.main()
