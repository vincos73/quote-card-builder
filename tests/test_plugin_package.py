import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "build_plugin_package", ROOT / "scripts" / "build_plugin_package.py"
)
BUILD_PLUGIN = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(BUILD_PLUGIN)


class PluginPackageTests(unittest.TestCase):
    def test_template_is_valid_and_italian_first(self):
        BUILD_PLUGIN.validate_template()
        manifest = json.loads(
            (ROOT / "plugin" / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["version"], "1.5.2")
        self.assertIn("quote card", manifest["interface"]["shortDescription"].lower())
        self.assertEqual(len(manifest["interface"]["defaultPrompt"]), 3)

    def test_build_keeps_canonical_runtime_files_in_sync(self):
        with tempfile.TemporaryDirectory() as temporary:
            plugin_root = BUILD_PLUGIN.build_directory(Path(temporary))
            skill_root = plugin_root / "skills" / "quote-card-builder"
            for relative in BUILD_PLUGIN.SKILL_FILES:
                self.assertEqual((ROOT / relative).read_bytes(), (skill_root / relative).read_bytes())
            self.assertFalse((skill_root / "scripts" / "build_plugin_package.py").exists())
            self.assertFalse(any(skill_root.rglob("__pycache__")))

    def test_zip_has_required_plugin_layout(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "quote-card-builder-plugin.zip"
            BUILD_PLUGIN.build_zip(output)
            with zipfile.ZipFile(output) as archive:
                names = set(archive.namelist())
            prefix = "quote-card-builder/"
            self.assertIn(prefix + ".codex-plugin/plugin.json", names)
            self.assertIn(prefix + "skills/quote-card-builder/SKILL.md", names)
            self.assertIn(prefix + "skills/quote-card-builder/assets/card-editor/index.html", names)


if __name__ == "__main__":
    unittest.main()
