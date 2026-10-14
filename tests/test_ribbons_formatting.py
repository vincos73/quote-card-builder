"""Local size ranges must survive editing and remain independent of fills."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
CORE = ROOT / "assets" / "card-editor" / "formatting-core.js"


@unittest.skipUnless(shutil.which("node"), "Node.js non disponibile")
class RibbonFormattingTests(unittest.TestCase):
    def evaluate(self, expression):
        script = f"const core=require({json.dumps(str(CORE))});process.stdout.write(JSON.stringify({expression}));"
        result = subprocess.run([shutil.which("node"), "-e", script], check=True, capture_output=True, text=True)
        return json.loads(result.stdout)

    def test_only_adjacent_ranges_of_the_same_size_merge(self):
        result = self.evaluate("core.normalizeStyleRanges(["
                               "{start:0,end:3,type:'size',scale:1.25},"
                               "{start:3,end:7,type:'size',scale:1.25},"
                               "{start:7,end:10,type:'size',scale:1.5}])")
        self.assertEqual([{"start": 0, "end": 7, "type": "size", "scale": 1.25},
                          {"start": 7, "end": 10, "type": "size", "scale": 1.5}], result)

    def test_new_size_replaces_selected_characters_without_losing_side_sizes_or_highlight(self):
        result = self.evaluate("core.setSizeRange(["
                               "{start:0,end:12,type:'size',scale:1.5},"
                               "{start:4,end:8,type:'highlight'}],4,8,1.25)")
        self.assertEqual([{"start": 0, "end": 4, "type": "size", "scale": 1.5},
                          {"start": 4, "end": 8, "type": "highlight"},
                          {"start": 4, "end": 8, "type": "size", "scale": 1.25},
                          {"start": 8, "end": 12, "type": "size", "scale": 1.5}], result)

    def test_hundred_percent_removes_only_local_size(self):
        result = self.evaluate("core.setSizeRange(["
                               "{start:0,end:12,type:'size',scale:1.5},"
                               "{start:4,end:8,type:'bold'}],4,8,1)")
        self.assertEqual([{"start": 0, "end": 4, "type": "size", "scale": 1.5},
                          {"start": 4, "end": 8, "type": "bold"},
                          {"start": 8, "end": 12, "type": "size", "scale": 1.5}], result)

    def test_unicode_edit_keeps_scale_and_code_point_offsets(self):
        result = self.evaluate("core.remapStyleRanges([{start:4,end:8,type:'size',scale:1.4}],"
                               "'L’🧠 idea','L’🧠 nuova idea')")
        self.assertEqual([{"start": 10, "end": 14, "type": "size", "scale": 1.4}], result)

    def test_mixed_or_partial_sizes_do_not_report_a_uniform_value(self):
        result = self.evaluate("["
                               "core.sizeScaleAt([{start:0,end:4,type:'size',scale:1.5}],0,4),"
                               "core.sizeScaleAt([{start:0,end:4,type:'size',scale:1.5}],0,8),"
                               "core.sizeScaleAt([],0,8)]")
        self.assertEqual([1.5, None, 1], result)

    def test_invalid_scales_cannot_enter_rendering(self):
        result = self.evaluate("core.normalizeStyleRanges(["
                               "{start:0,end:4,type:'size',scale:'1.5'},"
                               "{start:0,end:4,type:'size',scale:0.4},"
                               "{start:0,end:4,type:'size',scale:3},"
                               "{start:0,end:4,type:'size',scale:NaN}])")
        self.assertEqual([], result)

    def test_all_outputs_are_added_without_mutating_existing_geometry_or_hard_breaks(self):
        result = self.evaluate("(() => {const original=[{id:'4x5',width:1440,height:1800,"
                               "lines:['Una frase','con enfasi.'],text_scale:.9,vertical_position:'upper'}];"
                               "const completed=core.completeRibbonFormats(original,'Una frase con enfasi.');"
                               "completed[0].lines.push('prova');return {original,completed};})()")
        self.assertEqual(["Una frase", "con enfasi."], result["original"][0]["lines"])
        self.assertEqual(.9, result["completed"][0]["text_scale"])
        self.assertEqual("upper", result["completed"][0]["vertical_position"])
        self.assertEqual([("4x5", 1440, 1800), ("1x1", 1440, 1440), ("9x16", 1440, 2560)],
                         [(item["id"], item["width"], item["height"]) for item in result["completed"]])
        self.assertEqual(["Una frase con enfasi."], result["completed"][1]["lines"])

    def test_completing_outputs_preserves_an_existing_square_and_adds_no_duplicate(self):
        result = self.evaluate("core.completeRibbonFormats([{id:'4x5',width:1440,height:1800,lines:['Testo']},"
                               "{id:'1x1',width:1080,height:1080,lines:['Testo'],text_scale:.85}], 'Testo')")
        self.assertEqual(3, len(result))
        self.assertEqual((1080, .85), (result[1]["width"], result[1]["text_scale"]))


if __name__ == "__main__":
    unittest.main()
