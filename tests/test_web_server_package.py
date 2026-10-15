"""The web server source can be rebuilt without historical work snapshots."""

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("build_web_server_package", ROOT / "scripts/build_web_server_package.py")
BUILD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD)


class WebServerPackageTests(unittest.TestCase):
    def test_source_is_complete_and_has_no_work_or_user_configuration(self):
        files, info = BUILD.payload()
        self.assertTrue({"Dockerfile", "pyproject.toml", "requirements-mcp.txt", "uv.lock", ".gcloudignore",
                         "scripts/visual_grammars.py", "scripts/grammar_sessions.py", "scripts/inspect_render.py",
                         "assets/card-editor/fonts/Barlow-Regular.ttf", "assets/card-editor/fonts/Barlow-Bold.ttf"} <= set(files))
        self.assertIn("assets/urban/urban-xerox-lime-v1.png", files)
        self.assertNotIn("assets/urban/urban-xerox-lime-reference.png", files)
        self.assertTrue({"assets/card-editor/fonts/BarlowCondensed-Black.ttf",
                         "assets/card-editor/fonts/BarlowCondensed-OFL.txt"} <= set(files))
        self.assertFalse(any(name.startswith(("work/", "dist/", ".agents/", ".codex/")) for name in files))
        self.assertNotIn("scripts/card_review_server.py", files)
        self.assertNotIn("scripts/saved_styles.py", files)
        self.assertEqual(len(files) - 1, info["file_count"])
        self.assertEqual("none", info["auth"])
        self.assertEqual(BUILD.FEATURES, info["features"])
        for name, expected in info["files"].items():
            self.assertEqual(expected, hashlib.sha256(files[name]).hexdigest())

    def test_clean_source_subset_builds_without_any_historical_snapshot(self):
        with tempfile.TemporaryDirectory() as temporary:
            clone = Path(temporary).resolve() / "clone"
            for name, content in BUILD.source_files().items():
                target = clone / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
            (clone / ".agents").mkdir()
            (clone / ".agents" / "private.json").write_text("private test marker")
            cloned_files, cloned_info = BUILD.payload(clone)
            original_files, original_info = BUILD.payload()
            self.assertEqual(original_info["content_sha256"], cloned_info["content_sha256"])
            self.assertEqual(original_files, cloned_files)
            self.assertFalse((clone / "work").exists())

    def test_metadata_uses_canonical_versions_without_importing_the_runtime(self):
        files = BUILD.source_files()
        current = BUILD.build_info(files)
        version_declaration = f'version = "{current["version"]}"'.encode()
        files["pyproject.toml"] = files["pyproject.toml"].replace(version_declaration, b'version = "2.7.4"', 1)
        files["scripts/mcp_app.py"] = files["scripts/mcp_app.py"].replace(current["ui_version"].encode(), b"v9.99")
        info = BUILD.build_info(files)
        self.assertEqual("2.7.4", info["version"])
        self.assertEqual("v9.99", info["ui_version"])

    def test_archive_and_directory_are_identical_and_checksums_are_reproducible(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary).resolve()
            files, _info = BUILD.payload()
            directory = BUILD.build_directory(base / "context", contents=files)
            archive = BUILD.build_zip(base / "server.zip", contents=files)
            second = BUILD.build_zip(base / "second.zip", contents=files)
            self.assertEqual(archive.read_bytes(), second.read_bytes())
            expected_hash = hashlib.sha256(archive.read_bytes()).hexdigest()
            self.assertEqual(f"{expected_hash}  server.zip\n", archive.with_suffix(".sha256").read_text())
            with zipfile.ZipFile(archive) as package:
                self.assertIsNone(package.testzip())
                self.assertEqual({f"{BUILD.NAME}/{name}" for name in files}, set(package.namelist()))
                for name in files:
                    self.assertEqual((directory / name).read_bytes(), package.read(f"{BUILD.NAME}/{name}"))

    def test_frozen_directory_and_symlink_outputs_are_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary).resolve()
            frozen = base / "frozen"; frozen.mkdir(); marker = frozen / "marker"; marker.write_text("keep")
            with self.assertRaisesRegex(ValueError, "frozen"):
                BUILD.build_directory(frozen)
            self.assertEqual("keep", marker.read_text())
            target = base / "original.zip"; target.write_bytes(b"keep")
            link = base / "link.zip"; link.symlink_to(target)
            with self.assertRaisesRegex(ValueError, "Symlink"):
                BUILD.build_zip(link)
            linked_directory = base / "linked"; linked_directory.symlink_to(frozen, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "Symlink"):
                BUILD.build_directory(linked_directory / "new-context")
            self.assertEqual(b"keep", target.read_bytes())

    def test_missing_docker_dependency_is_refused_before_building(self):
        with tempfile.TemporaryDirectory() as temporary:
            clone = Path(temporary).resolve() / "clone"
            for name, content in BUILD.source_files().items():
                if name == "scripts/visual_grammars.py":
                    continue
                target = clone / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(content)
            with self.assertRaisesRegex(ValueError, "visual_grammars"):
                BUILD.payload(clone)


if __name__ == "__main__":
    unittest.main()
