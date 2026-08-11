import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


PACK = load_module("render_quote_card_pack", ROOT / "scripts" / "render_quote_card_pack.py")
FINALIZE = load_module("finalize_quote_card_pack", ROOT / "scripts" / "finalize_quote_card_pack.py")


def production_manifest(proof_path):
    text = "Un agente non si commuove per il tuo claim: confronta."
    return {
        "schema_version": "0.3",
        "state": "prova_visuale_approvata",
        "approval": {
            "direction": "statement",
            "proof_path": str(proof_path),
            "content_sha256": PACK.sha256_text(text),
            "approved_by": "user",
            "approved_at": "2026-08-10",
        },
        "content": {
            "text": text,
            "transformation": "VERBATIM",
            "evidence_status": "VERIFIED",
            "use_quotation_marks": True,
            "emphasis": "confronta.",
            "attribution": {"label": "example.test", "role": "publisher"},
        },
        "formats": [
            {
                "id": "4x5",
                "width": 1440,
                "height": 1800,
                "lines": ["Un agente non si commuove", "per il tuo claim:", "confronta."],
            },
            {
                "id": "1x1",
                "width": 1080,
                "height": 1080,
                "lines": ["Un agente non si commuove", "per il tuo claim:", "confronta."],
            },
            {
                "id": "9x16",
                "width": 1080,
                "height": 1920,
                "lines": ["Un agente", "non si commuove", "per il tuo claim:", "confronta."],
            },
        ],
        "brand": {
            "name": "Test Brand",
            "colors": {
                "primary": "#072743",
                "accent": "#E3F4FF",
                "background": "#FEFDFB",
                "text": "#323232",
            },
            "font": {"family": "Test Sans"},
        },
        "source": {"title": "Test source", "locator": "test://source"},
        "presentation": {"logo_mode": "auto", "show_quotation_marks": True, "graphic_mode": "auto"},
        "output": {"basename": "test-quote"},
    }


