"""Ribbons must retain the approved browser font and fragment spacing."""

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location("ribbon_raster", ROOT / "scripts/rasterize.py")
RASTER = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(RASTER)


class RibbonRasterTests(unittest.TestCase):
    def render(self, markup, **options):
        with tempfile.TemporaryDirectory() as directory:
            svg, png = Path(directory) / "card.svg", Path(directory) / "card.png"
            svg.write_text(markup, encoding="utf-8")
            return RASTER.rasterize(svg, png, 1440, 1800, **options)

    def test_explicit_ribbons_use_chrome_without_trying_sharp(self):
        legacy = mock.Mock()
        chrome = mock.Mock()
        with (mock.patch.object(RASTER, "BACKENDS", (("sharp", legacy),)),
              mock.patch.object(RASTER, "_chrome_ribbons", chrome),
              mock.patch.object(RASTER, "verify_png", return_value=[])):
            self.assertEqual("chrome", self.render("<svg/>", visual_grammar="ribbons"))
        chrome.assert_called_once()
        legacy.assert_not_called()

    def test_root_marker_automatically_selects_chrome(self):
        for quotes in ('"', "'"):
            with self.subTest(quotes=quotes):
                legacy = mock.Mock()
                chrome = mock.Mock()
                with (mock.patch.object(RASTER, "BACKENDS", (("sharp", legacy),)),
                      mock.patch.object(RASTER, "_chrome_ribbons", chrome),
                      mock.patch.object(RASTER, "verify_png", return_value=[])):
                    self.assertEqual("chrome", self.render(
                        f"<svg data-visual-grammar={quotes}ribbons{quotes}/>"))
                chrome.assert_called_once()
                legacy.assert_not_called()

    def test_unavailable_chrome_never_substitutes_a_legacy_font(self):
        legacy = mock.Mock()
        with (mock.patch.object(RASTER, "BACKENDS", (("sharp", legacy),)),
              mock.patch.object(RASTER, "_chrome_ribbons", side_effect=FileNotFoundError("Playwright assente"))):
            with self.assertRaises(RASTER.RasterError) as caught:
                self.render('<svg data-visual-grammar="ribbons"/>')
        self.assertEqual(["chrome"], [name for name, _ in caught.exception.attempts])
        self.assertIn("Playwright assente", str(caught.exception))
        legacy.assert_not_called()

    def test_marker_inside_card_content_does_not_change_legacy_rendering(self):
        legacy = mock.Mock()
        chrome = mock.Mock()
        with (mock.patch.object(RASTER, "BACKENDS", (("sharp", legacy),)),
              mock.patch.object(RASTER, "_chrome_ribbons", chrome),
              mock.patch.object(RASTER, "verify_png", return_value=[])):
            self.assertEqual("sharp", self.render(
                '<svg><text>data-visual-grammar="ribbons"</text></svg>'))
        legacy.assert_called_once()
        chrome.assert_not_called()

    def test_bad_chrome_png_is_rejected_without_falling_back(self):
        legacy = mock.Mock()
        with (mock.patch.object(RASTER, "BACKENDS", (("sharp", legacy),)),
              mock.patch.object(RASTER, "_chrome_ribbons", mock.Mock()),
              mock.patch.object(RASTER, "verify_png", return_value=["dimensioni errate"])):
            with self.assertRaises(RASTER.RasterError) as caught:
                self.render("<svg/>", visual_grammar="ribbons")
        self.assertIn("dimensioni errate", str(caught.exception))
        legacy.assert_not_called()

    def test_compatibility_baseline_remains_sharp_for_legacy(self):
        self.assertEqual("sharp", RASTER.PRIMARY_BACKEND)
        self.assertEqual("sharp", RASTER.BACKENDS[0][0])
        self.assertEqual("sharp", RASTER.primary_backend())
        self.assertEqual("chrome", RASTER.primary_backend("ribbons"))


if __name__ == "__main__":
    unittest.main()
