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
    def test_template_is_valid_and_marketplace_ready_in_english(self):
        BUILD_PLUGIN.validate_template()
        manifest = json.loads(
            (ROOT / "plugin" / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["version"], "1.7.13")
        self.assertEqual(manifest["interface"]["capabilities"], ["Interactive", "Read"])
        self.assertIn("quote card", manifest["interface"]["shortDescription"].lower())
        self.assertIn("guided editor", manifest["interface"]["shortDescription"].lower())
        self.assertEqual(len(manifest["interface"]["defaultPrompt"]), 3)
        self.assertEqual(manifest["mcpServers"], "./.mcp.json")

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
            self.assertIn("produce_quote_card", skill_text)
            self.assertIn("La sola apertura", skill_text)
            self.assertIn("Il terzo dato non è mai tono o mood", skill_text)
            self.assertIn("non sostituire mai l'app con generazione immagini", skill_text)
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