class ProductionManifestTests(unittest.TestCase):
    def test_accepts_approved_multi_format_manifest(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            proof_path = Path(temp_dir) / "proof.png"
            proof_path.write_bytes(b"proof")
            manifest = production_manifest(proof_path)
            self.assertEqual([], PACK.validate_production_manifest(manifest, Path(temp_dir)))

    def test_rejects_content_changed_after_approval(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            proof_path = Path(temp_dir) / "proof.png"
            proof_path.write_bytes(b"proof")
            manifest = production_manifest(proof_path)
            manifest["content"]["text"] += " Cambiato."
            codes = {error["code"] for error in PACK.validate_production_manifest(manifest, Path(temp_dir))}
            self.assertIn("content_changed", codes)

    def test_rejects_invalid_ratio_and_changed_lines(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            proof_path = Path(temp_dir) / "proof.png"
            proof_path.write_bytes(b"proof")
            manifest = production_manifest(proof_path)
            manifest["formats"][1]["height"] = 1200
            manifest["formats"][2]["lines"][0] = "Un algoritmo"
            codes = {error["code"] for error in PACK.validate_production_manifest(manifest, Path(temp_dir))}
            self.assertIn("ratio", codes)
            self.assertIn("text_changed", codes)

    def test_rejects_unsafe_visual_tuning(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            proof_path = Path(temp_dir) / "proof.png"
            proof_path.write_bytes(b"proof")
            manifest = production_manifest(proof_path)
            manifest["formats"][0]["text_scale"] = 1.2
            manifest["formats"][1]["vertical_position"] = "free"
            manifest["presentation"] = {"logo_mode": "custom", "show_quotation_marks": True, "graphic_mode": "custom"}
            codes = {error["code"] for error in PACK.validate_production_manifest(manifest, Path(temp_dir))}
            self.assertIn("range", codes)
            self.assertIn("enum", codes)

    def test_output_mode_selects_all_or_one_aspect_ratio(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            proof_path = Path(temp_dir) / "proof.png"
            proof_path.write_bytes(b"proof")
            manifest = production_manifest(proof_path)
            manifest["presentation"]["output_mode"] = "1x1"
            manifest["formats"] = [manifest["formats"][1]]
            self.assertEqual([], PACK.validate_production_manifest(manifest, Path(temp_dir)))
            manifest["presentation"]["output_mode"] = "all"
            codes = {error["code"] for error in PACK.validate_production_manifest(manifest, Path(temp_dir))}
            self.assertIn("selection", codes)

    def test_png_pack_discards_intermediate_svgs_by_default(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            proof_path = temp_path / "proof.png"
            proof_path.write_bytes(b"proof")
            manifest = production_manifest(proof_path)
            manifest_path = temp_path / "manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            output_dir = temp_path / "output"
            node = temp_path / "node"; node.write_bytes(b"node")
            modules = temp_path / "node_modules"; modules.mkdir()

            def fake_convert(_svg, png, _node, _modules, _width, _height):
                png.write_bytes(b"png")

            with mock.patch.object(PACK.proof, "convert_with_sharp", side_effect=fake_convert):
                result = PACK.render_pack(
                    manifest, manifest_path, output_dir, "required", node, modules, "auto"
                )
            self.assertTrue(all(item["svg"] is None for item in result["formats"]))
            self.assertFalse(list(output_dir.glob("*.svg")))
            self.assertTrue(all(item["png"] for item in result["formats"]))

    def test_pack_hides_the_direction_graphic_in_every_format(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            proof_path = temp_path / "proof.png"
            proof_path.write_bytes(b"proof")
            manifest = production_manifest(proof_path)
            manifest["presentation"]["graphic_mode"] = "hidden"
            manifest_path = temp_path / "manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            output_dir = temp_path / "output"
            self.assertEqual(0, PACK.main([str(manifest_path), "--output-dir", str(output_dir), "--png", "never"]))
            for svg_path in output_dir.glob("*.svg"):
                self.assertNotIn('class="direction-graphic', svg_path.read_text(encoding="utf-8"))

    def test_cli_renders_and_finalizes_pack(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            proof_path = temp_path / "proof.png"
            proof_path.write_bytes(b"proof")
            manifest_path = temp_path / "manifest.json"
            manifest_path.write_text(json.dumps(production_manifest(proof_path)), encoding="utf-8")
            output_dir = temp_path / "output"
            self.assertEqual(
                0,
                PACK.main([str(manifest_path), "--output-dir", str(output_dir), "--png", "never"]),
            )
            qa_path = output_dir / "test-quote-statement-production-qa.json"
            qa = json.loads(qa_path.read_text(encoding="utf-8"))
            self.assertEqual("qa", qa["state"])
            self.assertEqual("automatic_checks_passed", qa["status"])
            self.assertTrue(all((output_dir / item["svg"]["path"]).is_file() for item in qa["formats"]))
            self.assertEqual(
                0,
                FINALIZE.main([str(qa_path), "--all-formats", "--reviewer", "test-suite"]),
            )
            finalized = json.loads(qa_path.read_text(encoding="utf-8"))
            self.assertEqual("consegnato", finalized["state"])
            self.assertEqual("passed", finalized["status"])

    def test_finalizer_rejects_tampered_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            proof_path = temp_path / "proof.png"
            proof_path.write_bytes(b"proof")
            manifest_path = temp_path / "manifest.json"
            manifest_path.write_text(json.dumps(production_manifest(proof_path)), encoding="utf-8")
            output_dir = temp_path / "output"
            PACK.main([str(manifest_path), "--output-dir", str(output_dir), "--png", "never"])
            qa_path = output_dir / "test-quote-statement-production-qa.json"
            qa = json.loads(qa_path.read_text(encoding="utf-8"))
            first_svg = output_dir / qa["formats"][0]["svg"]["path"]
            first_svg.write_text("tampered", encoding="utf-8")
            self.assertEqual(
                1,
                FINALIZE.main([str(qa_path), "--all-formats", "--reviewer", "test-suite"]),
            )


if __name__ == "__main__":
    unittest.main()
