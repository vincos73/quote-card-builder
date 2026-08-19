import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "scripts" / "brand_profiles.py"
SPEC = importlib.util.spec_from_file_location("brand_profiles", MODULE_PATH)
PROFILES = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(PROFILES)


def brand(root: Path | None = None):
    result = {
        "name": "Vincos",
        "colors": {
            "primary": "#072743",
            "accent": "#E3F4FF",
            "background": "#FEFDFB",
            "text": "#323232",
        },
        "font": {"family": "Barlow"},
    }
    if root is not None:
        result["font"]["regular_path"] = str(root / "Barlow-Regular.ttf")
        result["logo"] = {"dark_path": str(root / "logo.svg")}
    return result


class BrandProfileTests(unittest.TestCase):
    def test_saves_and_lists_a_profile_outside_the_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Path(directory) / "profiles.json"
            saved = PROFILES.save_profile("Vincos Social", brand(), store)
            profiles = PROFILES.list_profiles(store)
            payload = json.loads(store.read_text(encoding="utf-8"))
        self.assertEqual("Vincos Social", saved["name"])
        self.assertEqual(1, len(profiles))
        self.assertEqual("Vincos", profiles[0]["brand_name"])
        self.assertNotIn("content", payload["profiles"][0])
        self.assertNotIn("alt_text", json.dumps(payload))

    def test_same_name_updates_in_place(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Path(directory) / "profiles.json"
            first = PROFILES.save_profile("Vincos", brand(), store)
            changed = brand()
            changed["colors"]["accent"] = "#FFFFFF"
            second = PROFILES.save_profile(" vincos ", changed, store)
            profiles = PROFILES.list_profiles(store)
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(1, len(profiles))
        self.assertEqual("#FFFFFF", profiles[0]["colors"]["accent"])

    def test_asset_status_reports_stale_profile_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profile_brand = brand(root)
            (root / "Barlow-Regular.ttf").write_bytes(b"font")
            status = PROFILES.asset_status(profile_brand)
        self.assertFalse(status["ready"])
        self.assertEqual(1, len(status["missing"]))
        self.assertTrue(status["missing"][0].endswith("logo.svg"))

    def test_rejects_invalid_or_oversized_names_and_colors(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Path(directory) / "profiles.json"
            with self.assertRaises(ValueError):
                PROFILES.save_profile("", brand(), store)
            invalid = brand()
            invalid["colors"]["primary"] = "navy"
            with self.assertRaises(ValueError):
                PROFILES.save_profile("Invalid", invalid, store)

    def test_get_profile_returns_the_full_explicit_brand(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Path(directory) / "profiles.json"
            saved = PROFILES.save_profile("Vincos", brand(), store)
            restored = PROFILES.get_profile(saved["id"], store)
        self.assertEqual(brand(), restored["brand"])
        self.assertEqual(PROFILES.brand_fingerprint(brand()), restored["fingerprint"])

    def test_relative_assets_are_frozen_as_absolute_profile_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            relative = brand()
            relative["font"]["regular_path"] = "assets/Barlow-Regular.ttf"
            resolved = PROFILES.resolve_brand_assets(relative, root)
        self.assertEqual(str((root / "assets" / "Barlow-Regular.ttf").resolve()), resolved["font"]["regular_path"])


if __name__ == "__main__":
    unittest.main()
