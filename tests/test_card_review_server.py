import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "scripts" / "card_review_server.py"
SPEC = importlib.util.spec_from_file_location("card_review_server", MODULE_PATH)
SERVER = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(SERVER)


def manifest():
    return {"schema_version":"0.4","state":"contenuto_approvato","revision":1,"content":{"text":"Una frase verificata.","transformation":"VERBATIM","evidence_status":"VERIFIED","use_quotation_marks":True,"emphasis":"verificata","attribution":{"label":"example.test","role":"publisher"}},"direction":"statement","presentation":{"logo_mode":"auto","show_quotation_marks":True,"graphic_mode":"auto"},"formats":[{"id":"4x5","width":1440,"height":1800,"lines":["Una frase verificata."],"text_scale":1.0,"vertical_position":"center"}],"brand":{"name":"Test","colors":{"primary":"#072743","accent":"#E3F4FF","background":"#FEFDFB","text":"#323232"},"font":{"family":"Test Sans"}},"source":{"title":"Source","locator":"test://source"},"output":{"basename":"quote"}}


class CardReviewServerTests(unittest.TestCase):
    def test_accepts_contract_04(self): self.assertEqual([], SERVER.validate_manifest(manifest()))
    def test_static_svg_asset_is_allowlisted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            logo = root / "logo.svg"
            logo.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8")
            self.assertEqual(logo.resolve(), SERVER.asset_path(root, "/logo.svg"))
            self.assertEqual("image/svg+xml", SERVER.MIME_TYPES[".svg"])
    def test_legacy_contract_without_graphic_mode_defaults_to_auto(self):
        item = manifest(); item["presentation"].pop("graphic_mode")
        self.assertEqual([], SERVER.validate_manifest(item))
    def test_accepts_selected_candidate_as_editor_seed(self):
        item = manifest(); item["state"] = "candidato_selezionato"
        self.assertEqual([], SERVER.validate_manifest(item))

    def test_text_edit_preserves_user_declarations(self):
        source = manifest()
        draft = SERVER.validate_draft({
            "base_revision": 1,
            "text": "Una frase riscritta.",
            "transformation": "PARAPHRASE",
            "evidence_status": "VERIFIED",
            "attribution": {"label": "Ada", "role": "speaker"},
            "use_quotation_marks": True,
            "emphasis": "riscritta.",
            "presentation": {"logo_mode": "auto", "show_quotation_marks": True},
            "formats": [{"id": "4x5", "width": 1440, "height": 1800, "lines": ["Una frase", "riscritta."], "text_scale": 1.0, "vertical_position": "center"}],
        }, source)
        self.assertEqual("Una frase riscritta.", draft["content"]["text"])
        self.assertEqual("PARAPHRASE", draft["content"]["transformation"])
        self.assertEqual("VERIFIED", draft["content"]["evidence_status"])
        self.assertEqual({"label": "Ada", "role": "speaker"}, draft["content"]["attribution"])
        self.assertTrue(draft["content"]["use_quotation_marks"])
        self.assertTrue(draft["presentation"]["show_quotation_marks"])
        self.assertEqual("user", draft["content"]["declared_by"])

    def test_modified_text_can_keep_user_declared_verbatim(self):
        source = manifest()
        draft = SERVER.validate_draft({
            "base_revision": 1,
            "text": "Una frase diversa.",
            "transformation": "VERBATIM",
            "emphasis": "",
            "formats": [{"id": "4x5", "width": 1440, "height": 1800, "lines": ["Una frase diversa."], "text_scale": 1.0, "vertical_position": "center"}],
        }, source)
        self.assertEqual("VERBATIM", draft["content"]["transformation"])
    def test_graphic_mode_is_editable_but_constrained(self):
        source = manifest()
        draft = SERVER.validate_draft({
            "base_revision": 1,
            "presentation": {"logo_mode": "auto", "show_quotation_marks": True, "graphic_mode": "hidden"},
        }, source)
        self.assertEqual("hidden", draft["presentation"]["graphic_mode"])
        source["presentation"]["graphic_mode"] = "custom"
        self.assertTrue(SERVER.validate_manifest(source))
    def test_output_mode_is_editable_but_constrained(self):
        source = manifest()
        draft = SERVER.validate_draft({
            "base_revision": 1,
            "presentation": {**source["presentation"], "output_mode": "1x1"},
        }, source)
        self.assertEqual("1x1", draft["presentation"]["output_mode"])
        source["presentation"]["output_mode"] = "pdf"
        self.assertTrue(SERVER.validate_manifest(source))
    def test_rejects_mutable_or_invalid_visual_contract(self):
        item = manifest(); item["revision"] = 0; item["formats"][0]["text_scale"] = 1.2
        self.assertTrue(SERVER.validate_manifest(item))
    def test_draft_preserves_editorial_content(self):
        source = manifest(); draft = SERVER.validate_draft({"base_revision":1,"direction":"editorial","emphasis":"frase","presentation":source["presentation"],"formats":source["formats"]}, source)
        self.assertEqual(source["content"]["text"], draft["content"]["text"])
        self.assertEqual("frase", draft["content"]["emphasis"])
    def test_session_rejects_rebound_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); first, second = root / "one.json", root / "two.json"
            first.write_text(json.dumps(manifest()), encoding="utf-8"); second.write_text(json.dumps(manifest()), encoding="utf-8")
            session = root / "session"; session.mkdir()
            (session / "session-state.json").write_text(json.dumps({"manifest": str(first.resolve())}), encoding="utf-8")
            with self.assertRaises(ValueError): SERVER.create_server(second, root / "session")

    def test_recorded_feedback_is_applied_before_returning(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(manifest()), encoding="utf-8")
            session_dir = root / "session"
            session_dir.mkdir()
            feedback_path = session_dir / "feedback.json"
            (session_dir / "session-state.json").write_text(json.dumps({
                "manifest": str(manifest_path.resolve()),
                "feedback_path": str(feedback_path.resolve()),
                "last_feedback_id": None,
                "applied_feedback_id": None,
            }), encoding="utf-8")
            item = manifest()
            feedback = {
                "feedback_id": "feedback-immediate", "submitted_at": "2026-08-11T00:00:00Z",
                "action": "feedback", "base_revision": 1, "editorial_responsibility": "user",
                "content": {
                    "text": item["content"]["text"],
                    "transformation": item["content"]["transformation"],
                    "evidence_status": item["content"]["evidence_status"],
                    "attribution": item["content"]["attribution"],
                    "use_quotation_marks": item["content"]["use_quotation_marks"],
                    "styles": [], "declared_by": "user",
                },
                "direction": "editorial", "emphasis": item["content"]["emphasis"],
                "presentation": item["presentation"],
                "formats": [{
                    "id": "4x5", "lines": ["Una frase verificata."],
                    "text_scale": 1.0, "vertical_position": "center",
                }],
                "overall_note": "",
            }
            result = SERVER.record_and_apply_feedback(manifest_path, session_dir, feedback)
            self.assertTrue(result["changed"])
            updated = json.loads(manifest_path.read_text(encoding="utf-8"))
            state = json.loads((session_dir / "session-state.json").read_text(encoding="utf-8"))
            self.assertEqual(2, updated["revision"])
            self.assertEqual("editorial", updated["direction"])
            self.assertEqual(state["last_feedback_id"], state["applied_feedback_id"])

    def test_empty_emphasis_is_valid(self):
        item = manifest(); item["content"]["emphasis"] = ""
        self.assertEqual([], SERVER.validate_manifest(item))

    def test_draft_accepts_spacer_rows_and_inline_styles(self):
        source = manifest()
        draft = SERVER.validate_draft({
            "base_revision": 1,
            "emphasis": "",
            "styles": [{"start": 4, "end": 9, "type": "highlight"}],
            "formats": [{
                "id": "4x5", "width": 1440, "height": 1800,
                "lines": ["Una", "", "frase verificata."],
                "text_scale": 1.0, "vertical_position": "center",
            }],
        }, source)
        self.assertEqual(["Una", "", "frase verificata."], draft["formats"][0]["lines"])
        self.assertEqual("highlight", draft["content"]["styles"][0]["type"])

    def test_rejects_invalid_inline_style(self):
        item = manifest()
        item["content"]["styles"] = [{"start": 0, "end": 999, "type": "bold"}]
        self.assertTrue(SERVER.validate_manifest(item))

    def test_session_reports_missing_and_exact_font_faces(self):
        item = manifest()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            regular = root / "Regular.ttf"; regular.write_bytes(b"regular")
            italic = root / "Italic.ttf"; italic.write_bytes(b"italic")
            item["brand"]["font"].update({"regular_path": str(regular), "italic_path": str(italic)})
            model = SERVER.session_model(item, root)
        self.assertTrue(model["font_capabilities"]["styles"]["bold"]["available"])
        self.assertFalse(model["font_capabilities"]["styles"]["bold"]["exact"])
        self.assertTrue(model["font_capabilities"]["styles"]["italic"]["exact"])

    def test_live_quality_gate_reports_checks(self):
        item = manifest()
        with tempfile.TemporaryDirectory() as directory:
            previews = SERVER.render_preview(item, Path(directory))
            qa = SERVER.preview_quality(item, previews, Path(directory))
        self.assertTrue(qa["passed"])
        self.assertIn("contrast", qa["checks"])
        self.assertIn("fitting", qa["checks"])
        self.assertEqual([], qa["warnings"])

    def test_square_contextual_fallback_fits_with_the_source_bar_indent(self):
        item = manifest()
        item["direction"] = "contextual"
        item["content"].update({
            "text": "Il passaggio non è da uomo a macchina. È dal task all’obiettivo.",
            "emphasis": "",
        })
        item["formats"] = [{
            "id": "1x1", "width": 1080, "height": 1080,
            "lines": ["Il passaggio non è", "da uomo a macchina.", "È dal task", "all’obiettivo."],
            "text_scale": 1.0, "vertical_position": "center",
        }]
        with tempfile.TemporaryDirectory() as directory:
            previews = SERVER.render_preview(item, Path(directory))
            qa = SERVER.preview_quality(item, previews, Path(directory))
        self.assertTrue(qa["passed"])
        self.assertLess(previews[0]["font_size"], 64)

    def test_semantic_combinations_are_user_owned_not_quality_failures(self):
        item = manifest()
        item["content"].update({
            "transformation": "PARAPHRASE",
            "evidence_status": "CONFLICT",
            "attribution": {"label": "Ada", "role": "speaker"},
            "use_quotation_marks": True,
        })
        with tempfile.TemporaryDirectory() as directory:
            previews = SERVER.render_preview(item, Path(directory))
            qa = SERVER.preview_quality(item, previews, Path(directory))
        self.assertTrue(qa["passed"])

    def test_live_quality_gate_flags_contrast_and_auto_fits_overflow(self):
        item = manifest()
        item["brand"]["colors"]["background"] = item["brand"]["colors"]["primary"]
        item["content"].update({"text": "Supercalifragilistichespiralidoso.", "emphasis": ""})
        item["formats"][0]["lines"] = ["Supercalifragilistichespiralidoso."]
        item["formats"][0]["text_scale"] = 1.08
        with tempfile.TemporaryDirectory() as directory:
            previews = SERVER.render_preview(item, Path(directory))
            qa = SERVER.preview_quality(item, previews, Path(directory))
        self.assertFalse(qa["passed"])
        codes = {warning["code"] for warning in qa["warnings"]}
        self.assertTrue(any(code.startswith("visual_contrast") for code in codes))
        self.assertNotIn("text_fit", codes)
        self.assertTrue(previews[0]["auto_fitted"])
        self.assertLess(previews[0]["font_size"], previews[0]["requested_font_size"])
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "quality gate"):
                SERVER.ensure_approvable(item, Path(directory))

    def test_square_variants_share_one_auto_fit_contract(self):
        item = manifest()
        item["content"].update({
            "text": "L’intelligenza artificiale non sostituisce il lavoro: ne riscrive i confini.",
            "emphasis": "ne riscrive i confini.",
        })
        item["formats"] = [{
            "id": "1x1", "width": 1080, "height": 1080,
            "lines": ["L’intelligenza artificiale", "non sostituisce il lavoro:", "ne riscrive i confini."],
            "text_scale": 1.0, "vertical_position": "center",
        }]
        for direction in ("statement", "contextual"):
            item["direction"] = direction
            with tempfile.TemporaryDirectory() as directory:
                previews = SERVER.render_preview(item, Path(directory))
                qa = SERVER.preview_quality(item, previews, Path(directory))
            self.assertTrue(qa["passed"], (direction, qa["warnings"]))
            self.assertNotIn("text_fit", {warning["code"] for warning in qa["warnings"]})


if __name__ == "__main__": unittest.main()
