import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "validate_quote_manifest.py"
SPEC = importlib.util.spec_from_file_location("validate_quote_manifest", MODULE_PATH)
VALIDATOR = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(VALIDATOR)


def valid_manifest():
    source_text = "La tecnologia utile non sostituisce il giudizio: lo rende più informato."
    return {
        "schema_version": "0.1",
        "state": "contenuto_approvato",
        "source": {"id": "source-1", "kind": "text", "text": source_text},
        "candidates": [
            {
                "id": "q1",
                "text": source_text,
                "transformation": "VERBATIM",
                "evidence_status": "VERIFIED",
                "evidence": [
                    {
                        "start": 0,
                        "end": len(source_text),
                        "excerpt": source_text,
                        "locator": "paragrafo 1",
                    }
                ],
                "attribution": {"label": "Autore", "role": "author"},
                "ranking": {"score": 86, "reason": "È chiara e fedele."},
            }
        ],
        "selection": {
            "candidate_id": "q1",
            "reason": "È il candidato più forte.",
            "content_approved": True,
        },
    }


class ValidateQuoteManifestTests(unittest.TestCase):
    def test_accepts_verified_verbatim(self):
        self.assertEqual([], VALIDATOR.validate_manifest(valid_manifest()))

    def test_accepts_user_supplied_verbatim_without_source_span(self):
        manifest = valid_manifest()
        candidate = manifest["candidates"][0]
        candidate["evidence_status"] = "USER_SUPPLIED"
        candidate["evidence"] = []
        self.assertEqual([], VALIDATOR.validate_manifest(manifest))

    def test_accepts_user_declared_changed_verbatim(self):
        manifest = valid_manifest()
        manifest["candidates"][0]["text"] = "La tecnologia non sostituisce mai il giudizio."
        self.assertEqual([], VALIDATOR.validate_manifest(manifest))

    def test_accepts_user_declared_paraphrase_in_personal_quotes(self):
        manifest = valid_manifest()
        candidate = manifest["candidates"][0]
        candidate["transformation"] = "PARAPHRASE"
        self.assertEqual([], VALIDATOR.validate_manifest(manifest))

    def test_accepts_user_declared_generated_speaker(self):
        manifest = valid_manifest()
        candidate = manifest["candidates"][0]
        candidate["transformation"] = "AI_GENERATED"
        candidate["evidence_status"] = "USER_SUPPLIED"
        candidate["evidence"] = []
        candidate["attribution"] = {"label": "Ada", "role": "speaker"}
        self.assertEqual([], VALIDATOR.validate_manifest(manifest))

    def test_accepts_generated_author_as_user_declaration(self):
        manifest = valid_manifest()
        candidate = manifest["candidates"][0]
        candidate["transformation"] = "AI_GENERATED"
        candidate["evidence_status"] = "USER_SUPPLIED"
        candidate["evidence"] = []
        candidate["attribution"] = {"label": "Ada", "role": "author"}
        self.assertEqual([], VALIDATOR.validate_manifest(manifest))

    def test_accepts_conflicted_selection_as_user_declaration(self):
        manifest = valid_manifest()
        manifest["candidates"][0]["evidence_status"] = "CONFLICT"
        self.assertEqual([], VALIDATOR.validate_manifest(manifest))

    def test_rejects_invalid_evidence_offsets(self):
        manifest = valid_manifest()
        manifest["candidates"][0]["evidence"][0]["end"] -= 1
        errors = VALIDATOR.validate_manifest(manifest)
        self.assertIn("span_mismatch", {error["code"] for error in errors})

    def test_core_rejects_unimplemented_visual_state(self):
        manifest = valid_manifest()
        manifest["state"] = "consegnato"
        errors = VALIDATOR.validate_manifest(manifest)
        self.assertIn("enum", {error["code"] for error in errors})


if __name__ == "__main__":
    unittest.main()
