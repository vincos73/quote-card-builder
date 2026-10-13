"""Contract checks for explicit chat edits to an already-open editor."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import mcp_server


class EditorFollowupTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = {
            "text": "La prima frase resta leggibile.",
            "format": "1x1",
            "attribution": "Fonte verificata",
            "profile_mode": "custom",
            "transformation": "VERBATIM",
            "evidence_status": "VERIFIED",
            "direction": "statement",
            "graphic_mode": "hidden",
            "graphic_variant": "default",
            "graphic_seed": 42,
            "text_scale": 0.9,
            "vertical_position": "upper",
            "palette": {"name": "Brand", "colors": {
                "primary": "#123456", "accent": "#FFF4CC",
                "background": "#FFFFFF", "text": "#111111",
            }},
            "lines": ["La prima frase", "resta leggibile."],
            "styles": [{"start": 3, "end": 8, "type": "bold"}],
            "alt_text": "Descrizione esistente",
        }

    def test_followup_merges_only_requested_fields_and_renders_full_state(self):
        result = mcp_server.quote_card_builder_update_editor(
            base_revision=7,
            base_snapshot=mcp_server.EditorState.model_validate(self.snapshot),
            patch=mcp_server.EditorPatch.model_validate({"attribution": "Fonte aggiornata"}),
        )

        self.assertFalse(result.is_error)
        self.assertTrue(result.structured_content["valid"])
        self.assertTrue(result.structured_content["rendered"])
        update = result.structured_content
        self.assertTrue(update["update"])
        self.assertEqual(7, update["base_revision"])
        self.assertEqual({"attribution": "Fonte aggiornata"}, update["patch"])
        state = update["editor_state"]
        self.assertEqual("Fonte aggiornata", state["attribution"])
        self.assertEqual("La prima frase resta leggibile.", state["text"])
        self.assertEqual("custom", state["profile_mode"])
        self.assertEqual(self.snapshot["palette"], state["palette"])
        self.assertEqual("statement", state["direction"])
        self.assertEqual(self.snapshot["lines"], state["lines"])
        self.assertEqual(self.snapshot["styles"], state["styles"])
        self.assertEqual("Descrizione esistente", state["alt_text"])
        self.assertIn("svg", result.meta["quoteCard"])

    def test_text_followup_clears_offsets_but_preserves_every_unmentioned_choice(self):
        result = mcp_server.quote_card_builder_update_editor(
            base_revision=3,
            base_snapshot=mcp_server.EditorState.model_validate(self.snapshot),
            patch=mcp_server.EditorPatch.model_validate({"text": "La nuova frase cambia solo il testo."}),
        )
        state = result.structured_content["editor_state"]

        self.assertEqual("La nuova frase cambia solo il testo.", state["text"])
        self.assertIsNone(state["lines"])
        self.assertEqual([], state["styles"])
        self.assertEqual("EDITED", state["transformation"])
        self.assertEqual("UNVERIFIED", state["evidence_status"])
        for field in (
            "format", "attribution", "profile_mode", "direction", "graphic_mode", "graphic_variant",
            "graphic_seed", "text_scale", "vertical_position", "palette", "alt_text",
        ):
            self.assertEqual(self.snapshot[field], state[field], field)

    def test_lines_only_followup_canonicalizes_text_and_remaps_styles(self):
        snapshot = {
            **self.snapshot,
            "text": "La  prima frase resta leggibile.",
            "styles": [{"start": 4, "end": 9, "type": "bold"}],
        }
        result = mcp_server.quote_card_builder_update_editor(
            base_revision=11,
            base_snapshot=mcp_server.EditorState.model_validate(snapshot),
            patch=mcp_server.EditorPatch.model_validate(
                {"lines": ["La", "prima frase resta leggibile."]}
            ),
        )

        self.assertFalse(result.is_error)
        update = result.structured_content
        state = update["editor_state"]
        canonical_text = "La\nprima frase resta leggibile."
        canonical_styles = [{"start": 3, "end": 8, "type": "bold"}]
        self.assertEqual(canonical_text, state["text"])
        self.assertEqual(["La", "prima frase resta leggibile."], state["lines"])
        self.assertEqual(canonical_styles, state["styles"])
        self.assertEqual(canonical_text, update["patch"]["text"])
        self.assertEqual(canonical_styles, update["patch"]["styles"])
        self.assertEqual("VERBATIM", state["transformation"])
        self.assertEqual("VERIFIED", state["evidence_status"])
        self.assertTrue(update["rendered"])
        svg = result.meta["quoteCard"]["svg"]
        self.assertIn(">LA</tspan>", svg)
        self.assertIn("PRIMA</tspan>", svg)
        self.assertIn("FRASE RESTA", svg)

    def test_lines_only_followup_rejects_changed_words(self):
        with self.assertRaisesRegex(ValueError, "may change line breaks and whitespace, but not quote words"):
            mcp_server.quote_card_builder_update_editor(
                base_revision=11,
                base_snapshot=mcp_server.EditorState.model_validate(self.snapshot),
                patch=mcp_server.EditorPatch.model_validate(
                    {"lines": ["La prima frase", "contiene parole diverse."]}
                ),
            )

    def test_unchanged_text_with_lines_patch_uses_the_canonical_newlines(self):
        result = mcp_server.quote_card_builder_update_editor(
            base_revision=12,
            base_snapshot=mcp_server.EditorState.model_validate(self.snapshot),
            patch=mcp_server.EditorPatch.model_validate(
                {
                    "text": self.snapshot["text"],
                    "lines": ["La prima frase", "resta leggibile."],
                }
            ),
        )
        state = result.structured_content["editor_state"]
        self.assertEqual("La prima frase\nresta leggibile.", state["text"])
        self.assertEqual(state["text"], result.structured_content["patch"]["text"])

    def test_instructions_cover_single_call_url_creation_and_followup_edits(self):
        instructions = mcp_server.mcp.instructions.lower()
        self.assertIn("readable url", instructions)
        self.assertIn("do not ask for quote, attribution, or palette confirmation", instructions)
        self.assertIn("quote_card_builder_update_editor", instructions)
        self.assertIn("do not call open_workspace/open_editor first", instructions)
        self.assertIn("editor_revision", instructions)

        opened = mcp_server.quote_card_builder_open_editor(
            text="Una frase scelta dalla pagina collegata.",
            attribution="",
            profile_mode="neutral",
            transformation="VERBATIM",
            evidence_status="VERIFIED",
        )
        state = opened.structured_content["editor_state"]
        self.assertTrue(opened.structured_content["rendered"])
        self.assertEqual("Una frase scelta dalla pagina collegata.", state["text"])
        self.assertEqual("", state["attribution"])
        self.assertEqual("neutral", state["profile_mode"])


if __name__ == "__main__":
    unittest.main()
