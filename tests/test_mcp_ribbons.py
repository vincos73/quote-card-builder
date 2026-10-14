"""Native ribbon scenes survive MCP snapshots, edits and exact production."""

import base64
import asyncio
import copy
import hashlib
import struct
import sys
import unittest
import xml.etree.ElementTree as ET
import zlib
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import mcp_quote_card as adapter
import mcp_server as server
from visual_grammars import demo_compositions


def authored_payload():
    scenes = demo_compositions("Le idee incontrano prospettive diverse.")
    for index, scene in enumerate(scenes):
        scene["id"] = f"authored-scene-{index}"
    scenes[0]["ribbons"][0]["points"][1] = [.42, .12]
    return {"text": "Le idee incontrano prospettive diverse.", "visual_grammar": "ribbons",
            "composition": scenes[0], "composition_candidates": scenes, "proposal_source": "model"}


class McpRibbonAdapterTests(unittest.TestCase):
    def test_authored_curves_and_candidates_are_detached_and_never_replaced(self):
        payload = authored_payload()
        before = copy.deepcopy(payload)
        manifest, errors = adapter.build_manifest(payload)
        self.assertEqual([], errors)
        self.assertEqual(payload["composition"], manifest["presentation"]["composition"])
        result = adapter.preview_quote_card(payload)
        self.assertTrue(result["valid"], result["errors"])
        self.assertEqual("model", result["proposal_source"])
        self.assertEqual(payload["composition_candidates"], result["composition_candidates"])
        self.assertIn("C 604.80 216.00", result["svg"])
        self.assertEqual(before, payload)
        result["composition"]["ribbons"][0]["points"][1][0] = 1
        self.assertEqual(before, payload)

    def test_missing_scene_returns_three_labelled_demo_proposals_in_every_format(self):
        for format_id, height in (("4x5", 1800), ("1x1", 1440), ("9x16", 2560)):
            with self.subTest(format=format_id):
                result = adapter.preview_quote_card({"text": "Le idee crescono insieme.", "visual_grammar": "ribbons", "format": format_id})
                self.assertTrue(result["rendered"], result["errors"])
                self.assertEqual("demo", result["proposal_source"])
                self.assertEqual((1440, height), (result["width"], result["height"]))
                self.assertEqual(3, len(result["composition_candidates"]))
                self.assertEqual(3, len(result["composition_previews"]))
                self.assertEqual(result["composition_candidates"][0], result["composition"])
                for preview in result["composition_previews"]:
                    self.assertEqual(preview["svg_sha256"], hashlib.sha256(preview["svg"].encode()).hexdigest())

    def test_presentation_mapping_resolves_to_canonical_flat_scene_fields(self):
        scene = authored_payload()["composition"]
        result = adapter.preview_quote_card({"text": "Una frase.", "presentation": {
            "visual_grammar": "ribbons", "composition": scene, "quote_font_size": 83, "author_font_size": 31}})
        self.assertTrue(result["valid"], result["errors"])
        self.assertEqual(scene, result["composition"])
        self.assertEqual((83, 31), (result["ribbon_layout"]["font_size"], result["ribbon_layout"]["author_font_size"]))

    def test_size_metadata_survives_blank_rows_and_canonical_unicode_offsets(self):
        text = "  Uno 😊\n\n  prospettive diverse.  "
        start = text.index("prospettive")
        payload = {"text": text, "lines": text.split("\n"), "visual_grammar": "ribbons", "quote_font_size": 50,
                   "styles": [{"start": start, "end": start + 11, "type": "size", "scale": 1.6},
                              {"start": start, "end": start + 11, "type": "highlight"}]}
        manifest, errors = adapter.build_manifest(payload)
        self.assertEqual([], errors)
        mapped = manifest["content"]["styles"][0]
        self.assertEqual("prospettive", manifest["content"]["text"][mapped["start"]:mapped["end"]])
        self.assertEqual(1.6, mapped["scale"])
        result = adapter.preview_quote_card(payload)
        selected = [fragment for row in result["ribbon_layout"]["rows"] for fragment in row["fragments"] if "size" in fragment["types"]]
        self.assertEqual("prospettive", "".join(fragment["text"] for fragment in selected))
        self.assertTrue(all(fragment["font_size"] == 80 for fragment in selected))

    def test_newlines_without_lines_are_hard_paragraphs_with_automatic_wrap(self):
        text = "La tecnologia apre nuove possibilità.\nIl valore nasce dalle persone che sanno come trasformarle."
        result = adapter.preview_quote_card({"text": text, "visual_grammar": "ribbons", "quote_font_size": 100})
        self.assertTrue(result["rendered"], result["errors"])
        canonical_boundary = len(text.split("\n")[0])
        rows = result["ribbon_layout"]["rows"]
        self.assertTrue(all(row["end"] <= canonical_boundary or row["start"] > canonical_boundary for row in rows))
        self.assertEqual(" ".join(text.split()), " ".join(result["ribbon_layout"]["lines"]))

    def test_style_reuse_inherits_palette_roles_and_ribbon_widths(self):
        base = authored_payload()["composition"]
        base.update(background_role="primary", text_role="background", highlight_role="text")
        base["ribbons"][0].update(width_ratio=.19, color_role="text")
        before = copy.deepcopy(base)
        result = adapter.preview_quote_card({"text": "Una nuova frase per la stessa identità.", "visual_grammar": "ribbons",
                                             "composition": None, "composition_candidates": [], "reuse_composition": base})
        self.assertEqual("demo", result["proposal_source"])
        for scene in result["composition_candidates"]:
            for key in ("background_role", "text_role", "highlight_role"):
                self.assertEqual(base[key], scene[key])
            self.assertEqual([(item["color_role"], item["width_ratio"]) for item in base["ribbons"]],
                             [(item["color_role"], item["width_ratio"]) for item in scene["ribbons"]])
        self.assertEqual(before, base)

    def test_invalid_curve_duplicate_candidates_and_legacy_size_are_technical_errors(self):
        for mutation in (
            lambda payload: payload["composition"]["ribbons"][0].update(points="<script/>"),
            lambda payload: payload.update(composition_candidates=[payload["composition"]] * 2),
            lambda payload: payload.update(visual_grammar=None),
        ):
            payload = authored_payload()
            mutation(payload)
            result = adapter.preview_quote_card(payload)
            self.assertFalse(result["valid"])
            self.assertFalse(result["rendered"])
            self.assertIsNone(result["svg"])
            self.assertTrue(result["errors"])
        invalid = adapter.preview_quote_card({"text": "Parola.", "styles": [{"start": 0, "end": 6, "type": "size", "scale": 2}]})
        self.assertFalse(invalid["rendered"])
        for scale in (True, .49, 2.51, float("nan")):
            result = adapter.preview_quote_card({"text": "Parola.", "visual_grammar": "ribbons",
                "styles": [{"start": 0, "end": 6, "type": "size", "scale": scale}]})
            self.assertFalse(result["rendered"])

    def test_all_visual_warnings_are_advisory_and_preserve_user_palette_and_sizes(self):
        payload = authored_payload()
        payload.update(attribution="Un autore", quote_font_size=500, author_font_size=500,
                       palette={"name": "Scelta utente", "colors": {role: "#DFFF00" for role in adapter.PALETTE_COLOR_KEYS}})
        scene = payload["composition"]
        scene["author_box"] = copy.deepcopy(scene["quote_box"])
        before = copy.deepcopy(payload)
        result = adapter.preview_quote_card(payload)
        self.assertTrue(result["valid"], result["errors"])
        self.assertTrue(result["rendered"])
        codes = {item["code"] for item in result["warnings"]}
        self.assertTrue({"contrast", "text_contrast", "quote_overflow", "author_overlaps_quote"}.issubset(codes))
        self.assertTrue(all(item["severity"] == "advisory" for item in result["warnings"]))
        self.assertEqual(payload["palette"]["colors"], result["palette"])
        self.assertEqual(500, result["ribbon_layout"]["font_size"])
        self.assertEqual(before, payload)

    def test_legacy_low_contrast_is_also_advisory_without_selecting_ribbons(self):
        result = adapter.preview_quote_card({"text": "Una frase.", "palette": {
            "name": "Scelta", "colors": {role: "#FFFFFF" for role in adapter.PALETTE_COLOR_KEYS}}})
        self.assertTrue(result["valid"], result["errors"])
        self.assertTrue(result["rendered"])
        self.assertIsNone(result["visual_grammar"])
        self.assertNotIn('data-visual-grammar="ribbons"', result["svg"])
        self.assertTrue(any(item["code"] == "contrast" for item in result["warnings"]))

    def test_only_native_ribbons_embed_the_portable_font_used_for_measurement(self):
        legacy, errors = adapter.build_manifest({"text": "Una frase."})
        self.assertEqual([], errors)
        self.assertEqual({"family": "Arial"}, legacy["brand"]["font"])
        result = adapter.preview_quote_card({"text": "Una frase.", "visual_grammar": "ribbons"})
        self.assertEqual("font_metrics_ttf", result["ribbon_layout"]["metric"])
        self.assertIn("data:font/ttf;base64,", result["svg"])
        self.assertIn("Barlow", result["svg"])


