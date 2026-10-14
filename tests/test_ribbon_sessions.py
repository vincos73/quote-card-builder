"""Nastri persists a selected card while safely reusing its visual grammar."""

import copy
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from test_card_review_server import SERVER, manifest as legacy_manifest
import saved_styles
import prepare_ribbon_review
from visual_grammars import demo_compositions, normalize_composition


ROOT = Path(__file__).parents[1]


def ribbon_manifest():
    candidate = legacy_manifest()
    candidate["state"] = "candidato_selezionato"
    candidate["direction"] = "editorial"
    candidate["content"].update(
        emphasis="", styles_customized=True, alt_text="Una citazione della fonte verificata.",
        attribution={"label": "Ada\nRicercatrice", "role": "author"},
        styles=[{"start": 4, "end": 9, "type": "bold"},
                {"start": 10, "end": 20, "type": "highlight"},
                {"start": 4, "end": 9, "type": "size", "scale": 1.25}],
    )
    candidate["brand"]["font"] = {
        "family": "Barlow",
        "regular_path": str(ROOT / "assets/card-editor/fonts/Barlow-Regular.ttf"),
        "bold_path": str(ROOT / "assets/card-editor/fonts/Barlow-Bold.ttf"),
    }
    candidate["brand"]["colors"] = {
        "primary": "#3524FF", "accent": "#FF47CA",
        "background": "#DAFF00", "text": "#072743",
    }
    proposals = demo_compositions(candidate["content"]["text"], seed=41)
    candidate["presentation"] = {
        "logo_mode": "auto", "graphic_mode": "auto", "graphic_variant": "default",
        "graphic_seed": 41, "output_mode": "4x5", "visual_grammar": "ribbons",
        "composition": copy.deepcopy(proposals[1]), "quote_font_size": 92.5,
        "author_font_size": 25.75,
    }
    candidate["composition_candidates"] = proposals
    candidate["proposal_source"] = "model"
    return candidate


class RibbonSessionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.store = self.directory / "styles.json"
        self.source = ribbon_manifest()
        self.assertEqual([], SERVER.validate_manifest(self.source))

    def save(self, candidate=None):
        return saved_styles.save_style(
            "Nastri personali", candidate or self.source, path=self.store, base_dir=ROOT,
        )

    def apply(self, saved, candidate=None, **options):
        return saved_styles.apply_style(
            saved["id"], candidate or self.source, self.source,
            path=self.store, base_dir=ROOT, **options,
        )

    def test_saved_base_reloads_the_exact_selected_geometry_and_independent_sizes(self):
        saved = self.save()
        reloaded = saved_styles.get_style(saved["id"], self.store)
        self.assertEqual(saved, reloaded)
        self.assertEqual(self.source["presentation"], reloaded["presentation"])
        self.assertEqual(self.source["brand"], reloaded["brand"])
        stored = json.loads(self.store.read_text(encoding="utf-8"))["styles"][0]
        for key in ("content", "source", "composition_candidates", "proposal_source"):
            self.assertNotIn(key, stored)

    def test_faithful_reuse_with_same_text_preserves_current_manual_ranges_and_author(self):
        saved = self.save()
        draft = copy.deepcopy(self.source)
        draft["content"]["styles"].append({"start": 0, "end": 3, "type": "underline"})
        before = copy.deepcopy(draft)
        reused = self.apply(saved, draft, reuse_mode="card", text=draft["content"]["text"])
        self.assertEqual(before, draft)
        self.assertEqual(draft["content"], reused["content"])
        self.assertEqual(saved["presentation"], reused["presentation"])
        self.assertEqual(draft["formats"][0], reused["formats"][0])
        self.assertEqual(["4x5", "1x1", "9x16"], [item["id"] for item in reused["formats"]])
        self.assertEqual([], SERVER.validate_manifest(reused))

    def test_new_text_clears_previous_ranges_evidence_author_and_absolute_quote_size(self):
        saved = self.save()
        text = "Una nuova idea cresce grazie a prospettive diverse."
        before = copy.deepcopy(self.source)
        reused = self.apply(saved, reuse_mode="card", text=text)
        self.assertEqual(before, self.source)
        self.assertEqual(text, reused["content"]["text"])
        self.assertEqual([], reused["content"]["styles"])
        self.assertTrue(reused["content"]["styles_customized"])
        self.assertEqual("", reused["content"]["emphasis"])
        self.assertEqual("", reused["content"]["alt_text"])
        self.assertEqual("EDITED", reused["content"]["transformation"])
        self.assertEqual("UNVERIFIED", reused["content"]["evidence_status"])
        self.assertEqual({"label": "", "role": "none"}, reused["content"]["attribution"])
        self.assertEqual("user-supplied", reused["source"]["locator"])
        self.assertNotEqual(self.source["source"], reused["source"])
        self.assertEqual([text], reused["formats"][0]["lines"])
        self.assertNotIn("quote_font_size", reused["presentation"])
        self.assertEqual(25.75, reused["presentation"]["author_font_size"])
        self.assertEqual(saved["presentation"]["composition"], reused["presentation"]["composition"])
        self.assertEqual([], SERVER.validate_manifest(reused))

    def test_new_author_accepts_two_lines_and_can_be_cleared_without_changing_text(self):
        saved = self.save()
        label = "Grace\nRicercatrice"
        reused = self.apply(saved, reuse_mode="card", text=self.source["content"]["text"], attribution=label)
        self.assertEqual({"label": label, "role": "author"}, reused["content"]["attribution"])
        self.assertEqual(self.source["content"]["styles"], reused["content"]["styles"])
        cleared = self.apply(saved, reused, reuse_mode="card", text=reused["content"]["text"], attribution="")
        self.assertEqual({"label": "", "role": "none"}, cleared["content"]["attribution"])
        self.assertEqual([], SERVER.validate_manifest(cleared))

    def test_style_recomposition_inherits_palette_roles_widths_and_ribbon_repertoire(self):
        draft = copy.deepcopy(self.source)
        base = draft["presentation"]["composition"]
        base.update(background_role="primary", text_role="background", highlight_role="text")
        base["ribbons"][0].update(id="wide", color_role="accent", width_ratio=.18)
        base["ribbons"][1].update(id="thin", color_role="text", width_ratio=.04)
        third = copy.deepcopy(base["ribbons"][0])
        third.update(id="third", color_role="primary", width_ratio=.065)
        base["ribbons"].append(third)
        base["crossings"] = []
        saved = self.save(draft)
        reused = self.apply(saved, draft, reuse_mode="style", text="Un altro punto di vista.")
        expected_repertoire = [(item["id"], item["color_role"], item["width_ratio"]) for item in base["ribbons"]]
        self.assertEqual(draft["brand"], reused["brand"])
        self.assertEqual("demo", reused["proposal_source"])
        self.assertEqual(3, len(reused["composition_candidates"]))
        for proposal in reused["composition_candidates"]:
            with self.subTest(proposal=proposal["id"]):
                self.assertEqual(expected_repertoire, [(item["id"], item["color_role"], item["width_ratio"]) for item in proposal["ribbons"]])
                for role in ("background_role", "text_role", "highlight_role"):
                    self.assertEqual(base[role], proposal[role])
                self.assertNotEqual(base["ribbons"], proposal["ribbons"])
                self.assertEqual(proposal, normalize_composition(proposal))
        self.assertEqual(3, len({json.dumps(item["ribbons"], sort_keys=True) for item in reused["composition_candidates"]}))
        self.assertEqual(reused["composition_candidates"][0], reused["presentation"]["composition"])

    def test_explicit_model_candidates_are_selected_exactly_without_demo_replacement(self):
        saved = self.save()
        proposals = demo_compositions("Un testo nuovo", seed=17)
        for index, proposal in enumerate(proposals):
            proposal["id"] = f"authored-{index}"
            proposal["ribbons"][0]["points"][1] = [.123 + index / 10, .456]
        before = copy.deepcopy(proposals)
        reused = self.apply(saved, reuse_mode="style", text="Un testo nuovo", composition_candidates=proposals)
        self.assertEqual(before, proposals)
        self.assertEqual(proposals, reused["composition_candidates"])
        self.assertEqual(proposals[0], reused["presentation"]["composition"])
        self.assertEqual("model", reused["proposal_source"])
        self.assertEqual([], SERVER.validate_manifest(reused))

    def test_new_candidates_require_style_mode_and_a_nonempty_unique_batch(self):
        saved = self.save()
        with self.assertRaisesRegex(ValueError, "reuse_mode style"):
            self.apply(saved, reuse_mode="card", composition_candidates=self.source["composition_candidates"])
        with self.assertRaisesRegex(ValueError, "da una a tre"):
            self.apply(saved, reuse_mode="style", composition_candidates=[])
        duplicated = [self.source["composition_candidates"][0]] * 2
        with self.assertRaisesRegex(ValueError, "distinti"):
            self.apply(saved, reuse_mode="style", composition_candidates=duplicated)

    def test_faithful_reuse_accepts_an_empty_editor_gallery_and_preserves_active_geometry(self):
        reused = self.apply(self.save(), reuse_mode="card", text=self.source["content"]["text"])
        reviewed = SERVER.validate_draft({"base_revision": reused["revision"], "composition_candidates": []}, reused)
        self.assertEqual([], reviewed["composition_candidates"])
        self.assertEqual(reused["presentation"]["composition"], reviewed["presentation"]["composition"])
        self.assertEqual([], SERVER.validate_manifest(reviewed))

    def test_malformed_geometry_is_rejected_for_the_selection_and_model_candidates(self):
        presentation = copy.deepcopy(self.source["presentation"])
        presentation["composition"]["ribbons"][0]["points"] = "M0 0<script/>"
        with self.assertRaisesRegex(ValueError, "points"):
            SERVER.validate_draft({"base_revision": 1, "presentation": presentation}, self.source)
        proposals = copy.deepcopy(self.source["composition_candidates"])
        proposals[0]["quote_box"]["x"] = .99
        with self.assertRaisesRegex(ValueError, "rientrare"):
            SERVER.validate_draft({"base_revision": 1, "composition_candidates": proposals}, self.source)
        self.assertEqual([], SERVER.validate_manifest(self.source))

    def test_approval_feedback_and_disk_application_keep_geometry_sizes_ranges_and_proposals(self):
        draft = SERVER.validate_draft({
            "base_revision": 1,
            "presentation": {**copy.deepcopy(self.source["presentation"]),
                             "composition": copy.deepcopy(self.source["composition_candidates"][2]),
                             "quote_font_size": 108.5, "author_font_size": 30.25},
        }, self.source)
        feedback = SERVER.approval_feedback(draft, 1)
        self.assertEqual(draft["presentation"], feedback["presentation"])
        self.assertEqual(draft["composition_candidates"], feedback["composition_candidates"])
        manifest_path = self.directory / "manifest.json"
        manifest_path.write_text(json.dumps(self.source), encoding="utf-8")
        session = self.directory / "session"
        session.mkdir()
        (session / "session-state.json").write_text(json.dumps({
            "manifest": str(manifest_path.resolve()),
            "feedback_path": str((session / "feedback.json").resolve()),
            "last_feedback_id": None, "applied_feedback_id": None,
        }), encoding="utf-8")
        result = SERVER.record_and_apply_feedback(manifest_path, session, feedback)
        applied = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertTrue(result["changed"])
        self.assertEqual(2, applied["revision"])
        self.assertEqual(draft["presentation"], applied["presentation"])
        self.assertEqual(draft["content"]["styles"], applied["content"]["styles"])
        self.assertEqual(draft["composition_candidates"], applied["composition_candidates"])
        self.assertEqual("model", applied["proposal_source"])

    def test_setting_auto_quote_size_in_feedback_removes_the_previous_absolute_size(self):
        presentation = copy.deepcopy(self.source["presentation"])
        del presentation["quote_font_size"]
        draft = SERVER.validate_draft({"base_revision": 1, "presentation": presentation}, self.source)
        applied = SERVER.review_applier.expected_manifest_after_feedback(self.source, SERVER.approval_feedback(draft, 1))
        self.assertNotIn("quote_font_size", applied["presentation"])
        self.assertEqual(25.75, applied["presentation"]["author_font_size"])
        self.assertEqual(presentation["composition"], applied["presentation"]["composition"])

    def test_session_project_json_roundtrip_keeps_brand_manual_edits_and_selected_proposal(self):
        model = SERVER.session_model(self.source, ROOT)
        project = json.loads(json.dumps(model, ensure_ascii=False))
        for key in ("font_capabilities", "limits", "return_url"):
            project.pop(key, None)
        self.assertEqual([], SERVER.validate_manifest(project))
        reopened = SERVER.session_model(project, ROOT)
        for key in ("content", "presentation", "formats", "brand", "composition_candidates", "proposal_source"):
            self.assertEqual(model[key], reopened[key], key)
        self.assertEqual(64, reopened["limits"]["max_lines"])
        self.assertEqual(self.source["brand"]["font"], reopened["brand"]["font"])

    def test_preview_serialization_returns_the_identical_selected_model_and_each_proposal(self):
        result = SERVER.preview_response(self.source, ROOT, self.source["revision"])
        self.assertEqual(self.source["presentation"], result["model"]["presentation"])
        self.assertEqual("model", result["proposal_source"])
        selected = ET.fromstring(result["previews"][0]["svg"])
        self.assertEqual(self.source["presentation"]["composition"]["id"], selected.attrib["data-composition-id"])
        self.assertEqual(92.5, result["previews"][0]["font_size"])
        self.assertEqual(25.75, result["previews"][0]["author_font_size"])
        self.assertEqual(3, len(result["composition_previews"]))
        for proposal in result["composition_previews"]:
            self.assertEqual(proposal["id"], ET.fromstring(proposal["svg"]).attrib["data-composition-id"])

    def test_prepare_three_numeric_scenes_preserves_text_brand_and_source_for_the_editor(self):
        base = legacy_manifest()
        base["brand"] = copy.deepcopy(self.source["brand"])
        base["formats"].append({
            "id": "1x1", "width": 1080, "height": 1080,
            "lines": [base["content"]["text"]], "text_scale": 1.0,
            "vertical_position": "center",
        })
        before = copy.deepcopy(base)
        proposals = copy.deepcopy(self.source["composition_candidates"])
        prepared = prepare_ribbon_review.prepare(base, proposals, ROOT)
        self.assertEqual(before, base)
        self.assertEqual(before["brand"], prepared["brand"])
        self.assertEqual(before["source"], prepared["source"])
        for key in ("text", "transformation", "evidence_status", "attribution", "emphasis"):
            self.assertEqual(before["content"][key], prepared["content"][key], key)
        self.assertEqual("candidato_selezionato", prepared["state"])
        self.assertEqual("model", prepared["proposal_source"])
        self.assertEqual("ribbons", prepared["presentation"]["visual_grammar"])
        self.assertEqual(proposals, prepared["composition_candidates"])
        self.assertEqual(proposals[0], prepared["presentation"]["composition"])
        self.assertEqual(3, len({json.dumps(item["ribbons"], sort_keys=True) for item in proposals}))
        self.assertEqual(["4x5", "1x1", "9x16"], [item["id"] for item in prepared["formats"]])
        self.assertEqual([before["content"]["text"]], prepared["formats"][0]["lines"])
        self.assertEqual(64, SERVER.session_model(prepared, ROOT)["limits"]["max_lines"])

    def test_prepare_rejects_a_single_scene_and_unavailable_brand_assets(self):
        proposals = self.source["composition_candidates"]
        with self.assertRaisesRegex(ValueError, "tre composizioni distinte"):
            prepare_ribbon_review.prepare(self.source, proposals[:1], ROOT)
        unavailable = copy.deepcopy(self.source)
        unavailable["brand"]["font"]["regular_path"] = str(self.directory / "missing.ttf")
        with self.assertRaisesRegex(ValueError, "Asset non disponibili"):
            prepare_ribbon_review.prepare(unavailable, proposals, ROOT)


if __name__ == "__main__":
    unittest.main()
