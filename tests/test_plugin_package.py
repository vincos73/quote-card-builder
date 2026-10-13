import importlib.util
import json
import tempfile
import unittest
import zipfile
from unittest.mock import patch
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "build_plugin_package", ROOT / "scripts" / "build_plugin_package.py"
)
BUILD_PLUGIN = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(BUILD_PLUGIN)


class PluginPackageTests(unittest.TestCase):
    def test_package_rejects_mismatched_server_version(self):
        original_read = Path.read_text

        def changed_project(path, *args, **kwargs):
            content = original_read(path, *args, **kwargs)
            if path == ROOT / "pyproject.toml":
                return content.replace('version = "1.8.10"', 'version = "0.0.0"')
            return content

        with patch.object(Path, "read_text", changed_project):
            with self.assertRaisesRegex(ValueError, "versione del runtime MCP"):
                BUILD_PLUGIN.validate_template()

    def test_template_is_valid_and_marketplace_ready_in_english(self):
        BUILD_PLUGIN.validate_template()
        manifest = json.loads(
            (ROOT / "plugin" / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["version"], "1.8.10")
        self.assertEqual(manifest["interface"]["capabilities"], ["Interactive", "Read"])
        self.assertIn("quote card", manifest["interface"]["shortDescription"].lower())
        self.assertIn("one populated editor", manifest["interface"]["longDescription"].lower())
        self.assertLessEqual(len(manifest["interface"]["shortDescription"]), 30)
        self.assertIn("global workspace", manifest["interface"]["longDescription"].lower())
        self.assertIn("drafts do not sync across devices or conversations", manifest["interface"]["longDescription"].lower())
        self.assertIn("Proceed with this link and make a quote card.", manifest["interface"]["defaultPrompt"])
        self.assertEqual(manifest["mcpServers"], "./.mcp.json")

    def test_package_pins_the_mcp_apps_2x_runtime(self):
        requirement = (ROOT / "requirements-mcp.txt").read_text(encoding="utf-8")
        self.assertRegex(requirement, r"(?m)^mcp\[cli\]==2\.1\.1\s*$")

        with tempfile.TemporaryDirectory() as temporary:
            plugin_root = BUILD_PLUGIN.build_directory(Path(temporary))
            bundled = plugin_root / "skills" / "quote-card-builder" / "requirements-mcp.txt"
            self.assertEqual(requirement, bundled.read_text(encoding="utf-8"))

    def test_build_keeps_canonical_runtime_files_in_sync(self):
        with tempfile.TemporaryDirectory() as temporary:
            plugin_root = BUILD_PLUGIN.build_directory(Path(temporary))
            skill_root = plugin_root / "skills" / "quote-card-builder"
            for relative in BUILD_PLUGIN.SKILL_FILES:
                self.assertEqual((ROOT / relative).read_bytes(), (skill_root / relative).read_bytes())
            self.assertFalse((skill_root / "scripts" / "build_plugin_package.py").exists())
            self.assertTrue((plugin_root / ".mcp.json").is_file())
            self.assertTrue((skill_root / "scripts" / "mcp_server.py").is_file())
            self.assertTrue((skill_root / "scripts" / "mcp_quote_card.py").is_file())
            self.assertTrue((skill_root / "scripts" / "mcp_app.py").is_file())
            self.assertTrue((skill_root / "assets" / "card-editor" / "fonts" / "Barlow-Regular.ttf").is_file())
            self.assertTrue((skill_root / "assets" / "card-editor" / "fonts" / "Orbitron-Variable.ttf").is_file())
            self.assertTrue((skill_root / "assets" / "card-editor" / "fonts" / "Barlow-Regular-latin.woff2").is_file())
            self.assertTrue((skill_root / "assets" / "card-editor" / "fonts" / "Orbitron-Variable-latin.woff2").is_file())
            self.assertTrue((skill_root / "assets" / "card-editor" / "vincos-lockup-white.svg").is_file())
            self.assertTrue((skill_root / "assets" / "mcp-editor" / "host-context.js").is_file())
            self.assertTrue((skill_root / "assets" / "mcp-editor" / "host-theme.css").is_file())
            wordmark = skill_root / "assets" / "card-editor" / "quote-card-builder-wordmark.svg"
            self.assertTrue(wordmark.is_file())
            wordmark_svg = wordmark.read_text(encoding="utf-8")
            self.assertIn("<text", wordmark_svg)
            self.assertIn("font-family: 'QCB Orbitron'", wordmark_svg)
            self.assertIn("data:font/woff2;base64,", wordmark_svg)
            self.assertTrue((skill_root / "scripts" / "build_wordmark_svg.py").is_file())
            skill_text = (skill_root / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("## Routing del plugin e adattatore MCP", skill_text)
            self.assertIn("preview_quote_card", skill_text)
            self.assertIn("quote_card_builder_open_editor", skill_text)
            self.assertIn("quote_card_builder_open_workspace", skill_text)
            self.assertIn("apri subito l'editor con quella frase", skill_text)
            self.assertIn("workspace locale", skill_text)
            self.assertIn("produce_quote_card", skill_text)
            self.assertIn("La sola apertura", skill_text)
            self.assertIn("La palette non è mai tono o mood", skill_text)
            self.assertIn("quote_card_builder_headless", skill_text)
            self.assertIn("approved_preview_sha256", skill_text)
            self.assertFalse(any(skill_root.rglob("__pycache__")))

    def test_zip_has_required_plugin_layout(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "quote-card-builder-plugin.zip"
            BUILD_PLUGIN.build_zip(output)
            with zipfile.ZipFile(output) as archive:
                names = set(archive.namelist())
            prefix = "quote-card-builder/"
            self.assertIn(prefix + ".codex-plugin/plugin.json", names)
            self.assertIn(prefix + ".mcp.json", names)
            self.assertIn(prefix + "skills/quote-card-builder/scripts/mcp_server.py", names)
            self.assertIn(prefix + "skills/quote-card-builder/scripts/mcp_app.py", names)
            self.assertIn(prefix + "skills/quote-card-builder/requirements-mcp.txt", names)
            self.assertIn(prefix + "skills/quote-card-builder/SKILL.md", names)
            self.assertIn(prefix + "skills/quote-card-builder/assets/card-editor/index.html", names)
            self.assertIn(prefix + "skills/quote-card-builder/assets/card-editor/fonts/Barlow-Regular.ttf", names)
            self.assertIn(prefix + "skills/quote-card-builder/assets/card-editor/fonts/Orbitron-Variable.ttf", names)
            self.assertIn(prefix + "skills/quote-card-builder/assets/card-editor/fonts/Barlow-Regular-latin.woff2", names)
            self.assertIn(prefix + "skills/quote-card-builder/assets/card-editor/fonts/Orbitron-Variable-latin.woff2", names)
            self.assertIn(prefix + "skills/quote-card-builder/assets/card-editor/vincos-lockup-white.svg", names)
            self.assertIn(prefix + "skills/quote-card-builder/assets/card-editor/quote-card-builder-wordmark.svg", names)


if __name__ == "__main__":
    unittest.main()
