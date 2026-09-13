"""Contract checks for the seeded Editorial/Gradient renderer."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
PYTHON_NODE = Path("/Users/vincos/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node")
NODE_MODULES = Path("/Users/vincos/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules")


def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


RENDER = load("render_quote_card", "render_quote_card.py")
INSPECT = load("inspect_render", "inspect_render.py")
RASTER = load("rasterize", "rasterize.py")


COLORS = {"primary": "#68364F", "accent": "#E992B0", "background": "#FEFDFB", "text": "#323232"}


def manifest(width: int = 1080, height: int = 1350) -> dict:
    return {
        "schema_version": "0.2", "state": "contenuto_approvato", "direction": "editorial",
        "canvas": {"width": width, "height": height},
        "content": {
            "text": "Lo spazio rende nitide le idee.", "lines": ["Lo spazio rende", "nitide le idee."],
            "transformation": "VERBATIM", "evidence_status": "VERIFIED", "emphasis": "",
            "styles": [], "styles_customized": True,
            "attribution": {"label": "Vincos", "role": "publisher"},
        },
        "brand": {"name": "Gradient test", "colors": dict(COLORS), "font": {"family": "Arial"}},
        "presentation": {"graphic_mode": "auto", "graphic_variant": "gradient", "graphic_seed": 42,
                         "logo_mode": "hidden"},
    }


class GradientRenderTests(unittest.TestCase):
    def test_seed_is_deterministic_and_visibly_changes_generator_geometry(self):
        args = dict(width=1080, height=1350, colors=COLORS, enabled=True, variant="gradient")
        self.assertEqual(
            RENDER.direction_graphic("editorial", **args, seed=1842),
            RENDER.direction_graphic("editorial", **args, seed=1842),
        )
        fingerprints = {
            hashlib.sha256(RENDER.direction_graphic("editorial", **args, seed=seed).encode()).hexdigest()
            for seed in range(16)
        }
        self.assertGreaterEqual(len(fingerprints), 14)

    @unittest.skipUnless(RASTER.available_backends(node=PYTHON_NODE, node_modules=NODE_MODULES),
                         "nessun convertitore raster installato")
    def test_seed_changes_raster_pixels_while_same_seed_is_byte_stable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            def paint(seed: int, name: str) -> bytes:
                graphic = RENDER.direction_graphic(
                    "editorial", width=240, height=300, colors=COLORS, enabled=True,
                    variant="gradient", seed=seed,
                )
                svg_path, png_path = root / f"{name}.svg", root / f"{name}.png"
                svg_path.write_text(
                    '<svg xmlns="http://www.w3.org/2000/svg" width="240" height="300">'
                    f'<rect width="240" height="300" fill="{COLORS["background"]}"/>{graphic}</svg>',
                    encoding="utf-8",
                )
                RASTER.rasterize(svg_path, png_path, 240, 300, node=PYTHON_NODE, node_modules=NODE_MODULES)
                return png_path.read_bytes()

            same_a, same_b, other = paint(42, "same-a"), paint(42, "same-b"), paint(1842, "other")
            self.assertEqual(same_a, same_b)
            _, _, channels, first = RASTER.decode_png(same_a)
            _, _, _, second = RASTER.decode_png(other)
            changed = sum(
                1 for offset in range(0, len(first), channels)
                if sum(abs(first[offset + channel] - second[offset + channel]) for channel in range(3)) >= 8
            )
            self.assertGreater(changed / (len(first) // channels), 0.12)

    def test_actual_gradient_surface_passes_conservative_contrast_bound(self):
        data = manifest()
        self.assertEqual([], RENDER.validate_visual_manifest(data, ROOT))
        report = RENDER.gradient_render_safety(data["brand"], ROOT, logo_mode="hidden")
        self.assertTrue(report["passed"], report)
        svg = RENDER.render_svg(data, ROOT, "editorial", font_size_override=72)
        self.assertEqual([], INSPECT.inspect_render(svg, "editorial", 1080, 1350))

    @unittest.skipUnless(RASTER.available_backends(node=PYTHON_NODE, node_modules=NODE_MODULES),
                         "nessun convertitore raster installato")
    def test_raster_background_samples_clear_primary_contrast(self):
        """Test pixels after SVG alpha compositing, not only declared stops."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            graphic = RENDER.direction_graphic(
                "editorial", width=360, height=450, colors=COLORS, enabled=True,
                variant="gradient", seed=999999,
            )
            svg_path, png_path = root / "surface.svg", root / "surface.png"
            svg_path.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" width="360" height="450">'
                f'<rect width="360" height="450" fill="{COLORS["background"]}"/>{graphic}</svg>',
                encoding="utf-8",
            )
            RASTER.rasterize(svg_path, png_path, 360, 450, node=PYTHON_NODE, node_modules=NODE_MODULES)
            width, height, channels, pixels = RASTER.decode_png(png_path.read_bytes())
            ratios = []
            # Sample a dense, regular grid across the *rasterised* surface.
            for y in range(0, height, 7):
                for x in range(0, width, 7):
                    offset = (y * width + x) * channels
                    rgb = pixels[offset:offset + 3]
                    colour = "#" + "".join(f"{channel:02X}" for channel in rgb)
                    ratios.append(RENDER.contrast_ratio(COLORS["primary"], colour))
            self.assertGreaterEqual(min(ratios), 4.45)

    def test_svg_logo_is_checked_across_three_output_formats(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            logo = root / "logo.svg"
            logo.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 60">'
                '<path d="M0 0h200v60H0z" fill="#68364F"/></svg>', encoding="utf-8",
            )
            for width, height in ((1080, 1350), (1080, 1080), (1080, 1920)):
                data = manifest(width, height)
                data["brand"]["logo"] = {"dark_path": str(logo)}
                data["presentation"]["logo_mode"] = "auto"
                report = RENDER.gradient_render_safety(data["brand"], root)
                self.assertTrue(report["passed"], (width, height, report))
                self.assertEqual("verified_svg_logo", report["logo_status"])
                svg = RENDER.render_svg(data, root, "editorial", font_size_override=52)
                self.assertIn('data-gradient-logo-status="verified_svg_logo"', svg)
                self.assertEqual([], INSPECT.inspect_render(svg, "editorial", width, height), (width, height))

    def test_logo_opacity_or_css_causes_a_fail_closed_contrast_result(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, source in {
                "opacity": '<svg xmlns="http://www.w3.org/2000/svg"><rect width="10" height="10" fill="#68364F" opacity=".1"/></svg>',
                "css": '<svg xmlns="http://www.w3.org/2000/svg"><style>.logo{fill:#68364F}</style><rect class="logo" width="10" height="10"/></svg>',
            }.items():
                logo = root / f"{name}.svg"; logo.write_text(source, encoding="utf-8")
                data = manifest(); data["brand"]["logo"] = {"dark_path": str(logo)}
                data["presentation"]["logo_mode"] = "auto"
                safety = RENDER.gradient_render_safety(data["brand"], root)
                self.assertFalse(safety["passed"], safety)
                svg = RENDER.render_svg(data, root, "editorial", font_size_override=50)
                codes = {item["code"] for item in INSPECT.inspect_render(svg, "editorial", 1080, 1350)}
                self.assertIn("gradient_logo_contrast_unverifiable", codes)

    def test_unsafe_accent_and_outline_are_checked_against_gradient_surface(self):
        data = manifest()
        data["content"]["styles"] = [{"start": 0, "end": 2, "type": "accent"}]
        accent_svg = RENDER.render_svg(data, ROOT, "editorial", font_size_override=72)
        self.assertIn("gradient_contrast", {item["code"] for item in INSPECT.inspect_render(accent_svg, "editorial", 1080, 1350)})
        data["content"]["styles"] = [{"start": 0, "end": 2, "type": "outline"}]
        outline_svg = RENDER.render_svg(data, ROOT, "editorial", font_size_override=72).replace(
            f'stroke="{COLORS["primary"]}"', f'stroke="{COLORS["accent"]}"', 1,
        )
        self.assertIn("gradient_contrast", {item["code"] for item in INSPECT.inspect_render(outline_svg, "editorial", 1080, 1350)})

    def test_channel_envelope_handles_a_mid_tone_ink_inside_the_range(self):
        inside = RENDER._gradient_contrast_bound(["#111111", "#F0F0F0"], ["#AAAAAA"])
        self.assertEqual(1.0, inside["minimum"])
        dark = RENDER._gradient_contrast_bound(["#000000", "#333333"], ["#111111"])
        self.assertLess(dark["minimum"], 2.0)


if __name__ == "__main__":
    unittest.main()