class McpRibbonServerTests(unittest.TestCase):
    def test_stdio_protocol_roundtrip_transports_native_scenes_sizes_gallery_and_exact_svg(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        async def exercise():
            payload = authored_payload()
            payload.update(format="9x16", quote_font_size=80,
                           styles=[{"start": 3, "end": 7, "type": "size", "scale": 1.4}])
            params = StdioServerParameters(command=sys.executable, args=[str(ROOT / "scripts/mcp_server.py")])
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write, extensions={"io.modelcontextprotocol/ui": {
                    "mimeTypes": ["text/html;profile=mcp-app"]}}) as session:
                    initialized = await session.initialize()
                    self.assertEqual(server.MCP_SERVER_VERSION, initialized.server_info.version)
                    opened = await session.call_tool("quote_card_builder_open_editor", {**payload, "style": "ribbons"})
                    self.assertFalse(opened.is_error)
                    self.assertTrue(opened.structured_content["rendered"])
                    self.assertNotIn("svg", opened.structured_content)
                    self.assertEqual(3, len(opened.meta["quoteCard"]["composition_previews"]))
                    self.assertEqual(payload["composition"], opened.structured_content["editor_state"]["composition"])
                    self.assertEqual(payload["styles"], opened.structured_content["editor_state"]["styles"])
                    preview = await session.call_tool("preview_quote_card", {**payload, "compact_output": True})
                    produced = await session.call_tool("produce_quote_card", {**payload, "compact_output": True})
                    self.assertTrue(produced.structured_content["produced"])
                    self.assertEqual(opened.meta["quoteCard"]["svg"], preview.meta["quoteCard"]["svg"])
                    self.assertEqual(preview.meta["quoteCard"]["svg"], produced.meta["quoteCard"]["svg"])
                    changed = await session.call_tool("quote_card_builder_update_editor", {
                        "base_revision": 0, "base_snapshot": opened.structured_content["editor_state"],
                        "patch": {"attribution": "Un autore"}})
                    self.assertFalse(changed.is_error)
                    self.assertEqual(payload["composition"], changed.structured_content["editor_state"]["composition"])
                    self.assertEqual(payload["styles"], changed.structured_content["editor_state"]["styles"])
        asyncio.run(exercise())

    def test_initial_open_keeps_embedded_fonts_and_gallery_svg_out_of_model_context(self):
        payload = authored_payload()
        result = server.quote_card_builder_open_editor(**payload, style="ribbons", profile_mode="neutral", attribution="",
                                                       transformation="VERBATIM", evidence_status="USER_SUPPLIED")
        structured = result.structured_content
        self.assertTrue(structured["rendered"])
        self.assertNotIn("svg", structured)
        self.assertNotIn("svg_data_uri", structured)
        self.assertTrue(all("svg" not in item for item in structured["composition_previews"]))
        self.assertEqual(payload["composition"], structured["editor_state"]["composition"])
        self.assertEqual(payload["composition_candidates"], structured["editor_state"]["composition_candidates"])
        self.assertIn("data:font/ttf;base64,", result.meta["quoteCard"]["svg"])

    def test_compact_gallery_svg_is_ui_only_and_snapshot_keeps_native_scene(self):
        payload = authored_payload()
        result = server.preview_quote_card(**payload, compact_output=True)
        state = result.structured_content["editor_state"]
        self.assertEqual(payload["composition"], state["composition"])
        self.assertEqual(payload["composition_candidates"], state["composition_candidates"])
        self.assertTrue(all("svg" not in item for item in result.structured_content["composition_previews"]))
        self.assertEqual(3, len(result.meta["quoteCard"]["composition_previews"]))
        self.assertTrue(all(ET.fromstring(item["svg"]).tag == "{http://www.w3.org/2000/svg}svg"
                            for item in result.meta["quoteCard"]["composition_previews"]))

    def test_followup_preserves_scene_and_remapped_size_scale(self):
        payload = authored_payload()
        start = payload["text"].index("prospettive")
        payload.update(quote_font_size=66, author_font_size=31,
                       styles=[{"start": start, "end": start + 11, "type": "size", "scale": 1.4}])
        initial = server.preview_quote_card(**payload, compact_output=True).structured_content
        changed_text = "Domani " + payload["text"]
        result = server.quote_card_builder_update_editor(base_revision=3,
            base_snapshot=server.EditorState.model_validate(initial["editor_state"]),
            patch=server.EditorPatch.model_validate({"text": changed_text, "format": "9x16"}))
        state = result.structured_content["editor_state"]
        self.assertFalse(result.is_error)
        self.assertEqual(payload["composition"], state["composition"])
        self.assertEqual(payload["composition_candidates"], state["composition_candidates"])
        self.assertEqual((66, 31), (state["quote_font_size"], state["author_font_size"]))
        self.assertEqual(1.4, state["styles"][0]["scale"])
        self.assertEqual("prospettive", state["text"][state["styles"][0]["start"]:state["styles"][0]["end"]])

    def test_patch_explicit_auto_and_fresh_demo_gallery_resolve_into_snapshot(self):
        initial = server.preview_quote_card(text="Una frase.", visual_grammar="ribbons", quote_font_size=66).structured_content
        base = initial["editor_state"]["composition"]
        result = server.quote_card_builder_update_editor(base_revision=2,
            base_snapshot=server.EditorState.model_validate(initial["editor_state"]),
            patch=server.EditorPatch.model_validate({"quote_font_size": None, "composition": None,
                "composition_candidates": [], "reuse_composition": base}))
        state = result.structured_content["editor_state"]
        self.assertIsNone(state["quote_font_size"])
        self.assertEqual("demo", state["proposal_source"])
        self.assertEqual(3, len(state["composition_candidates"]))
        self.assertNotIn("reuse_composition", state)

    def test_production_uses_identical_preview_bytes_even_with_visual_warnings(self):
        payload = authored_payload()
        payload["quote_font_size"] = 600
        preview = server.preview_quote_card(**payload, compact_output=True)
        produced = server.produce_quote_card(**payload, compact_output=True)
        self.assertTrue(preview.structured_content["warnings"])
        self.assertTrue(produced.structured_content["produced"])
        self.assertEqual(preview.meta["quoteCard"]["svg"], produced.meta["quoteCard"]["svg"])
        self.assertEqual(preview.structured_content["svg_sha256"], produced.structured_content["svg_sha256"])
        request = server.PreviewQuoteCardInput.model_validate(payload)
        accepted = server.quote_card_builder_headless(action="produce", input=request, ui_unavailable=True,
            approve_production=True, approved_preview_sha256=preview.structured_content["svg_sha256"])
        self.assertTrue(accepted.structured_content["produced"])
        rejected = server.quote_card_builder_headless(action="produce", input=request, ui_unavailable=True,
            approve_production=True, approved_preview_sha256="0" * 64)
        self.assertFalse(rejected.structured_content["produced"])

    def test_size_shape_is_exposed_and_legacy_ranges_keep_original_shape(self):
        self.assertEqual({"start": 0, "end": 2, "type": "bold"}, server.StyleRange(start=0, end=2, type="bold").model_dump())
        self.assertEqual(1.4, server.StyleRange(start=0, end=2, type="size", scale=1.4).model_dump()["scale"])
        for payload in ({"start": 0, "end": 2, "type": "size"},
                        {"start": 0, "end": 2, "type": "bold", "scale": 1.4}):
            with self.assertRaises(ValueError):
                server.StyleRange.model_validate(payload)
        for cls in (server.PreviewQuoteCardInput, server.EditorState, server.EditorPatch):
            self.assertIn("9x16", str(cls.model_json_schema()["properties"]["format"]))
            self.assertIn("composition", cls.model_json_schema()["properties"])

    def test_story_png_validation_accepts_complete_canvas_without_changing_bytes(self):
        def chunk(kind, value):
            return struct.pack(">I", len(value)) + kind + value + struct.pack(">I", zlib.crc32(kind + value) & 0xffffffff)
        width, height = 1440, 2560
        data = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress((b"\0" + b"\0" * (width * 3)) * height)) + chunk(b"IEND", b""))
        self.assertEqual(data, server._validated_png(base64.b64encode(data).decode()))


if __name__ == "__main__":
    unittest.main()
