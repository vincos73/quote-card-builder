"""Tests for preserving model-selected quote layout and emphasis on first open."""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import mcp_server


class InitialCompositionTests(unittest.TestCase):
    def setUp(self):
        self.lines = [
            "Il futuro non si prevede.",
            "Si costruisce con scelte",
            "che trasformano le idee",
            "in risultati concreti.",
        ]
        self.text = "\n".join(self.lines)
        self.styles = [
            {"start": 0, "end": len(self.lines[0]), "type": "bold"},
            {
                "start": self.text.index("scelte"),
                "end": self.text.index("scelte") + len("scelte"),
                "type": "italic",
            },
            {
                "start": self.text.index("risultati concreti."),
                "end": len(self.text),
                "type": "highlight",
            },
        ]

    @staticmethod
    def quote_font_size(svg: str) -> float:
        match = re.search(r'<text class="quote"[^>]*font-size="([0-9.]+)"', svg)
        if not match:
            raise AssertionError("canonical SVG did not expose a fitted quote font size")
        return float(match.group(1))

    def test_open_editor_renders_four_semantic_lines_and_explicit_emphasis(self):
        result = mcp_server.quote_card_builder_open_editor(
            text=self.text,
            lines=self.lines,
            styles=self.styles,
            attribution="",
            profile_mode="neutral",
            transformation="VERBATIM",
            evidence_status="VERIFIED",
        )
        self.assertFalse(result.is_error)
        output = result.structured_content
        state = output["editor_state"]
        svg = result.meta["quoteCard"]["svg"]

        self.assertTrue(output["valid"])
        self.assertTrue(output["rendered"])
        self.assertEqual(self.text, state["text"])
        self.assertEqual(self.lines, state["lines"])
        self.assertEqual(self.styles, state["styles"])
        self.assertEqual("VERBATIM", state["transformation"])
        self.assertEqual("VERIFIED", state["evidence_status"])
        self.assertEqual("", state["attribution"])
        self.assertEqual("neutral", state["profile_mode"])
        self.assertIn('<tspan font-weight="700">Il futuro non si prevede.</tspan>', svg)
        self.assertIn('<tspan font-style="italic">scelte</tspan>', svg)
        self.assertIn('class="highlight-marker"', svg)

        one_line = mcp_server.quote_card_builder_open_editor(
            text=" ".join(self.lines),
            styles=[],
            attribution="",
            profile_mode="neutral",
            transformation="VERBATIM",
            evidence_status="VERIFIED",
        )
        one_line_svg = one_line.meta["quoteCard"]["svg"]
        self.assertGreater(self.quote_font_size(svg), self.quote_font_size(one_line_svg) * 1.5)

    def test_open_editor_infers_lines_from_newlines_when_lines_are_omitted(self):
        result = mcp_server.quote_card_builder_open_editor(
            text=self.text,
            styles=self.styles,
            attribution="",
            profile_mode="neutral",
            transformation="VERBATIM",
            evidence_status="VERIFIED",
        )
        state = result.structured_content["editor_state"]
        self.assertEqual(self.text, state["text"])
        self.assertEqual(self.lines, state["lines"])
        self.assertEqual(self.styles, state["styles"])

    def test_open_editor_rejects_lines_that_change_words_or_punctuation(self):
        with self.assertRaisesRegex(ValueError, "preserve the quote's exact words and punctuation"):
            mcp_server.quote_card_builder_open_editor(
                text=self.text,
                lines=[
                    "Il futuro non si prevede.",
                    "Si costruisce con scelte",
                    "che trasformano le idee",
                    "in risultati diversi.",
                ],
                styles=self.styles,
            )

    def test_style_offsets_count_unicode_code_points_in_canonical_text(self):
        text = "🌱 Cresci ogni giorno."
        styles = [{"start": 2, "end": 8, "type": "bold"}]
        result = mcp_server.quote_card_builder_open_editor(
            text=text,
            styles=styles,
            attribution="",
            profile_mode="neutral",
            transformation="VERBATIM",
            evidence_status="VERIFIED",
        )
        self.assertFalse(result.is_error)
        state = result.structured_content["editor_state"]
        self.assertEqual(text, state["text"])
        self.assertEqual(styles, state["styles"])
        self.assertIn('<tspan font-weight="700">Cresci</tspan>', result.meta["quoteCard"]["svg"])

        out_of_codepoint_range = mcp_server.quote_card_builder_open_editor(
            text=text,
            styles=[{"start": len(text), "end": len(text) + 1, "type": "bold"}],
            attribution="",
            profile_mode="neutral",
            transformation="VERBATIM",
            evidence_status="VERIFIED",
        )
        self.assertTrue(out_of_codepoint_range.is_error)
        self.assertFalse(out_of_codepoint_range.structured_content["valid"])

    def test_explicit_empty_styles_keep_multiline_quote_plain(self):
        plain_lines = ["Una frase rimane", "semplice e integra."]
        text = "\n".join(plain_lines)
        result = mcp_server.quote_card_builder_open_editor(
            text=text,
            lines=plain_lines,
            styles=[],
            attribution="",
            profile_mode="neutral",
            transformation="VERBATIM",
            evidence_status="VERIFIED",
        )
        state = result.structured_content["editor_state"]
        svg = result.meta["quoteCard"]["svg"]
        self.assertEqual(text, state["text"])
        self.assertEqual(plain_lines, state["lines"])
        self.assertEqual([], state["styles"])
        self.assertNotIn('font-weight="700"', svg)
        self.assertNotIn('class="highlight-marker"', svg)


if __name__ == "__main__":
    unittest.main()
