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
