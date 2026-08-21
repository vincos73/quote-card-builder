import json
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
CORE = ROOT / "assets" / "card-editor" / "formatting-core.js"


@unittest.skipUnless(shutil.which("node"), "Node.js non disponibile")
class FormattingCoreTests(unittest.TestCase):
    def run_core(self, expression):
        script = (
            f"const core=require({json.dumps(str(CORE))});"
            f"process.stdout.write(JSON.stringify({expression}));"
        )
        result = subprocess.run(
            [shutil.which("node"), "-e", script],
            check=True,
            capture_output=True,
            text=True,
        )
        return json.loads(result.stdout)

    def test_blank_rows_do_not_shift_canonical_text_offsets(self):
        result = self.run_core("core.canonicalLineStart(['Riga uno','','Riga due'],2)")
        self.assertEqual(9, result)

    def test_styles_after_an_insertion_shift_without_being_removed(self):
        result = self.run_core(
            "core.remapStyleRanges([{start:9,end:17,type:'highlight'}],"
            "'Riga uno Riga due','Riga uno nuova Riga due')"
        )
        self.assertEqual([{"start": 15, "end": 23, "type": "highlight"}], result)

    def test_edit_inside_a_style_keeps_the_replacement_formatted(self):
        result = self.run_core(
            "core.remapStyleRanges([{start:4,end:7,type:'bold'}],"
            "'Uno due tre','Uno parola tre')"
        )
        self.assertEqual([{"start": 4, "end": 10, "type": "bold"}], result)

    def test_deleting_the_entire_styled_text_drops_only_that_range(self):
        result = self.run_core(
            "core.remapStyleRanges(["
            "{start:0,end:3,type:'underline'},"
            "{start:4,end:7,type:'bold'}],"
            "'Uno due tre','Uno tre')"
        )
        self.assertEqual([{"start": 0, "end": 3, "type": "underline"}], result)

    def test_accent_is_an_allowed_inline_style(self):
        result = self.run_core("Array.from(core.STYLE_TYPES).includes('accent')")
        self.assertTrue(result)

    def test_balanced_lines_avoid_an_orphan_final_word(self):
        result = self.run_core(
            "core.suggestBalancedLines('Questo momento presente, un tempo, era il futuro inimmaginabile.', 3)"
        )
        self.assertEqual(
            ["Questo momento presente,", "un tempo, era il", "futuro inimmaginabile."],
            result,
        )
        self.assertTrue(all(len(line.split()) > 1 for line in result))

    def test_balanced_lines_respect_the_session_line_limit(self):
        result = self.run_core(
            "core.suggestBalancedLines(Array(30).fill('parola').join(' '), 12, 3)"
        )
        self.assertEqual(3, len(result))
        self.assertEqual(["parola"] * 30, " ".join(result).split(" "))

    def test_invalid_session_line_limit_falls_back_to_six(self):
        result = self.run_core(
            "[undefined,null,0,-1,6,8,'8'].map((value)=>core.normalizeLineLimit(value))"
        )
        self.assertEqual([6, 6, 6, 6, 6, 8, 6], result)

    def test_outline_is_an_allowed_inline_style(self):
        result = self.run_core("Array.from(core.STYLE_TYPES).includes('outline')")
        self.assertTrue(result)

    def test_the_fill_cycle_returns_to_plain_text_after_the_last_treatment(self):
        result = self.run_core(
            "[null,'accent','highlight','outline'].map((type)=>core.nextFillType(type))"
        )
        self.assertEqual(["accent", "highlight", "outline", None], result)

    def test_a_fill_reports_itself_only_when_it_covers_the_whole_range(self):
        styles = "[{start:0,end:10,type:'accent'},{start:2,end:6,type:'bold'}]"
        self.assertEqual("accent", self.run_core(f"core.fillTypeAt({styles},2,6)"))
        self.assertIsNone(self.run_core(f"core.fillTypeAt({styles},2,20)"))

    def test_applying_a_fill_splits_the_one_underneath_instead_of_stacking(self):
        result = self.run_core(
            "core.clearFillRanges("
            "[{start:0,end:10,type:'accent'},{start:2,end:6,type:'bold'}],2,6,'outline')"
        )
        self.assertEqual(
            [
                {"start": 0, "end": 2, "type": "accent"},
                {"start": 2, "end": 6, "type": "bold"},
                {"start": 6, "end": 10, "type": "accent"},
            ],
            result,
        )

    def test_clearing_fills_leaves_the_treatment_being_applied_untouched(self):
        result = self.run_core(
            "core.clearFillRanges([{start:0,end:10,type:'accent'}],2,6,'accent')"
        )
        self.assertEqual([{"start": 0, "end": 10, "type": "accent"}], result)

    def test_a_weak_split_is_improved_at_the_same_row_count(self):
        """The editor's rebalance action feeds the canonical text back in
        with the current row count as a weak preference. A long opening row
        closed by a one-word orphan has to lose to an even split, without
        the count itself being treated as the thing to preserve."""
        result = self.run_core(
            "core.suggestBalancedLines("
            "'Un agente non si commuove per il tuo claim: confronta.', 2)"
        )
        self.assertEqual(
            ["Un agente non si commuove", "per il tuo claim: confronta."], result
        )
        self.assertNotEqual(
            ["Un agente non si commuove per il tuo claim:", "confronta."], result
        )

    def test_clamped_styles_cannot_block_preview_after_text_shortens(self):
        result = self.run_core(
            "core.clampStyleRanges([{start:0,end:99,type:'underline'},{start:8,end:9,type:'bold'}], 12)"
        )
        self.assertEqual(
            [{"start": 0, "end": 12, "type": "underline"}, {"start": 8, "end": 9, "type": "bold"}],
            result,
        )


if __name__ == "__main__":
    unittest.main()
