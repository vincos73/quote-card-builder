import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location("apply_card_review", ROOT / "scripts" / "apply_card_review.py")
APPLIER = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(APPLIER)


def manifest():
    text = "Un agente non si commuove per il tuo claim: confronta."
    return {
        "schema_version": "0.4", "revision": 3, "state": "prova_visuale_approvata", "direction": "statement",
        "content": {"text": text, "transformation": "VERBATIM", "evidence_status": "VERIFIED",
                    "emphasis": "confronta.", "use_quotation_marks": True,
                    "attribution": {"label": "vincos.it", "role": "publisher"}},
        "presentation": {"logo_mode": "auto", "show_quotation_marks": True, "graphic_mode": "auto"},
        "formats": [{"id": "4x5", "width": 1440, "height": 1800, "lines": [text], "text_scale": 1.0, "vertical_position": "center"}],
        "brand": {"name": "Brand"},
    }


class ApplyCardReviewTests(unittest.TestCase):
    def make_files(self, feedback):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        manifest_path, feedback_path = root / "manifest.json", root / "feedback.json"
        manifest_path.write_text(json.dumps(manifest()), encoding="utf-8")
        feedback_path.write_text(json.dumps(feedback), encoding="utf-8")
        (root / "session-state.json").write_text(json.dumps({
            "manifest": str(manifest_path), "feedback_path": str(feedback_path),
            "last_feedback_id": "f-1", "manifest_revision": 3,
        }), encoding="utf-8")
        return temp, root, manifest_path, feedback_path

    def test_applies_only_permitted_changes_atomically(self):
        feedback = {"feedback_id": "f-1", "base_revision": 3, "action": "feedback", "direction": "editorial",
                    "emphasis": "claim:", "presentation": {"logo_mode": "hidden", "graphic_mode": "hidden", "output_mode": "1x1"},
                    "formats": [{"id": "4x5", "lines": ["Un agente non si commuove per il tuo claim: confronta."], "text_scale": 1.04, "vertical_position": "upper"}]}
        temp, root, manifest_path, feedback_path = self.make_files(feedback)
        with temp:
            result = APPLIER.apply_review(manifest_path, feedback_path, root)
            saved = json.loads(manifest_path.read_text())
            state = json.loads((root / "session-state.json").read_text())
            self.assertTrue(result["changed"])
            self.assertEqual(4, saved["revision"])
            self.assertEqual("Brand", saved["brand"]["name"])
            self.assertEqual("hidden", saved["presentation"]["graphic_mode"])
            self.assertEqual("1x1", saved["presentation"]["output_mode"])
            self.assertEqual("f-1", state["applied_feedback_id"])
            self.assertTrue(list(root.glob("manifest-r3.backup.json")))

    def test_rejects_content_or_format_identity_change(self):
        feedback = {"feedback_id": "f-1", "base_revision": 3, "action": "feedback", "content": {"text": "alterato"}}
        temp, root, manifest_path, feedback_path = self.make_files(feedback)
        with temp:
            with self.assertRaises(APPLIER.ReviewError):
                APPLIER.apply_review(manifest_path, feedback_path, root)
            self.assertEqual(3, json.loads(manifest_path.read_text())["revision"])

    def test_approve_only_requests_approval(self):
        feedback = {"feedback_id": "f-1", "base_revision": 3, "action": "approve", "direction": "editorial"}
        temp, root, manifest_path, feedback_path = self.make_files(feedback)
        with temp:
            result = APPLIER.apply_review(manifest_path, feedback_path, root)
            self.assertTrue(result["approval_requested"])
            self.assertEqual("f-1", json.loads((root / "session-state.json").read_text())["applied_feedback_id"])
            self.assertEqual("editorial", json.loads(manifest_path.read_text())["direction"])

    def test_approve_applies_current_editorial_declarations_in_same_batch(self):
        edited = "Testo scelto interamente dall’utente."
        feedback = {
            "feedback_id": "f-1", "base_revision": 3, "action": "approve",
            "editorial_responsibility": "user",
            "content": {
                "text": edited, "transformation": "VERBATIM", "evidence_status": "CONFLICT",
                "attribution": {"label": "Ada", "role": "speaker"},
                "use_quotation_marks": True, "declared_by": "user",
            },
            "emphasis": "",
            "presentation": {"logo_mode": "auto", "show_quotation_marks": True},
            "formats": [{"id": "4x5", "lines": [edited], "text_scale": 1.0, "vertical_position": "center"}],
        }
        temp, root, manifest_path, feedback_path = self.make_files(feedback)
        with temp:
            result = APPLIER.apply_review(manifest_path, feedback_path, root)
            saved = json.loads(manifest_path.read_text())
            self.assertTrue(result["approval_requested"])
            self.assertEqual("CONFLICT", saved["content"]["evidence_status"])
            self.assertEqual({"label": "Ada", "role": "speaker"}, saved["content"]["attribution"])
            self.assertTrue(saved["presentation"]["show_quotation_marks"])

    def test_rejects_bad_lines_but_allows_quote_toggle(self):
        feedback = {"feedback_id": "f-1", "base_revision": 3, "action": "feedback",
                    "formats": [{"id": "4x5", "lines": ["Parafrasi"]}]}
        temp, root, manifest_path, feedback_path = self.make_files(feedback)
        with temp:
            with self.assertRaises(APPLIER.ReviewError):
                APPLIER.apply_review(manifest_path, feedback_path, root)
        doc = manifest(); doc["content"]["use_quotation_marks"] = False
        APPLIER._validate_patch(
            {"feedback_id": "f", "base_revision": 3, "action": "feedback", "presentation": {"show_quotation_marks": True}}, doc)

    def test_applies_spacer_rows_and_inline_styles(self):
        text = manifest()["content"]["text"]
        feedback = {
            "feedback_id": "f-1", "base_revision": 3, "action": "feedback",
            "content": {
                "styles": [
                    {"start": 0, "end": 9, "type": "bold"},
                    {"start": 44, "end": 54, "type": "highlight"},
                ],
            },
            "formats": [{
                "id": "4x5",
                "lines": ["Un agente non si commuove", "", "per il tuo claim: confronta."],
            }],
        }
        temp, root, manifest_path, feedback_path = self.make_files(feedback)
        with temp:
            APPLIER.apply_review(manifest_path, feedback_path, root)
            saved = json.loads(manifest_path.read_text())
            self.assertEqual(["Un agente non si commuove", "", "per il tuo claim: confronta."], saved["formats"][0]["lines"])
            self.assertEqual("bold", saved["content"]["styles"][0]["type"])

    def test_text_edit_is_applied_atomically_and_confirms_content(self):
        edited = "Un agente confronta i fatti."
        feedback = {
            "feedback_id": "f-1", "base_revision": 3, "action": "feedback",
            "content": {"text": edited, "transformation": "EDITED", "evidence_status": "USER_SUPPLIED", "use_quotation_marks": False},
            "emphasis": "fatti.",
            "presentation": {"logo_mode": "auto", "show_quotation_marks": False},
            "formats": [{"id": "4x5", "lines": ["Un agente", "confronta i fatti."], "text_scale": 1.0, "vertical_position": "center"}],
        }
        temp, root, manifest_path, feedback_path = self.make_files(feedback)
        with temp:
            doc = json.loads(manifest_path.read_text())
            doc["state"] = "candidato_selezionato"
            manifest_path.write_text(json.dumps(doc), encoding="utf-8")
            result = APPLIER.apply_review(manifest_path, feedback_path, root)
            saved = json.loads(manifest_path.read_text())
            self.assertTrue(result["content_confirmed"])
            self.assertEqual("contenuto_approvato", saved["state"])
            self.assertEqual(edited, saved["content"]["text"])
            self.assertEqual("EDITED", saved["content"]["transformation"])
            self.assertEqual("USER_SUPPLIED", saved["content"]["evidence_status"])
            self.assertFalse(saved["content"]["use_quotation_marks"])
            self.assertFalse(saved["presentation"]["show_quotation_marks"])
            self.assertEqual(["Un agente", "confronta i fatti."], saved["formats"][0]["lines"])

    def test_text_edit_can_keep_verified_but_must_update_format_lines(self):
        base = {"feedback_id": "f-1", "base_revision": 3, "action": "feedback",
                "content": {"text": "Testo nuovo.", "transformation": "EDITED", "evidence_status": "VERIFIED", "use_quotation_marks": False}}
        temp, root, manifest_path, feedback_path = self.make_files(base)
        with temp:
            with self.assertRaisesRegex(APPLIER.ReviewError, "tutti i formati"):
                APPLIER.apply_review(manifest_path, feedback_path, root)
        base["formats"] = [{"id": "4x5", "lines": ["Testo nuovo."], "text_scale": 1.0, "vertical_position": "center"}]
        base["emphasis"] = ""
        temp, root, manifest_path, feedback_path = self.make_files(base)
        with temp:
            result = APPLIER.apply_review(manifest_path, feedback_path, root)
            saved = json.loads(manifest_path.read_text())
            self.assertTrue(result["changed"])
            self.assertEqual("VERIFIED", saved["content"]["evidence_status"])


if __name__ == "__main__":
    unittest.main()
