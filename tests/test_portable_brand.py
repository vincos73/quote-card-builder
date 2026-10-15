import base64
import io
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from scripts.portable_brand import (
    MAX_ASSET_BYTES, SCHEMA, SCHEMA_VERSION, brand_from_kit,
    kit_from_brand, normalize_brand_kit,
)


def base_kit():
    return {"schema": SCHEMA, "schema_version": SCHEMA_VERSION, "name": "Test",
            "colors": {"primary": "#112233", "accent": "#223344",
                       "background": "#334455", "text": "#445566"}}


def png_bytes() -> bytes:
    image = Image.new("RGBA", (2, 2), "white")
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


class PortableBrandTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.temp_path = Path(self.temp.name)

    def test_roundtrip_embeds_and_materializes_assets_without_paths(self):
        source_font = Path("assets/card-editor/fonts/Barlow-Regular.ttf").resolve()
        font = self.temp_path / "Barlow-Regular.ttf"
        font.write_bytes(source_font.read_bytes())
        logo = self.temp_path / "logo.png"
        logo.write_bytes(png_bytes())
        kit = kit_from_brand({
            "name": "Studio", "colors": {"primary": "#112233", "accent": "#445566",
                                         "background": "#FFFFFF", "text": "#010203"},
            "font": {"family": "Barlow", "regular_path": str(font)},
            "logo": {"dark_path": str(logo)},
        }, self.temp_path)
        self.assertEqual(kit["schema"], SCHEMA)
        self.assertEqual(kit["schema_version"], SCHEMA_VERSION)
        self.assertNotIn(str(font), json.dumps(kit))
        self.assertNotIn(str(logo), json.dumps(kit))
        out_dir = self.temp_path / "portable assets"
        brand = brand_from_kit(kit, out_dir)
        self.assertEqual(brand["font"]["family"], "Barlow")
        self.assertEqual(Path(brand["font"]["regular_path"]).read_bytes(), font.read_bytes())
        self.assertEqual(brand["logo"]["dark_path"], brand["logo"]["light_path"])
        self.assertEqual(Path(brand["logo"]["light_path"]).read_bytes(), logo.read_bytes())
        self.assertEqual(brand_from_kit(kit, out_dir), brand)
        self.assertEqual(len(list(out_dir.iterdir())), 2)

    def test_distinct_local_logo_variants_survive_portability(self):
        dark_logo = self.temp_path / "dark.png"
        light_logo = self.temp_path / "light.png"
        for path, color in ((dark_logo, "black"), (light_logo, "white")):
            image = Image.new("RGBA", (3, 2), color)
            output = io.BytesIO()
            image.save(output, format="PNG")
            path.write_bytes(output.getvalue())
        brand = {"name": "Dual", "colors": base_kit()["colors"],
                 "logo": {"dark_path": str(dark_logo), "light_path": str(light_logo)}}
        kit = kit_from_brand(brand, self.temp_path)
        self.assertIn("logo", kit)  # Single-logo compatibility is retained.
        self.assertEqual(set(kit["logo_variants"]), {"dark", "light"})
        portable = brand_from_kit(kit, self.temp_path / "restored")
        self.assertEqual(Path(portable["logo"]["dark_path"]).read_bytes(), dark_logo.read_bytes())
        self.assertEqual(Path(portable["logo"]["light_path"]).read_bytes(), light_logo.read_bytes())

    def test_builtin_family_and_palette_need_no_asset_paths(self):
        brand = {"name": "Plain", "colors": {"primary": "#abcdef", "accent": "#111111",
                                             "background": "#ffffff", "text": "#000000"},
                 "font": {"family": "Arial"}}
        kit = kit_from_brand(brand, ".")
        self.assertEqual(set(kit["font"]), {"family"})
        self.assertNotIn("logo", kit)

    def test_rejects_unsupported_schema_version(self):
        kit = base_kit()
        kit["schema_version"] = 2
        with self.assertRaisesRegex(ValueError, "schema"):
            normalize_brand_kit(kit)

    def test_rejects_invalid_color(self):
        kit = base_kit()
        kit["colors"]["primary"] = "#12345"
        with self.assertRaisesRegex(ValueError, "#RRGGBB"):
            normalize_brand_kit(kit)

    def test_rejects_unknown_fields(self):
        kit = base_kit()
        kit["unexpected"] = True
        with self.assertRaisesRegex(ValueError, "unsupported fields"):
            normalize_brand_kit(kit)

    def test_rejects_invalid_base64_mismatched_mime_and_svg_root(self):
        kit = base_kit()
        kit["logo"] = {"mime_type": "image/png", "data_base64": "%%%"}
        with self.assertRaisesRegex(ValueError, "base64"):
            normalize_brand_kit(kit)
        kit["logo"] = {"mime_type": "image/png", "data_base64": base64.b64encode(b"GIF89a").decode()}
        with self.assertRaisesRegex(ValueError, "MIME"):
            normalize_brand_kit(kit)
        kit["logo"] = {"mime_type": "image/svg+xml", "data_base64": base64.b64encode(b"<svg/>").decode()}
        with self.assertRaisesRegex(ValueError, "SVG namespace"):
            normalize_brand_kit(kit)

    def test_approved_svg_roundtrips_and_executable_or_external_content_is_rejected(self):
        source = Path("assets/card-editor/vincos-lockup-white.svg").resolve()
        local = self.temp_path / source.name
        local.write_bytes(source.read_bytes())
        kit = kit_from_brand({"name": "Vincos", "colors": base_kit()["colors"],
                              "logo": {"dark_path": str(local)}}, self.temp_path)
        self.assertEqual(kit["logo"]["mime_type"], "image/svg+xml")
        materialized = brand_from_kit(kit, self.temp_path / "out")
        self.assertEqual(Path(materialized["logo"]["dark_path"]).read_bytes(), source.read_bytes())
        unsafe = (
            '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg"><image href="https://bad.example/x"/></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg"><path fill="url(https://bad.example/x)"/></svg>',
            '<!DOCTYPE svg [<!ENTITY x "boom">]><svg xmlns="http://www.w3.org/2000/svg">&x;</svg>',
            '<svg xmlns="http://www.w3.org/2000/svg"><path onclick="alert(1)"/></svg>',
        )
        for payload in unsafe:
            with self.subTest(payload=payload[:32]):
                kit["logo"] = {"mime_type": "image/svg+xml",
                               "data_base64": base64.b64encode(payload.encode()).decode()}
                with self.assertRaises(ValueError):
                    normalize_brand_kit(kit)

    def test_rejects_oversize_asset_and_out_of_context_path(self):
        kit = base_kit()
        oversized = b"\x89PNG\r\n\x1a\n" + b"x" * MAX_ASSET_BYTES
        kit["logo"] = {"mime_type": "image/png", "data_base64": base64.b64encode(oversized).decode()}
        with self.assertRaisesRegex(ValueError, "limit"):
            normalize_brand_kit(kit)
        outside = self.temp_path.parent / (self.temp_path.name + "-outside.png")
        outside.write_bytes(png_bytes())
        self.addCleanup(lambda: outside.unlink(missing_ok=True))
        brand = {"name": "x", "colors": base_kit()["colors"], "logo": {"dark_path": str(outside)}}
        with self.assertRaisesRegex(ValueError, "inside base_dir"):
            kit_from_brand(brand, self.temp_path)

    def test_rejects_mismatched_font_signature(self):
        kit = base_kit()
        kit["font"] = {"family": "x", "regular": {"mime_type": "font/ttf",
                                                        "data_base64": base64.b64encode(b"bad font").decode()}}
        with self.assertRaisesRegex(ValueError, "font bytes"):
            normalize_brand_kit(kit)

    def test_rejects_truncated_raster_image(self):
        kit = base_kit()
        kit["logo"] = {"mime_type": "image/png",
                       "data_base64": base64.b64encode(b"\x89PNG\r\n\x1a\ntruncated").decode()}
        with self.assertRaisesRegex(ValueError, "truncated or invalid"):
            normalize_brand_kit(kit)


if __name__ == "__main__":
    unittest.main()
