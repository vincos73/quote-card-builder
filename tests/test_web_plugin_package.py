"""The remote plugin includes its visual reference when the skill links to it."""

import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "build_web_plugin_package", ROOT / "scripts" / "build_web_plugin_package.py"
)
BUILD = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(BUILD)


class WebPluginPackageTests(unittest.TestCase):
    def test_zip_bundles_the_urban_xerox_art_direction_reference(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "web-plugin.zip"
            BUILD.build_zip(output)
            with zipfile.ZipFile(output) as archive:
                names = set(archive.namelist())
                reference = "quote-card-builder-web/skills/quote-card-builder/assets/urban/urban-xerox-lime-reference.png"
                self.assertIn(reference, names)
                self.assertEqual(
                    (ROOT / "assets" / "urban" / "urban-xerox-lime-reference.png").read_bytes(),
                    archive.read(reference),
                )


if __name__ == "__main__":
    unittest.main()
