"""Release identity catches drift between packaged sources and runtime inputs."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("build_identity_builder", ROOT / "scripts/build_plugin_package.py")
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


class BuildIdentityTests(unittest.TestCase):
    def test_identity_covers_every_packaged_file_and_is_reproducible(self):
        with tempfile.TemporaryDirectory() as directory:
            package = BUILDER.build_directory(Path(directory))
            original = (package / "BUILD-INFO.json").read_bytes()
            identity = json.loads(original)
            actual = {
                path.relative_to(package).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in package.rglob("*") if path.is_file() and path.name != "BUILD-INFO.json"
            }
            self.assertEqual(identity["files"], actual)
            canonical = json.dumps(actual, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            self.assertEqual(identity["content_sha256"], hashlib.sha256(canonical.encode()).hexdigest())
            rebuilt = BUILDER.build_directory(Path(directory))
            self.assertEqual(original, (rebuilt / "BUILD-INFO.json").read_bytes())

    def test_container_dependency_drift_is_rejected(self):
        original = Path.read_text
        def altered(path, *args, **kwargs):
            text = original(path, *args, **kwargs)
            return text + "\nunexpected-package==1.0\n" if path == ROOT / "requirements-mcp.txt" else text
        with patch.object(Path, "read_text", altered):
            with self.assertRaisesRegex(ValueError, "dipendenze del container"):
                BUILDER.validate_template()

    def test_stale_project_lock_version_is_rejected(self):
        original = Path.read_text
        import tomllib
        version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
        def altered(path, *args, **kwargs):
            text = original(path, *args, **kwargs)
            return text.replace(f'version = "{version}"', 'version = "0.0.0"') if path == ROOT / "uv.lock" else text
        with patch.object(Path, "read_text", altered):
            with self.assertRaisesRegex(ValueError, "lockfile"):
                BUILDER.validate_template()
