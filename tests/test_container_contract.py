import ast
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def copied_sources():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8").replace("\\\n", " ")
    files = set()
    for sources in re.findall(r"(?m)^COPY\s+(.+)$", dockerfile):
        for relative in sources.split()[:-1]:
            path = ROOT / relative
            if path.is_dir():
                files.update(item for item in path.rglob("*") if item.is_file())
            else:
                files.add(path)
    return files


class ContainerContractTests(unittest.TestCase):
    def test_dockerfile_runs_one_non_root_http_mcp_service(self):
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("FROM python:3.13-slim", dockerfile)
        self.assertIn("USER app", dockerfile)
        self.assertIn('"--transport", "streamable-http"', dockerfile)
        self.assertIn('"--host", "0.0.0.0"', dockerfile)
        self.assertNotIn("COPY scripts/ ./scripts/", dockerfile)
        for filename in (
            "mcp_server.py",
            "mcp_quote_card.py",
            "mcp_app.py",
            "remote_png_store.py",
            "render_quote_card.py",
            "visual_grammars.py",
            "grammar_sessions.py",
            "inspect_render.py",
            "quote_card_contract.py",
            "rasterize.py",
        ):
            self.assertIn(f"scripts/{filename}", dockerfile)
        self.assertNotIn("scripts/card_review_server.py", dockerfile)
        self.assertNotIn("scripts/build_plugin_package.py", dockerfile)
        self.assertIn(
            "COPY assets/card-editor/vincos-lockup-white.svg ./assets/card-editor/",
            dockerfile,
        )
        self.assertIn(
            "COPY assets/card-editor/quote-card-builder-wordmark.svg ./assets/card-editor/",
            dockerfile,
        )
        self.assertIn("COPY assets/card-editor/fonts/ ./assets/card-editor/fonts/", dockerfile)
        self.assertIn("COPY assets/mcp-editor/ ./assets/mcp-editor/", dockerfile)
        self.assertIn("PORT=8080", dockerfile)
        self.assertIn("COPY pyproject.toml ./", dockerfile)

    def test_web_bundle_contains_every_transitive_local_python_import(self):
        files = copied_sources()
        bundled = {path.stem for path in files if path.parent == ROOT / "scripts" and path.suffix == ".py"}
        local = {path.stem for path in (ROOT / "scripts").glob("*.py")}
        for path in files:
            if path.parent != ROOT / "scripts" or path.suffix != ".py":
                continue
            self.assertTrue(path.is_file(), path)
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"), filename=str(path))):
                imported = ([item.name.split(".", 1)[0] for item in node.names] if isinstance(node, ast.Import)
                            else [node.module.split(".", 1)[0]] if isinstance(node, ast.ImportFrom) and node.module else [])
                missing = (set(imported) & local) - bundled
                self.assertEqual(set(), missing, f"{path.name}: local imports missing from Docker COPY: {missing}")

    def test_web_bundle_contains_no_local_editor_session_or_user_storage(self):
        files = copied_sources()
        paths = {path.relative_to(ROOT).as_posix() for path in files}
        self.assertNotIn("scripts/card_review_server.py", paths)
        self.assertNotIn("scripts/saved_styles.py", paths)
        self.assertNotIn("scripts/brand_profiles.py", paths)
        self.assertNotIn("assets/card-editor/app.js", paths)
        self.assertFalse(any(path.startswith(("work/", ".agents/", ".codex/")) for path in paths))

    def test_build_context_excludes_session_artifacts(self):
        ignored = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
        self.assertIn("work/", ignored)
        self.assertIn(".git", ignored)
        self.assertNotIn("assets/", ignored)

    def test_ci_python_matrix_matches_supported_runtime(self):
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        release = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
        self.assertIn('requires-python = ">=3.12,<3.15"', pyproject)
        self.assertIn('python-version: ["3.12", "3.13", "3.14"]', workflow)
        self.assertNotRegex(workflow, r'"3\.(?:10|11)"')
        self.assertIn('python-version: "3.12"', release)


if __name__ == "__main__":
    unittest.main()
