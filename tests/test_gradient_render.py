"""Regression coverage for the seeded Editorial/Gradient renderer."""

import copy
import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("render_quote_card_gradient", ROOT / "scripts" / "render_quote_card.py")
RENDER = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(RENDER)
INSPECT_SPEC = importlib.util.spec_from_file_location(
    "inspect_render_gradient", ROOT / "scripts" / "inspect_render.py"
)
INSPECT = importlib.util.module_from_spec(INSPECT_SPEC)
assert INSPECT_SPEC and INSPECT_SPEC.loader
INSPECT_SPEC.loader.exec_module(INSPECT)

COLORS = {"primary": "#68364F", "accent": "#E992B0", "background": "#FEFDFB", "text": "#323232"}


def manifest() -> dict:
    return {
        "schema_version": "0.2",
        "state": "contenuto_approvato",
        "direction": "editorial",
        "canvas": {"width": 1080, "height": 1350},
        "content": {
            "text": "Lo spazio rende nitide le idee.",
            "lines": ["Lo spazio rende", "nitide le idee."],
            "transformation": "VERBATIM",
            "evidence_status": "VERIFIED",
            "emphasis": "",
            "styles": [],
            "styles_customized": True,
            "attribution": {"label": "Vincos", "role": "publisher"},
        },
        "brand": {"name": "Gradient test", "colors": copy.deepcopy(COLORS), "font": {"family": "Arial"}},
        "presentation": {
            "graphic_mode": "auto",
            "graphic_variant": "gradient",
            "graphic_seed": 42,
            "logo_mode": "hidden",
        },
    }


class GradientRenderTests(unittest.TestCase):
    def test_gradient_is_allowed_seeded_and_visibly_changes_geometry(self):
        args = dict(width=1080, height=1350, colors=COLORS, enabled=True, variant="gradient")
        self.assertTrue(RENDER.graphic_variant_allowed("editorial", "gradient"))
        same = RENDER.direction_graphic("editorial", **args, seed=1842)
        self.assertEqual(same, RENDER.direction_graphic("editorial", **args, seed=1842))
        fingerprints = {
            hashlib.sha256(RENDER.direction_graphic("editorial", **args, seed=seed).encode()).hexdigest()
            for seed in range(16)
        }
        self.assertGreaterEqual(len(fingerprints), 14)
        self.assertIn('data-generator="gradient-v1"', same)
        self.assertIn('data-gradient-floor="4.5"', same)

    def test_gradient_surface_passes_conservative_contrast_validation(self):
        data = manifest()
        self.assertEqual([], RENDER.validate_visual_manifest(data, ROOT))
        report = RENDER.gradient_render_safety(data["brand"], ROOT, logo_mode="hidden")
        self.assertTrue(report["passed"], report)
        svg = RENDER.render_svg(data, ROOT, "editorial", font_size_override=72)
        self.assertIn("direction-graphic--gradient", svg)
        self.assertIn('data-gradient-inks="#68364F,#323232"', svg)
        self.assertEqual([], INSPECT.inspect_render(svg, "editorial", 1080, 1350))

    def test_render_inspector_rejects_unverifiable_gradient_logo(self):
        data = manifest()
        data["presentation"]["logo_mode"] = "auto"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            logo = root / "css-logo.svg"
            logo.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg"><style>.logo{fill:#68364F}</style>'
                '<rect class="logo" width="10" height="10"/></svg>',
                encoding="utf-8",
            )
            data["brand"]["logo"] = {"dark_path": str(logo)}
            svg = RENDER.render_svg(data, root, "editorial", font_size_override=72)
            self.assertIn(
                "gradient_logo_contrast_unverifiable",
                {item["code"] for item in INSPECT.inspect_render(svg, "editorial", 1080, 1350)},
            )

    def test_gradient_rejects_a_palette_with_an_unreadable_full_field(self):
        data = manifest()
        data["brand"]["colors"] = {
            "primary": "#555555",
            "accent": "#888888",
            "background": "#777777",
            "text": "#777777",
        }
        errors = RENDER.validate_visual_manifest(data, ROOT)
        self.assertIn("gradient_contrast", {item["code"] for item in errors})

    def test_gradient_logo_audit_fails_closed_for_css_and_accepts_flat_svg(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = manifest()
            css_logo = root / "css-logo.svg"
            css_logo.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg"><style>.logo{fill:#68364F}</style>'
                '<rect class="logo" width="10" height="10"/></svg>',
                encoding="utf-8",
            )
            data["brand"]["logo"] = {"dark_path": str(css_logo)}
            self.assertEqual("unverifiable_svg_logo", RENDER.gradient_render_safety(data["brand"], root)["logo_status"])

            flat_logo = root / "flat-logo.svg"
            flat_logo.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg"><rect width="10" height="10" fill="#68364F"/></svg>',
                encoding="utf-8",
            )
            data["brand"]["logo"] = {"dark_path": str(flat_logo)}
            self.assertEqual("verified_svg_logo", RENDER.gradient_render_safety(data["brand"], root)["logo_status"])


if __name__ == "__main__":
    unittest.main()
