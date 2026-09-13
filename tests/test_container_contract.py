import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


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
            "render_quote_card.py",
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
        self.assertIn("PORT=8080", dockerfile)

    def test_build_context_excludes_session_artifacts(self):
        ignored = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
        self.assertIn("work/", ignored)
        self.assertIn(".git", ignored)
        self.assertNotIn("assets/", ignored)


if __name__ == "__main__":
    unittest.main()
