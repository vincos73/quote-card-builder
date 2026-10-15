import importlib.util
import json
import re
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
    def test_portable_manifest_rejects_legacy_top_level_fields(self):
        original_read = Path.read_text
        manifest_path = ROOT / "plugin" / "plugin.json"
        for field in ("skills", "mcpServers", "interface", "apps"):
            def changed_manifest(path, *args, **kwargs):
                content = original_read(path, *args, **kwargs)
                if path == manifest_path:
                    value = json.loads(content)
                    value[field] = "./legacy"
                    return json.dumps(value)
                return content
            with self.subTest(field=field), patch.object(Path, "read_text", changed_manifest):
                with self.assertRaisesRegex(ValueError, "campi root"):
                    BUILD_PLUGIN.validate_template()

    def test_package_rejects_mismatched_server_version(self):
        original_read = Path.read_text

        def changed_project(path, *args, **kwargs):
            content = original_read(path, *args, **kwargs)
            if path == ROOT / "pyproject.toml":
                return re.sub(r'(?m)^version = "[^"]+"$', 'version = "0.0.0"', content, count=1)
            return content

        with patch.object(Path, "read_text", changed_project):
            with self.assertRaisesRegex(ValueError, "versione del runtime MCP"):
                BUILD_PLUGIN.validate_template()

    def test_template_is_valid_and_marketplace_ready_in_english(self):
        BUILD_PLUGIN.validate_template()
        manifest = json.loads((ROOT / "plugin" / "plugin.json").read_text(encoding="utf-8"))
        legacy = json.loads((ROOT / "plugin" / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        interface = manifest["extensions"]["com.openai"]["interface"]
        self.assertEqual("https://agent-plugins.org/schemas/1.0.0/plugin.schema.json", manifest["$schema"])
        self.assertEqual("quote-card-builder", manifest["name"])
        self.assertEqual(manifest["version"], legacy["version"])
        self.assertEqual(interface, legacy["interface"])
        self.assertEqual(manifest["version"], BUILD_PLUGIN._skill_version())
        self.assertEqual(interface["capabilities"], ["Interactive", "Read"])
        self.assertIn("quote card", interface["shortDescription"].lower())
        self.assertIn("one populated editor", interface["longDescription"].lower())
        self.assertLessEqual(len(interface["shortDescription"]), 30)
        self.assertIn("global workspace", interface["longDescription"].lower())
        self.assertIn("drafts do not sync across devices or conversations", interface["longDescription"].lower())
        self.assertEqual(interface["defaultPrompt"], [
            "Open Quote Card Builder and turn this quote into a card.",
            "Find the strongest quote in this text and open the Quote Card Builder editor.",
            "Proceed with this link and make a quote card.",
        ])
        self.assertNotIn("skills", manifest)
        self.assertNotIn("mcpServers", manifest)

    def test_portable_mcp_manifest_and_legacy_overlay_start_the_same_stdio_runtime(self):
        portable = json.loads((ROOT / "plugin" / "mcp.json").read_text(encoding="utf-8"))
        legacy = json.loads((ROOT / "plugin" / ".mcp.json").read_text(encoding="utf-8"))
        self.assertEqual("https://agent-plugins.org/schemas/1.0.0/mcp.schema.json", portable["$schema"])
        server = portable["mcpServers"]["quote-card-builder"]
        legacy_server = legacy["mcpServers"]["quote-card-builder"]
        self.assertEqual("stdio", server["type"])
        self.assertEqual("uv", server["command"])
        self.assertEqual("uv", legacy_server["command"])
        self.assertEqual(["run", "--frozen", "python", "--local-file-delivery"], server["args"][:3] + server["args"][4:])
        self.assertEqual(server["args"][:3], legacy_server["args"][:3])
        self.assertEqual(server["args"][4:], legacy_server["args"][4:])
        self.assertTrue(server["args"][3].startswith("${PLUGIN_ROOT}/"))
        self.assertEqual("${PLUGIN_ROOT}/skills/quote-card-builder", server["cwd"])
        self.assertEqual("skills/quote-card-builder", legacy_server["cwd"])

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
            self.assertTrue((skill_root / "scripts" / "visual_grammars.py").is_file())
            self.assertTrue((skill_root / "scripts" / "grammar_sessions.py").is_file())
            self.assertTrue((skill_root / "scripts" / "inspect_render.py").is_file())
            self.assertTrue((skill_root / "assets" / "card-editor" / "fonts" / "Barlow-Regular.ttf").is_file())
            self.assertTrue((skill_root / "assets" / "card-editor" / "fonts" / "Orbitron-Variable.ttf").is_file())
            self.assertTrue((skill_root / "assets" / "card-editor" / "fonts" / "Barlow-Regular-latin.woff2").is_file())
            self.assertTrue((skill_root / "assets" / "card-editor" / "fonts" / "Orbitron-Variable-latin.woff2").is_file())
            self.assertTrue((skill_root / "assets" / "urban" / "urban-xerox-lime-reference.png").is_file())
            self.assertTrue((skill_root / "assets" / "urban" / "urban-xerox-lime-v1.png").is_file())
            self.assertTrue((skill_root / "assets" / "card-editor" / "fonts" / "BarlowCondensed-Black.ttf").is_file())
            self.assertTrue((skill_root / "assets" / "card-editor" / "fonts" / "BarlowCondensed-OFL.txt").is_file())
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
            prefix = "quote-card-builder/"
            with zipfile.ZipFile(output) as archive:
                names = set(archive.namelist())
                portable_mcp = json.loads(archive.read(prefix + "mcp.json"))
            self.assertIn(prefix + "plugin.json", names)
            self.assertIn(prefix + "mcp.json", names)
            self.assertIn(prefix + ".codex-plugin/plugin.json", names)
            self.assertIn(prefix + ".mcp.json", names)
            self.assertIn(prefix + "skills/quote-card-builder/scripts/mcp_server.py", names)
            self.assertIn(prefix + "skills/quote-card-builder/scripts/mcp_app.py", names)
            portable_entry = portable_mcp["mcpServers"]["quote-card-builder"]["args"][3].replace("${PLUGIN_ROOT}/", "")
            self.assertIn(prefix + portable_entry, names)
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
