import importlib.util
import base64
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
BUILD_SPEC = importlib.util.spec_from_file_location(
    "build_plugin_package", SCRIPTS / "build_plugin_package.py"
)
BUILD_PLUGIN = importlib.util.module_from_spec(BUILD_SPEC)
assert BUILD_SPEC.loader is not None
BUILD_SPEC.loader.exec_module(BUILD_PLUGIN)
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import mcp_quote_card as ADAPTER


class McpAdapterTests(unittest.TestCase):
    def test_default_input_validates_and_renders_with_neutral_profile(self):
        result = ADAPTER.preview_quote_card({
            "text": "La tecnologia migliore ci aiuta a decidere meglio.",
            "attribution": "Input di prova",
        })
        self.assertTrue(result["valid"])
        self.assertTrue(result["rendered"])
        self.assertEqual("Neutral profile", result["profile"])
        self.assertEqual("4x5", result["format"])
        self.assertIn("<svg ", result["svg"][:160])
        self.assertTrue(result["svg_data_uri"].startswith("data:image/svg+xml;base64,"))
        self.assertEqual([], result["errors"])
        self.assertIn("Input di prova", result["alt_text"])

    def test_explicit_lines_and_direction_reuse_visual_contract(self):
        result = ADAPTER.preview_quote_card({
            "text": "Decidere meglio richiede tempo.",
            "lines": ["Decidere meglio", "richiede tempo."],
            "direction": "statement",
            "transformation": "EDITED",
            "evidence_status": "VERIFIED",
        })
        self.assertTrue(result["valid"])
        self.assertIn('fill="#072743"', result["svg"])
        self.assertEqual("statement", result["direction"])

    def test_square_format_uses_the_canonical_renderer(self):
        result = ADAPTER.preview_quote_card({
            "text": "Una quote quadrata per il feed.",
            "format": "1x1",
            "lines": ["Una quote quadrata", "per il feed."],
        })

        self.assertTrue(result["valid"])
        self.assertTrue(result["rendered"])
        self.assertEqual("1x1", result["format"])
        self.assertEqual((1440, 1440), (result["width"], result["height"]))
        self.assertIn("<svg ", result["svg"][:160])

    def test_new_graphics_reuse_the_canonical_renderer(self):
        cases = (
            ("editorial", "cover"),
            ("editorial", "cutouts"),
            ("editorial", "gradient"),
            ("contextual", "constellations"),
        )
        for direction, graphic_variant in cases:
            with self.subTest(graphic_variant=graphic_variant):
                result = ADAPTER.preview_quote_card({
                    "text": "Una composizione con motivo coerente.",
                    "direction": direction,
                    "graphic_variant": graphic_variant,
                    "graphic_seed": 42,
                })
                self.assertTrue(result["valid"])
                self.assertTrue(result["rendered"])
                self.assertEqual("4x5", result["format"])
                self.assertEqual((1440, 1800), (result["width"], result["height"]))
                self.assertIn(f"direction-graphic--{graphic_variant}", result["svg"])

    def test_more_than_six_authored_lines_are_rendered(self):
        lines = [f"Riga {index}" for index in range(1, 9)]
        result = ADAPTER.preview_quote_card({
            "text": " ".join(lines),
            "lines": lines,
            "direction": "editorial",
        })

        self.assertTrue(result["valid"])
        self.assertTrue(result["rendered"])
        for line in lines:
            self.assertIn(line, result["svg"])

    def test_statement_does_not_add_an_automatic_word_accent(self):
        result = ADAPTER.preview_quote_card({
            "text": "Nessun accento implicito su queste parole.",
            "direction": "statement",
        })

        self.assertTrue(result["valid"])
        root = ET.fromstring(result["svg"])
        quote = root.find(".//{http://www.w3.org/2000/svg}text[@class='quote']")
        self.assertIsNotNone(quote)
        accent = result["palette"]["accent"]
        self.assertFalse(any(node.attrib.get("fill") == accent for node in quote.iter()))

    def test_editor_controls_reach_renderer_and_output(self):
        result = ADAPTER.preview_quote_card({
            "text": "Scegliere bene richiede tempo.",
            "lines": ["Scegliere bene", "richiede tempo."],
            "direction": "editorial",
            "graphic_variant": "rhythm_lines",
            "text_scale": 0.8,
            "vertical_position": "lower",
            "styles": [{"start": 0, "end": 8, "type": "bold"}],
        })
        self.assertTrue(result["valid"])
        self.assertEqual("rhythm_lines", result["graphic_variant"])
        self.assertEqual(0.8, result["text_scale"])
        self.assertEqual("lower", result["vertical_position"])
        self.assertIn('font-weight="700"', result["svg"])

    def test_styles_after_blank_rows_are_mapped_to_canonical_text(self):
        text = "uno\n\ndue\n\ntre"
        manifest, errors = ADAPTER.build_manifest({
            "text": text,
            "lines": ["uno", "", "due", "", "tre"],
            "styles": [{"start": text.index("tre"), "end": len(text), "type": "bold"}],
        })

        self.assertEqual([], errors)
        self.assertIsNotNone(manifest)
        self.assertEqual("uno due tre", manifest["content"]["text"])
        self.assertEqual(
            [{"start": 8, "end": 11, "type": "bold"}],
            manifest["content"]["styles"],
        )

    def test_separately_formatted_words_keep_exact_offsets_across_authored_rows(self):
        text = "in\n\ngirum\n\nimus\n\nnocte\n\net\n\nconsumimur\n\nigni"
        words_and_types = [
            ("in", "bold"),
            ("girum", "italic"),
            ("imus", "underline"),
            ("nocte", "accent"),
            ("et", "outline"),
            ("consumimur", "highlight"),
            ("igni", "bold"),
        ]
        raw_styles = [
            {"start": text.index(word), "end": text.index(word) + len(word), "type": kind}
            for word, kind in words_and_types
        ]

        manifest, errors = ADAPTER.build_manifest({
            "text": text,
            "lines": text.split("\n"),
            "styles": raw_styles,
        })

        self.assertEqual([], errors)
        self.assertIsNotNone(manifest)
        canonical = "in girum imus nocte et consumimur igni"
        self.assertEqual(canonical, manifest["content"]["text"])
        self.assertEqual(
            [
                {
                    "start": canonical.index(word),
                    "end": canonical.index(word) + len(word),
                    "type": kind,
                }
                for word, kind in words_and_types
            ],
            manifest["content"]["styles"],
        )

    def test_word_per_row_formatting_does_not_duplicate_the_quote(self):
        text = "errare\numano\nest"
        words_and_types = [
            ("errare", "bold"),
            ("umano", "italic"),
            ("est", "highlight"),
        ]
        result = ADAPTER.preview_quote_card({
            "text": text,
            "lines": text.split("\n"),
            "styles": [
                {"start": text.index(word), "end": text.index(word) + len(word), "type": kind}
                for word, kind in words_and_types
            ],
        })

        self.assertTrue(result["valid"])
        self.assertTrue(result["rendered"])
        quote = ET.fromstring(result["svg"]).find(".//{http://www.w3.org/2000/svg}text[@class='quote']")
        self.assertIsNotNone(quote)
        rendered_text = "".join(quote.itertext())
        self.assertEqual("errareumanoest", rendered_text)
        for word, _ in words_and_types:
            self.assertEqual(1, rendered_text.count(word))

    def test_each_formatted_row_keeps_its_own_first_glyph(self):
        """Adjacent line ranges must not bleed into the next row's first glyph."""
        lines = ["test"] * 6
        text = "\n".join(lines)
        styles = [
            {"start": index * 5, "end": index * 5 + 4, "type": kind}
            for index, kind in enumerate(
                ["bold", "italic", "underline", "accent", "outline", "highlight"]
            )
        ]
        result = ADAPTER.preview_quote_card({"text": text, "lines": lines, "styles": styles})

        self.assertTrue(result["valid"])
        root = ET.fromstring(result["svg"])
        quote = root.find('.//{http://www.w3.org/2000/svg}text[@class="quote"]')
        self.assertIsNotNone(quote)
        rows = list(quote)
        self.assertEqual(6, len(rows))
        self.assertEqual(["test"] * 6, ["".join(row.itertext()) for row in rows])
        self.assertIn('font-weight="700"', ET.tostring(rows[0], encoding="unicode"))
        self.assertIn('font-style="italic"', ET.tostring(rows[1], encoding="unicode"))
        self.assertIn("text-decoration:underline", ET.tostring(rows[2], encoding="unicode"))
        self.assertIn('fill="#E3F4FF"', ET.tostring(rows[3], encoding="unicode"))
        self.assertIn('fill="none"', ET.tostring(rows[4], encoding="unicode"))
        self.assertEqual(1, len(root.findall('.//{http://www.w3.org/2000/svg}rect[@class="highlight-marker"]')))

    def test_style_selection_does_not_include_surrounding_line_breaks(self):
        manifest, errors = ADAPTER.build_manifest({
            "text": "uno\n\ndue",
            "lines": ["uno", "", "due"],
            "styles": [{"start": 0, "end": 5, "type": "highlight"}],
        })

        self.assertEqual([], errors)
        self.assertEqual(
            [{"start": 0, "end": 3, "type": "highlight"}],
            manifest["content"]["styles"],
        )

    def test_invalid_graphic_variant_is_readable(self):
        result = ADAPTER.preview_quote_card({
            "text": "Motivo non coerente.",
            "direction": "editorial",
            "graphic_variant": "modules",
        })
        self.assertFalse(result["valid"])
        self.assertEqual("enum", result["errors"][0]["code"])

    def test_explicit_palette_is_passed_to_the_canonical_renderer(self):
        result = ADAPTER.preview_quote_card({
            "text": "Una palette scelta dall'utente.",
            "direction": "contextual",
            "palette": {
                "name": "Blu personale",
                "colors": {
                    "primary": "#123456",
                    "accent": "#FFF4CC",
                    "background": "#FFFFFF",
                    "text": "#111111",
                },
            },
        })
        self.assertTrue(result["valid"])
        self.assertEqual("Blu personale", result["profile"])
        self.assertEqual("contextual", result["direction"])
        self.assertEqual("#123456", result["palette"]["primary"])
        self.assertIn('fill="#123456"', result["svg"])

    def test_custom_palette_is_applied_to_every_direction(self):
        palette = {
            "name": "Palette diagnostica",
            "colors": {
                "primary": "#000000",
                "accent": "#FF00FF",
                "background": "#00FFFF",
                "text": "#222222",
            },
        }
        expected_fills = {
            "editorial": {"#000000", "#00FFFF", "#222222"},
            "statement": {"#000000", "#00FFFF"},
            "contextual": {"#000000", "#FF00FF", "#00FFFF", "#222222"},
        }

        for direction, expected in expected_fills.items():
            with self.subTest(direction=direction):
                result = ADAPTER.preview_quote_card({
                    "text": "La stessa palette in ogni direzione.",
                    "direction": direction,
                    "palette": palette,
                })
                self.assertTrue(result["valid"])
                self.assertEqual(palette["colors"], result["palette"])
                root = ET.fromstring(result["svg"])
                fills = {
                    node.attrib["fill"]
                    for node in root.iter()
                    if node.attrib.get("fill", "").startswith("#")
                }
                self.assertTrue(expected.issubset(fills))

    def test_invalid_palette_has_readable_errors_and_no_render(self):
        result = ADAPTER.preview_quote_card({
            "text": "Palette non valida.",
            "palette": {
                "name": "Test",
                "colors": {
                    "primary": "navy",
                    "accent": "#FFF4CC",
                    "background": "#FFFFFF",
                    "text": "#111111",
                },
            },
        })
        self.assertFalse(result["valid"])
        self.assertFalse(result["rendered"])
        self.assertEqual("color", result["errors"][0]["code"])

    def test_invalid_input_has_readable_structured_errors_and_no_render(self):
        result = ADAPTER.preview_quote_card({
            "text": "",
            "lines": ["testo diverso"],
            "direction": "unknown",
        })
        self.assertFalse(result["valid"])
        self.assertFalse(result["rendered"])
        self.assertIsNone(result["svg"])
        codes = {error["code"] for error in result["errors"]}
        self.assertIn("required", codes)
        self.assertIn("enum", codes)

    def test_invalid_style_range_is_rejected_before_renderer(self):
        result = ADAPTER.preview_quote_card({
            "text": "Una frase breve.",
            "styles": [{"start": 0, "end": 999, "type": "bold"}],
        })
        self.assertFalse(result["valid"])
        self.assertEqual("range", result["errors"][0]["code"])

    def test_json_smoke_result_is_serializable(self):
        result = json.loads(ADAPTER.json_result({"text": "Prova JSON."}))
        self.assertTrue(result["valid"])
        self.assertEqual("4x5", result["format"])

    def test_editor_serializes_browser_line_breaks_and_prepares_png_download(self):
        import mcp_app

        html = mcp_app.quote_card_preview_html()
        self.assertIn('function serializeEditorNode(node, boundaryNode, boundaryOffset)', html)
        self.assertIn('const value = serializeEditorNode(text, null, 0).value', html)
        self.assertIn('.replace(/\\r\\n?/g, "\\n")', html)
        self.assertIn('lines:readLines()', html)
        self.assertIn("async function svgToPngFile", html)
        self.assertNotIn('canvas.toDataURL("image/png")', html)
        self.assertIn("canvas.toBlob", html)
        self.assertIn('type:"image/png"', html)
        self.assertIn('filename.replace(/\\.svg$/i, ".png")', html)
        self.assertNotIn("fetch(pngDataUrl)", html)
        self.assertIn('bridge.uploadFile(file, { library:false })', html)
        self.assertNotIn("download.click()", html)
        self.assertIn("openPreparedDownload", html)
        self.assertIn("getFileDownloadUrl", html)
        self.assertIn("openExternal", html)
        self.assertIn("uploadFile", html)
        self.assertIn('link.download = deliveryFilename || "quote-card.png"', html)
        self.assertNotIn('link.target = "_blank"', html)
        self.assertIn("PNG ready. Click Open PNG", html)
        self.assertIn('Open PNG', html)
        self.assertIn('function trimRangeWhitespace(range)', html)
        self.assertIn('function selectionRange()', html)
        self.assertIn('const caret = selectionRange()', html)
        self.assertIn('renderEditor(caret)', html)
        self.assertIn('function rangeCovered(kind, range)', html)
        self.assertIn('function subtractRange(item, range)', html)
        self.assertIn('alt="Vincos"', html)
        self.assertIn("data:image/svg+xml;base64,", html)
        self.assertIn('class="product-title" id="title"', html)
        self.assertNotIn("Quote card editor", html)
        self.assertIn("v1.36", html)
        self.assertNotIn("v1.36 TEST", html)
        self.assertNotIn('data-motif="default"', html)
        self.assertNotIn('data-motif="alternate"', html)
        self.assertIn("overflow:visible", html)
        self.assertNotIn(".editor { min-height:104px; outline:none; overflow:auto", html)
        self.assertNotIn("Optional emphasis", html)
        self.assertNotIn('id="emphasis"', html)
        self.assertNotIn("emphasis:emphasis.value", html)
        self.assertIn("function remapStylesAcrossWhitespace", html)
        self.assertIn("function remapStylesAfterEdit", html)
        self.assertIn("function insertAuthoredNewline", html)
        self.assertIn('text.addEventListener("beforeinput"', html)
        self.assertIn("event.preventDefault()", html)
        self.assertIn("formatting preserved", html)
        self.assertIn('className = "editor-line"', html)
        self.assertIn("newline is part of the text model", html)
        self.assertNotIn("styles = []; clearProduction()", html)
        self.assertIn("signature !== currentSignature()", html)
        self.assertIn("function schedulePreview(delay = 160)", html)
        self.assertIn("schedulePreview(0)", html)
        self.assertIn('["primary", "accent", "background", "textColor"]', html)

    def test_editor_remaps_style_ranges_instead_of_dropping_them_after_edits(self):
        if shutil.which("node") is None:
            self.skipTest("Node.js non disponibile: test helper UI saltato")
        import mcp_app

        html = mcp_app.quote_card_preview_html()
        script = html.split("function pointLength", 1)[1].split(
            "function trimRangeWhitespace", 1
        )[0]
        script = "function pointLength" + script
        assertions = r'''
const original = "in girum imus";
const styled = [
  {start:0,end:2,type:"bold"},
  {start:3,end:8,type:"italic"},
  {start:9,end:13,type:"underline"},
];
const withRows = remapStylesAfterEdit(original, "in\ngirum\nimus", styled);
if (JSON.stringify(withRows) !== JSON.stringify([
  {start:0,end:2,type:"bold"},
  {start:3,end:8,type:"italic"},
  {start:9,end:13,type:"underline"},
])) throw new Error(`whitespace remap failed: ${JSON.stringify(withRows)}`);
const afterInsertion = remapStylesAfterEdit(
  "uno due tre",
  "uno grande due tre",
  [{start:4,end:7,type:"accent"},{start:8,end:11,type:"highlight"}],
);
if (JSON.stringify(afterInsertion) !== JSON.stringify([
  {start:11,end:14,type:"accent"},
  {start:15,end:18,type:"highlight"},
])) throw new Error(`insertion remap failed: ${JSON.stringify(afterInsertion)}`);
const firstBreak = insertAuthoredNewline("test test test", {start:4,end:4});
if (firstBreak.value !== "test\ntest test") throw new Error(`first Enter kept a separator: ${JSON.stringify(firstBreak)}`);
if (JSON.stringify(firstBreak.range) !== JSON.stringify({start:5,end:5})) throw new Error(`first caret drifted: ${JSON.stringify(firstBreak)}`);
const secondBreak = insertAuthoredNewline(firstBreak.value, {start:9,end:9});
if (secondBreak.value !== "test\ntest\ntest") throw new Error(`second Enter kept a separator: ${JSON.stringify(secondBreak)}`);
const fourthRow = insertAuthoredNewline(secondBreak.value, {start:14,end:14});
if (fourthRow.value !== "test\ntest\ntest\n") throw new Error(`terminal Enter was lost: ${JSON.stringify(fourthRow)}`);
if (JSON.stringify(fourthRow.range) !== JSON.stringify({start:15,end:15})) throw new Error(`terminal caret drifted: ${JSON.stringify(fourthRow)}`);
const blankRow = insertAuthoredNewline("one\ntwo", {start:4,end:4});
if (blankRow.value !== "one\n\ntwo") throw new Error(`blank row was lost: ${JSON.stringify(blankRow)}`);
'''
        completed = subprocess.run(
            ["node", "-e", script + assertions],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)

    def test_png_delivery_uses_chatgpt_file_apis_when_available(self):
        if shutil.which("node") is None:
            self.skipTest("Node.js non disponibile: test download UI saltato")
        import mcp_app

        html = mcp_app.quote_card_preview_html()
        delivery_functions = "async function prepareDownload" + html.split(
            "async function prepareDownload", 1
        )[1].split("function syncFromOpenAiAliases", 1)[0]
        assertions = r'''
let deliveryUrl = "";
let deliveryFileId = "";
let deliveryFilename = "";
let blobCount = 0;
let uploadCount = 0;
let downloadUrlCount = 0;
let externalOpenCount = 0;
let downloadClickCount = 0;
const download = { disabled:true };
const deliveryName = { textContent:"" };
const delivery = { hidden:true };
const status = { textContent:"" };
const errors = { textContent:"", hidden:true };
const document = { body:{ append(){} }, createElement:() => ({ style:{}, click(){ downloadClickCount += 1; }, remove(){} }) };
const URL = { createObjectURL:(file) => { blobCount += 1; return `blob:local/${file.name}`; }, revokeObjectURL(){} };
const window = { openai:{
  uploadFile:async (file, options) => { uploadCount += 1; if (file.name !== "quote-card-test.png" || options.library !== false) throw new Error("unexpected upload"); return { fileId:"file_qcb" }; },
  getFileDownloadUrl:async ({fileId}) => { downloadUrlCount += 1; if (fileId !== "file_qcb") throw new Error("wrong file id"); return { downloadUrl:"https://files.openai.example/quote-card-test.png" }; },
  openExternal:async ({href, redirectUrl}) => { externalOpenCount += 1; if (href !== "https://files.openai.example/quote-card-test.png" || redirectUrl !== false) throw new Error("wrong external request"); }
} };
const scheduleResize = () => {};
const clearProduction = () => { deliveryUrl = ""; deliveryFileId = ""; deliveryFilename = ""; download.disabled = true; };
const svgToPngFile = async (_svg, filename) => ({ name:filename.replace(/\.svg$/i, ".png"), type:"image/png" });
await prepareDownload({ produced:true, svg:"<svg/>", filename:"quote-card-test.svg" });
if (deliveryUrl !== "") throw new Error("host delivery should not use a local URL");
if (deliveryFileId !== "file_qcb") throw new Error("host file was not prepared");
if (deliveryFilename !== "quote-card-test.png") throw new Error("filename missing");
if (download.disabled) throw new Error("download button remained disabled");
if (blobCount !== 0) throw new Error(`unexpected local Blob: ${blobCount}`);
if (uploadCount !== 1) throw new Error(`upload missing: ${uploadCount}`);
if (delivery.hidden) throw new Error("download action remained hidden");
await openPreparedDownload();
if (downloadUrlCount !== 1) throw new Error(`download URL missing: ${downloadUrlCount}`);
if (externalOpenCount !== 1) throw new Error(`host download did not start: ${externalOpenCount}`);
if (status.textContent !== "PNG opened in a new tab. Save it from your browser.") throw new Error(`unexpected status: ${status.textContent}`);
'''
        completed = subprocess.run(
            ["node", "--input-type=module", "-e", delivery_functions + assertions],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)

    def test_editor_selection_offsets_count_block_line_breaks_at_root_boundaries(self):
        if shutil.which("node") is None:
            self.skipTest("Node.js non disponibile: test serializer UI saltato")
        import mcp_app

        html = mcp_app.quote_card_preview_html()
        serializer = "function isPlaceholderBreak" + html.split(
            "function isPlaceholderBreak", 1
        )[1].split("function textValue", 1)[0]
        assertions = r'''
const Node = { TEXT_NODE:3, ELEMENT_NODE:1 };
const blockTags = new Set(["DIV", "P", "LI", "BLOCKQUOTE", "PRE"]);
const textNode = (data) => ({ nodeType:Node.TEXT_NODE, data, childNodes:[] });
const element = (tagName, children=[]) => ({ nodeType:Node.ELEMENT_NODE, tagName, childNodes:children });
const root = element("DIV", [
  textNode("in girum"),
  element("DIV", [element("BR")]),
  element("DIV", [textNode("imus nocte")]),
]);
const beforeThirdBlock = serializeEditorNode(root, root, 2).value;
if (beforeThirdBlock !== "in girum\n\n") throw new Error(`root boundary lost line breaks: ${JSON.stringify(beforeThirdBlock)}`);
const complete = serializeEditorNode(root, null, 0).value;
if (complete !== "in girum\n\nimus nocte") throw new Error(`full serialization drifted: ${JSON.stringify(complete)}`);
const authoredRows = element("DIV", [
  element("DIV", [textNode("test")]),
  element("DIV", [textNode("test")]),
  element("DIV", [textNode("test")]),
  element("DIV", [element("BR")]),
]);
const fourthLineReady = serializeEditorNode(authoredRows, null, 0).value;
if (fourthLineReady !== "test\ntest\ntest\n") throw new Error(`terminal authored row was lost: ${JSON.stringify(fourthLineReady)}`);
const fourthLineCaret = serializeEditorNode(authoredRows, authoredRows.childNodes[3], 0).value;
if (fourthLineCaret !== fourthLineReady) throw new Error(`terminal caret offset drifted: ${JSON.stringify(fourthLineCaret)}`);
'''
        completed = subprocess.run(
            ["node", "-e", serializer + assertions],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)


class McpProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if importlib.util.find_spec("mcp") is None:
            raise unittest.SkipTest("SDK MCP non installato: test protocollo saltato")

    def test_tool_exposes_explicit_input_and_output_schemas(self):
        import mcp_server

        tools = {item.name: item for item in mcp_server.mcp._tool_manager.list_tools()}
        self.assertEqual({"quote_card_builder_open_editor", "preview_quote_card", "produce_quote_card"}, set(tools))

        data_tool = tools["preview_quote_card"]
        self.assertIn("text", data_tool.parameters["properties"])
        self.assertIn("text", data_tool.parameters["required"])
        self.assertIn("valid", data_tool.output_schema["properties"])
        self.assertIn("svg", data_tool.output_schema["properties"])
        self.assertIn("palette", data_tool.parameters["properties"])
        self.assertIn("direction", data_tool.output_schema["properties"])
        self.assertIn("graphic_variant", data_tool.parameters["properties"])
        self.assertIn("text_scale", data_tool.parameters["properties"])
        self.assertIn("vertical_position", data_tool.parameters["properties"])
        self.assertNotIn("emphasis", data_tool.parameters["properties"])
        self.assertNotIn("maxItems", data_tool.parameters["properties"]["lines"])
        self.assertIn("graphic_mode", data_tool.output_schema["properties"])
        self.assertIn("editor_state", data_tool.output_schema["properties"])
        self.assertEqual(["app"], data_tool.meta["ui"]["visibility"])
        self.assertTrue(data_tool.meta["openai/widgetAccessible"])
        self.assertNotIn("resourceUri", data_tool.meta["ui"])
        self.assertNotIn("openai/outputTemplate", data_tool.meta)

        production_tool = tools["produce_quote_card"]
        self.assertNotIn("emphasis", production_tool.parameters["properties"])
        self.assertEqual(["app"], production_tool.meta["ui"]["visibility"])
        self.assertTrue(production_tool.meta["openai/widgetAccessible"])
        self.assertIn("produced", production_tool.output_schema["properties"])
        self.assertIn("filename", production_tool.output_schema["properties"])
        self.assertNotIn("resourceUri", production_tool.meta["ui"])

        ui_tool = tools["quote_card_builder_open_editor"]
        self.assertNotIn("emphasis", ui_tool.parameters["properties"])
        self.assertTrue({"text", "attribution", "profile_mode", "direction"}.issubset(ui_tool.parameters["required"]))
        self.assertEqual(
            {"text", "attribution", "profile_mode", "direction", "format", "palette"},
            set(ui_tool.parameters["properties"]),
        )
        self.assertEqual("Open Quote Card Builder", ui_tool.title)
        self.assertTrue(ui_tool.description.startswith("Use this when"))
        self.assertIn("only public tool", ui_tool.description)
        self.assertIn("call it once", ui_tool.description)
        self.assertIn("do not create SVG, PNG, HTML", ui_tool.description)
        self.assertIn("do not look for a local editor", ui_tool.description)
        self.assertIn("palette, never tone or mood", ui_tool.description.lower())
        self.assertEqual("1. Quote", ui_tool.parameters["properties"]["text"]["title"])
        self.assertEqual("2. Visible attribution", ui_tool.parameters["properties"]["attribution"]["title"])
        self.assertEqual("3. Palette", ui_tool.parameters["properties"]["profile_mode"]["title"])
        self.assertEqual("4. Direction", ui_tool.parameters["properties"]["direction"]["title"])
        self.assertIn(
            "does not represent tone, mood, or style",
            ui_tool.parameters["properties"]["profile_mode"]["description"],
        )
        self.assertIn(
            "Do not accept minimal",
            ui_tool.parameters["properties"]["direction"]["description"],
        )
        self.assertEqual(
            "ui://quote-card-builder/preview/v1.36.html",
            ui_tool.meta["ui"]["resourceUri"],
        )
        self.assertEqual(["model"], ui_tool.meta["ui"]["visibility"])
        self.assertEqual(
            "ui://quote-card-builder/preview/v1.36.html",
            ui_tool.meta["openai/outputTemplate"],
        )
        self.assertEqual("Opening Quote Card Builder…", ui_tool.meta["openai/toolInvocation/invoking"])

    def test_routing_metadata_covers_the_reported_chatgpt_failure(self):
        import mcp_server

        tools = {item.name: item for item in mcp_server.mcp._tool_manager.list_tools()}
        ui_tool = tools["quote_card_builder_open_editor"]
        routing_copy = f"{mcp_server.mcp.instructions} {ui_tool.description}".lower()

        direct_prompts = ("selects quote card builder", "open a quote card")
        indirect_prompts = ("create", "test")
        disallowed_fallbacks = (
            "image generation",
            "local filesystem",
            "do not look for a local editor",
            "do not say the plugin is unavailable",
        )
        for phrase in (*direct_prompts, *indirect_prompts, *disallowed_fallbacks):
            self.assertIn(phrase, routing_copy)

        result = mcp_server.quote_card_builder_open_editor(
            text="noli me tangere lauria uber alles",
            attribution="vincos",
            profile_mode="neutral",
            direction="editorial",
            format="4x5",
            palette=None,
        )
        self.assertTrue(result.structuredContent["rendered"])
        state = result.structuredContent["editor_state"]
        self.assertEqual("noli me tangere lauria uber alles", state["text"])
        self.assertEqual("vincos", state["attribution"])
        self.assertEqual("neutral", state["profile_mode"])
        self.assertEqual("editorial", state["direction"])
        self.assertFalse(any(item.type == "image" for item in result.content))

    def test_preview_ui_resource_is_a_portable_mcp_app(self):
        import asyncio
        import mcp_app
        import mcp_server

        resources = asyncio.run(mcp_server.mcp.list_resources())
        resource = next(
            item
            for item in resources
            if str(item.uri) == "ui://quote-card-builder/preview/v1.36.html"
        )
        self.assertEqual(
            resource.meta["ui"]["domain"],
            "https://quote-card-builder-mcp-960066178304.europe-west8.run.app",
        )
        self.assertEqual(resource.meta["ui"]["csp"]["connectDomains"], [])
        self.assertEqual(resource.meta["ui"]["csp"]["resourceDomains"], [])
        self.assertEqual(
            resource.meta["openai/widgetCSP"]["redirect_domains"],
            ["https://oaisdmntpritalynorth.blob.core.windows.net"],
        )
        self.assertEqual("text/html;profile=mcp-app", resource.mimeType)
        self.assertTrue(resource.meta["ui"]["prefersBorder"])

        contents = asyncio.run(
            mcp_server.mcp.read_resource("ui://quote-card-builder/preview/v1.36.html")
        )
        self.assertEqual(1, len(contents))
        html = contents[0].content
        self.assertIn("ui/initialize", html)
        self.assertIn("ui/notifications/tool-result", html)
        self.assertIn('request("tools/call"', html)
        self.assertIn('name:"preview_quote_card"', html)
        self.assertIn('name:"produce_quote_card"', html)
        self.assertIn("window.openai", html)
        self.assertIn("bridge.toolOutput", html)
        self.assertIn("safeInlineSvg", html)
        self.assertNotIn("image.src = result.svg_data_uri", html)
        self.assertIn("result.svg", html)
        self.assertIn("contenteditable=\"true\"", html)
        self.assertIn("renderEditor", html)
        self.assertIn("ui/notifications/size-changed", html)
        self.assertIn("Content &amp; formatting", html)
        self.assertIn('<html lang="en">', html)
        self.assertIn('@font-face{font-family:"QCB Barlow"', html)
        self.assertIn("data:font/woff2;base64,", html)
        self.assertNotIn("data:font/ttf;base64,", html)
        self.assertNotIn('font-family:"QCB Orbitron"', html)
        wordmark = (ROOT / "assets" / "card-editor" / "quote-card-builder-wordmark.svg").read_text(encoding="utf-8")
        wordmark_builder_spec = importlib.util.spec_from_file_location(
            "build_wordmark_svg", ROOT / "scripts" / "build_wordmark_svg.py"
        )
        wordmark_builder = importlib.util.module_from_spec(wordmark_builder_spec)
        assert wordmark_builder_spec.loader is not None
        wordmark_builder_spec.loader.exec_module(wordmark_builder)
        self.assertEqual(wordmark_builder.build_wordmark(), wordmark)
        self.assertIn("Orbitron-Variable-latin.woff2", (ROOT / "scripts" / "build_wordmark_svg.py").read_text(encoding="utf-8"))
        self.assertIn("font-family: 'QCB Orbitron'", wordmark)
        self.assertIn("data:font/woff2;base64,", wordmark)
        self.assertIn('fill="#B9D936"', wordmark)
        self.assertIn('fill="#9B86AD"', wordmark)
        self.assertIn('viewBox="0 0 660 64"', wordmark)
        self.assertIn('x="372" y="48"', wordmark)
        self.assertGreaterEqual(html.count("data:image/svg+xml;base64,"), 2)
        self.assertLess(len(html.encode("utf-8")), 200_000)
        self.assertIn("--chrome:#2b1830", html)
        self.assertIn("--signal:#b9d936", html)
        self.assertNotIn("font-family: Inter", html)

        self.assertIn("selected motif", html)
        self.assertIn('data-direction="editorial"', html)
        self.assertIn('id="paletteMode"', html)
        self.assertIn("palette:readPalette()", html)
        self.assertIn('id="produce"', html)
        self.assertIn("Update preview", html)
        self.assertIn("Check current changes", html)
        self.assertIn("Generate PNG", html)
        self.assertIn("Prepare image", html)
        self.assertNotIn(">Refresh preview<", html)
        self.assertNotIn(">Generate<", html)
        self.assertIn('id="download"', html)
        self.assertIn("appendRun(line.length, previous)", html)
        self.assertIn("result.editor_state", html)
        self.assertIn("bridge?.uploadFile", html)
        self.assertIn('data-style="bold"', html)
        self.assertIn('data-style="italic"', html)
        self.assertIn('id="rebalance"', html)
        self.assertIn('id="scale"', html)
        self.assertIn('id="position"', html)
        self.assertIn('graphic_variant', html)

    def test_cached_preview_resource_versions_serve_the_current_editor(self):
        import asyncio
        import mcp_server

        resources = asyncio.run(mcp_server.mcp.list_resources())
        uris = {str(item.uri) for item in resources}
        for version in (26, 27, 28, 29, 30, 31, 32, 33, 34, 35):
            uri = f"ui://quote-card-builder/preview/v1.{version}.html"
            self.assertIn(uri, uris)
            contents = asyncio.run(mcp_server.mcp.read_resource(uri))
            self.assertEqual(1, len(contents))
            self.assertIn("v1.36", contents[0].content)

        self.assertNotIn("ui://quote-card-builder/preview/v1.25.html", uris)

    def test_domain_challenge_is_exact_and_disabled_without_a_token(self):
        import asyncio
        import mcp_server

        previous = os.environ.get("OPENAI_APPS_CHALLENGE_TOKEN")
        try:
            os.environ.pop("OPENAI_APPS_CHALLENGE_TOKEN", None)
            unavailable = asyncio.run(mcp_server.openai_apps_challenge(None))
            self.assertEqual(404, unavailable.status_code)
            self.assertEqual(b"", unavailable.body)

            os.environ["OPENAI_APPS_CHALLENGE_TOKEN"] = "test-challenge-value"
            available = asyncio.run(mcp_server.openai_apps_challenge(None))
            self.assertEqual(200, available.status_code)
            self.assertEqual(b"test-challenge-value", available.body)
        finally:
            if previous is None:
                os.environ.pop("OPENAI_APPS_CHALLENGE_TOKEN", None)
            else:
                os.environ["OPENAI_APPS_CHALLENGE_TOKEN"] = previous

    def test_http_transport_reads_explicit_host_allowlist(self):
        import mcp_server

        previous = os.environ.get("MCP_ALLOWED_HOSTS")
        try:
            os.environ["MCP_ALLOWED_HOSTS"] = "quote-card-builder-mcp-960066178304.europe-west8.run.app"
            mcp_server.configure_http_transport_security()
            settings = mcp_server.mcp.settings.transport_security
            self.assertTrue(settings.enable_dns_rebinding_protection)
            self.assertEqual(
                ["quote-card-builder-mcp-960066178304.europe-west8.run.app"],
                settings.allowed_hosts,
            )
        finally:
            if previous is None:
                os.environ.pop("MCP_ALLOWED_HOSTS", None)
            else:
                os.environ["MCP_ALLOWED_HOSTS"] = previous

    def test_stdio_round_trip_calls_the_real_server(self):
        import asyncio
        import sys

        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        async def run_round_trip():
            params = StdioServerParameters(
                command=sys.executable,
                args=[str(SCRIPTS / "mcp_server.py")],
            )
            async with stdio_client(params) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    initialized = await session.initialize()
                    self.assertIn("Do not choose defaults", initialized.instructions)
                    self.assertIn("3. Palette", initialized.instructions)
                    self.assertIn("Do not ask for tone", initialized.instructions)
                    self.assertIn("Do not use image generation", initialized.instructions)
                    self.assertIn("do not look for a local editor", initialized.instructions)
                    tools = await session.list_tools()
                    self.assertEqual(
                        ["preview_quote_card", "produce_quote_card", "quote_card_builder_open_editor"],
                        sorted(tool.name for tool in tools.tools),
                    )
                    result = await session.call_tool("preview_quote_card", {"text": "Una preview reale."})
                    self.assertFalse(result.isError)
                    self.assertTrue(result.structuredContent["valid"])
                    self.assertTrue(result.structuredContent["rendered"])
                    self.assertEqual("4x5", result.structuredContent["format"])
                    images = [item for item in result.content if item.type == "image"]
                    self.assertEqual(1, len(images))
                    self.assertEqual("image/svg+xml", images[0].mimeType)
                    decoded = base64.b64decode(images[0].data).decode("utf-8")
                    self.assertIn("<svg ", decoded[:220])

                    ui_result = await session.call_tool(
                        "quote_card_builder_open_editor",
                        {
                            "text": "Una sola interfaccia.",
                            "attribution": "",
                            "profile_mode": "custom",
                            "direction": "contextual",
                            "palette": {
                                "name": "Palette test",
                                "colors": {
                                    "primary": "#123456",
                                    "accent": "#FFF4CC",
                                    "background": "#FFFFFF",
                                    "text": "#111111",
                                },
                            },
                        },
                    )
                    self.assertFalse(ui_result.isError)
                    self.assertTrue(ui_result.structuredContent["rendered"])
                    self.assertEqual("contextual", ui_result.structuredContent["direction"])
                    self.assertEqual("Palette test", ui_result.structuredContent["profile"])
                    self.assertEqual("Una sola interfaccia.", ui_result.structuredContent["editor_state"]["text"])
                    self.assertEqual("custom", ui_result.structuredContent["editor_state"]["profile_mode"])
                    self.assertFalse(any(item.type == "image" for item in ui_result.content))

                    produced = await session.call_tool(
                        "produce_quote_card",
                        {
                            "text": "Una produzione reale.",
                            "direction": "contextual",
                            "palette": {
                                "name": "Palette produzione",
                                "colors": {
                                    "primary": "#123456",
                                    "accent": "#FFF4CC",
                                    "background": "#FFFFFF",
                                    "text": "#111111",
                                },
                            },
                        },
                    )
                    self.assertFalse(produced.isError)
                    self.assertTrue(produced.structuredContent["produced"])
                    self.assertTrue(produced.structuredContent["filename"].endswith(".svg"))
                    self.assertEqual("custom", produced.structuredContent["editor_state"]["profile_mode"])
                    self.assertFalse(any(item.type == "image" for item in produced.content))

        asyncio.run(run_round_trip())

    def test_packaged_mcp_configuration_starts_the_packaged_server(self):
        """Exercise the command and path recorded in the distributed .mcp.json."""
        import asyncio
        import tempfile

        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        with tempfile.TemporaryDirectory() as temporary:
            plugin_root = BUILD_PLUGIN.build_directory(Path(temporary))
            mcp_config = json.loads((plugin_root / ".mcp.json").read_text(encoding="utf-8"))
            server = mcp_config["mcpServers"]["quote-card-builder"]

            async def run_round_trip():
                params = StdioServerParameters(
                    command=sys.executable,
                    args=server["args"],
                    cwd=str(plugin_root),
                )
                async with stdio_client(params) as (read_stream, write_stream):
                    async with ClientSession(read_stream, write_stream) as session:
                        await session.initialize()
                        result = await session.call_tool(
                            "quote_card_builder_open_editor",
                            {
                                "text": "Preview dal pacchetto distribuito.",
                                "attribution": "",
                                "profile_mode": "neutral",
                                "direction": "editorial",
                            },
                        )
                        self.assertFalse(result.isError)
                        self.assertTrue(result.structuredContent["rendered"])
                        self.assertEqual("Neutral profile", result.structuredContent["profile"])
                        self.assertFalse(any(item.type == "image" for item in result.content))

            asyncio.run(run_round_trip())

    def test_streamable_http_round_trip_calls_the_real_server(self):
        import asyncio

        from mcp import ClientSession
        from mcp.client.streamable_http import streamable_http_client

        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]

        process = subprocess.Popen(
            [
                sys.executable,
                str(SCRIPTS / "mcp_server.py"),
                "--transport",
                "streamable-http",
                "--host",
                "127.0.0.1",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env={**os.environ, "PORT": str(port)},
        )
        try:
            deadline = time.monotonic() + 5
            while True:
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                        break
                except OSError:
                    if process.poll() is not None:
                        self.fail("Il server Streamable HTTP è terminato prima di accettare connessioni.")
                    if time.monotonic() >= deadline:
                        self.fail("Il server Streamable HTTP non ha aperto la porta entro cinque secondi.")
                    time.sleep(0.05)

            with urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as response:
                self.assertEqual(200, response.status)
                self.assertEqual(
                    {"status": "ok", "service": "quote-card-builder", "mcp_path": "/mcp"},
                    json.loads(response.read()),
                )

            async def run_round_trip():
                url = f"http://127.0.0.1:{port}/mcp"
                async with streamable_http_client(url) as (read_stream, write_stream, _):
                    async with ClientSession(read_stream, write_stream) as session:
                        await session.initialize()
                        tools = await session.list_tools()
                        self.assertEqual(
                            ["preview_quote_card", "produce_quote_card", "quote_card_builder_open_editor"],
                            sorted(tool.name for tool in tools.tools),
                        )
                        result = await session.call_tool(
                            "quote_card_builder_open_editor",
                            {
                                "text": "Preview HTTP reale.",
                                "attribution": "",
                                "profile_mode": "neutral",
                                "direction": "editorial",
                            },
                        )
                        self.assertFalse(result.isError)
                        self.assertTrue(result.structuredContent["rendered"])

            asyncio.run(run_round_trip())
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
