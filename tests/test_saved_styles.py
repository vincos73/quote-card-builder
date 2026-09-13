import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location("saved_styles", ROOT / "scripts" / "saved_styles.py")
STYLES = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(STYLES)


class SavedStylesTests(unittest.TestCase):
    def fixture(self, root: Path):
        font = root / "regular.ttf"; font.write_bytes(b"font")
        logo = root / "logo.svg"; logo.write_text("<svg/>", encoding="utf-8")
        text = "Una frase\ncon a capo."
        brand = {"name": "Test", "colors": {"primary": "#072743", "accent": "#E3F4FF", "background": "#FEFDFB", "text": "#323232"}, "font": {"family": "Arial", "regular_path": str(font)}, "logo": {"dark_path": str(logo)}}
        return {"schema_version": "0.4", "state": "contenuto_approvato", "revision": 3,
                "content": {"text": text, "styles": [{"start": 0, "end": 4, "type": "bold"}], "emphasis": "frase", "alt_text": "alt", "attribution": {"label": "Fonte", "role": "publisher"}},
                "brand": brand, "direction": "editorial", "presentation": {"logo_mode": "auto", "graphic_mode": "auto", "graphic_variant": "cover", "graphic_seed": 42, "output_mode": "all"},
                "formats": [{"id": "4x5", "width": 1440, "height": 1800, "lines": ["Una frase", "con a capo."], "text_scale": .95, "vertical_position": "upper"}],
                "source": {"title": "private"}, "output": {}}

    def test_persistence_excludes_editorial_content_and_roundtrips_seed(self):
        with tempfile.TemporaryDirectory() as directory:
            root, store = Path(directory), Path(directory) / "styles.json"
            manifest = self.fixture(root)
            saved = STYLES.save_style("Editorial Cover", manifest, path=store)
            data = json.loads(store.read_text(encoding="utf-8"))
            self.assertEqual(42, saved["presentation"]["graphic_seed"])
            self.assertNotIn("content", data["styles"][0]); self.assertNotIn("source", data["styles"][0])
            self.assertEqual(saved, STYLES.get_style(saved["id"], store))

    def test_apply_keeps_current_text_wrapping_and_formatting(self):
        with tempfile.TemporaryDirectory() as directory:
            root, store = Path(directory), Path(directory) / "styles.json"
            original = self.fixture(root); style = STYLES.save_style("Style", original, path=store)
            current = json.loads(json.dumps(original)); current["revision"] = 8; current["content"]["text"] = "Testo corrente"; current["formats"][0]["lines"] = ["Testo", "corrente"]
            applied = STYLES.apply_style(style["id"], current, current, store)
            self.assertEqual("Testo corrente", applied["content"]["text"]); self.assertEqual(["Testo", "corrente"], applied["formats"][0]["lines"])
            self.assertEqual(original["content"]["styles"], applied["content"]["styles"]); self.assertEqual(8, applied["revision"])

    def test_raw_draft_save_uses_its_canonical_palette(self):
        with tempfile.TemporaryDirectory() as directory:
            root, store = Path(directory), Path(directory) / "styles.json"
            manifest = self.fixture(root)
            saved = STYLES.save_style("Bosco", {"palette": {
                "primary": "#123abc", "accent": "#e3f4ff", "background": "#fefdfb", "text": "#323232",
            }}, manifest, store)
            self.assertEqual("#123ABC", saved["brand"]["colors"]["primary"])
            self.assertEqual("#E3F4FF", saved["brand"]["colors"]["accent"])

    def test_missing_asset_and_invalid_seed_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); manifest = self.fixture(root)
            manifest["brand"]["font"]["regular_path"] = str(root / "gone.ttf")
            with self.assertRaisesRegex(ValueError, "Asset"):
                STYLES.save_style("Missing", manifest, path=root / "styles.json")
            manifest = self.fixture(root); manifest["presentation"]["graphic_seed"] = 1000000
            with self.assertRaisesRegex(ValueError, "graphic_seed"):
                STYLES.save_style("Bad", manifest, path=root / "styles.json")

    def test_gradient_is_an_editorial_style_and_roundtrips_seed(self):
        with tempfile.TemporaryDirectory() as directory:
            root, store = Path(directory), Path(directory) / "styles.json"
            manifest = self.fixture(root)
            manifest["presentation"]["graphic_variant"] = "gradient"
            manifest["presentation"]["graphic_seed"] = 999999
            saved = STYLES.save_style("Gradient", manifest, path=store)
            self.assertEqual("editorial", saved["direction"])
            self.assertEqual("gradient", saved["presentation"]["graphic_variant"])
            self.assertEqual(999999, STYLES.get_style(saved["id"], store)["presentation"]["graphic_seed"])

    def test_listing_tolerates_one_stale_style_when_another_is_ready(self):
        with tempfile.TemporaryDirectory() as directory:
            root, store = Path(directory), Path(directory) / "styles.json"
            manifest = self.fixture(root)
            ready = STYLES.save_style("Ready", manifest, path=store)
            stale_manifest = self.fixture(root)
            stale_manifest["brand"]["font"]["regular_path"] = str(root / "removed.ttf")
            stale = json.loads(store.read_text(encoding="utf-8"))
            stale["styles"].append({**ready, "id": "stale-style", "name": "Stale", "brand": stale_manifest["brand"]})
            store.write_text(json.dumps(stale), encoding="utf-8")
            self.assertEqual({"Ready", "Stale"}, {item["name"] for item in STYLES.list_styles(store)})
            with self.assertRaisesRegex(ValueError, "Asset"):
                STYLES.get_style("stale-style", store)


if __name__ == "__main__": unittest.main()
