"""Cross-tool behavior for the second grammar and editor-owned brand assets."""
import base64
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import mcp_quote_card as adapter
import mcp_server as server
import portable_brand
from visual_grammars import demo_compositions


def kit():
    return portable_brand.kit_from_brand({
        "name": "Explicit test brand", "colors": adapter.NEUTRAL_PROFILE["colors"],
        "font": {"family": "Barlow", "regular_path": str(ROOT / "assets/card-editor/fonts/Barlow-Regular.ttf"),
                 "bold_path": str(ROOT / "assets/card-editor/fonts/Barlow-Bold.ttf")},
        "logo": {"dark_path": str(ROOT / "assets/card-editor/vincos-lockup-white.svg")},
    }, ROOT)


class UrbanAndBrandTests(unittest.TestCase):
    def test_urban_authored_candidates_and_selected_scene_survive_preview_and_production(self):
        scenes = demo_compositions("Le idee diventano possibilità.", grammar="urban")
        for fmt in ("4x5", "1x1", "9x16"):
            with self.subTest(fmt=fmt):
                kwargs = {"text": "Le idee diventano possibilità.", "visual_grammar": "urban",
                          "format": fmt, "composition": scenes[1], "composition_candidates": scenes,
                          "proposal_source": "model", "compact_output": True}
                preview = server.preview_quote_card(**kwargs)
                produced = server.produce_quote_card(**kwargs)
                self.assertTrue(preview.structured_content["rendered"])
                self.assertTrue(produced.structured_content["produced"])
                self.assertEqual(scenes[1], produced.structured_content["editor_state"]["composition"])
                self.assertEqual(preview.meta["quoteCard"]["svg"], produced.meta["quoteCard"]["svg"])
                self.assertIn('data-visual-grammar="urban"', produced.meta["quoteCard"]["svg"])
                selected = next(p for p in preview.meta["quoteCard"]["composition_previews"] if p["id"] == scenes[1]["id"])
                self.assertEqual(selected["svg"], preview.meta["quoteCard"]["svg"])

    def test_mixed_grammar_candidates_are_rejected(self):
        scenes = demo_compositions("Una frase.", grammar="urban")
        scenes[1] = demo_compositions()[0]
        result = adapter.preview_quote_card({"text": "Una frase.", "visual_grammar": "urban", "composition_candidates": scenes})
        self.assertFalse(result["rendered"])
        self.assertTrue(result["errors"])

    def test_uploaded_font_and_logo_embed_and_preview_assets_are_request_scoped(self):
        brand = kit()
        payload = {"text": "Le idee restano leggibili.", "visual_grammar": "urban", "brand_kit": brand}
        before = copy.deepcopy(payload)
        with mock.patch.object(adapter, "brand_from_kit", wraps=adapter.brand_from_kit) as materialize:
            result = adapter.preview_quote_card(payload)
        self.assertTrue(result["rendered"], result["errors"])
        self.assertIn("data:font/ttf;base64,", result["svg"])
        self.assertIn("data:image/svg+xml;base64,", result["svg"])
        self.assertEqual(before, payload)
        self.assertFalse(Path(materialize.call_args.args[1]).exists(), "Uploaded server assets must be removed after rendering")
        hidden = adapter.preview_quote_card({**payload, "logo_mode": "hidden"})
        self.assertNotIn("data:image/svg+xml;base64,", hidden["svg"])

    def test_brand_binary_is_ui_only_and_chat_update_defers_to_live_assets(self):
        opened = server.quote_card_builder_open_editor(
            text="La citazione mantiene il proprio brand.", style="urban", brand_kit=kit(),
            attribution="", profile_mode="neutral", transformation="VERBATIM", evidence_status="USER_SUPPLIED")
        output = opened.structured_content
        self.assertTrue(output["rendered"])
        self.assertNotIn("data_base64", json.dumps(output))
        self.assertEqual("custom", output["editor_state"]["profile_mode"])
        self.assertTrue(output["editor_state"]["brand_kit_attached"])
        self.assertEqual(kit(), opened.meta["quoteCard"]["brand_kit"])
        state = server.EditorState.model_validate(output["editor_state"])
        with mock.patch.object(server, "_render_request", side_effect=AssertionError("Do not substitute a font for private assets")):
            update = server.quote_card_builder_update_editor(
                base_revision=7, base_snapshot=state,
                patch=server.EditorPatch(attribution="Autore fornito"))
        changed = update.structured_content
        self.assertTrue(changed["valid"])
        self.assertFalse(changed["rendered"])
        self.assertTrue(changed["deferred_render"])
        self.assertEqual(8, changed["editor_revision"])
        self.assertEqual("Autore fornito", changed["editor_state"]["attribution"])
        self.assertEqual(state.composition, changed["editor_state"]["composition"])
        self.assertNotIn("data_base64", json.dumps(changed))

    def test_invalid_brand_asset_is_a_technical_error(self):
        brand = kit()
        brand["font"]["regular"]["data_base64"] = base64.b64encode(b"not a font").decode()
        result = adapter.preview_quote_card({"text": "Una frase.", "visual_grammar": "urban", "brand_kit": brand})
        self.assertFalse(result["rendered"])
        self.assertEqual("brand_kit", result["errors"][0]["path"])


if __name__ == "__main__":
    unittest.main()
