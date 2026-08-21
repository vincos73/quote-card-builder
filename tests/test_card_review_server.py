import copy
import importlib.util
import json
import tempfile
import threading
import unittest
import zipfile
from unittest import mock
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request
from urllib.request import urlopen

MODULE_PATH = Path(__file__).parents[1] / "scripts" / "card_review_server.py"
SPEC = importlib.util.spec_from_file_location("card_review_server", MODULE_PATH)
SERVER = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(SERVER)


def manifest():
    return {"schema_version":"0.4","state":"contenuto_approvato","revision":1,"content":{"text":"Una frase verificata.","transformation":"VERBATIM","evidence_status":"VERIFIED","emphasis":"verificata","attribution":{"label":"example.test","role":"publisher"}},"direction":"statement","presentation":{"logo_mode":"auto","graphic_mode":"auto"},"formats":[{"id":"4x5","width":1440,"height":1800,"lines":["Una frase verificata."],"text_scale":1.0,"vertical_position":"center"}],"brand":{"name":"Test","colors":{"primary":"#072743","accent":"#E3F4FF","background":"#FEFDFB","text":"#323232"},"font":{"family":"Test Sans"}},"source":{"title":"Source","locator":"test://source"},"output":{"basename":"quote"}}


class CardReviewServerTests(unittest.TestCase):
    def test_accepts_contract_04(self): self.assertEqual([], SERVER.validate_manifest(manifest()))

    def test_arial_system_baseline_enables_real_standard_treatments(self):
        item = manifest()
        item["brand"]["font"] = {"family": "Arial"}
        capabilities = SERVER.font_capabilities(item, Path.cwd())
        self.assertFalse(capabilities["embedded"])
        self.assertEqual({"available": True, "exact": True}, capabilities["styles"]["bold"])
        self.assertEqual({"available": True, "exact": True}, capabilities["styles"]["italic"])
    def test_static_svg_asset_is_allowlisted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            logo = root / "logo.svg"
            logo.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8")
            self.assertEqual(logo.resolve(), SERVER.asset_path(root, "/logo.svg"))
            self.assertEqual("image/svg+xml", SERVER.MIME_TYPES[".svg"])
    def test_legacy_contract_without_graphic_mode_defaults_to_auto(self):
        item = manifest(); item["presentation"].pop("graphic_mode")
        self.assertEqual([], SERVER.validate_manifest(item))
    def test_accepts_selected_candidate_as_editor_seed(self):
        item = manifest(); item["state"] = "candidato_selezionato"
        self.assertEqual([], SERVER.validate_manifest(item))

    def test_text_edit_preserves_user_declarations(self):
        source = manifest()
        draft = SERVER.validate_draft({
            "base_revision": 1,
            "text": "Una frase riscritta.",
            "transformation": "PARAPHRASE",
            "evidence_status": "VERIFIED",
            "attribution": {"label": "Ada", "role": "speaker"},
            "emphasis": "riscritta.",
            "presentation": {"logo_mode": "auto"},
            "formats": [{"id": "4x5", "width": 1440, "height": 1800, "lines": ["Una frase", "riscritta."], "text_scale": 1.0, "vertical_position": "center"}],
        }, source)
        self.assertEqual("Una frase riscritta.", draft["content"]["text"])
        self.assertEqual("PARAPHRASE", draft["content"]["transformation"])
        self.assertEqual("VERIFIED", draft["content"]["evidence_status"])
        self.assertEqual({"label": "Ada", "role": "speaker"}, draft["content"]["attribution"])
        self.assertEqual("user", draft["content"]["declared_by"])

    def test_modified_text_can_keep_user_declared_verbatim(self):
        source = manifest()
        draft = SERVER.validate_draft({
            "base_revision": 1,
            "text": "Una frase diversa.",
            "transformation": "VERBATIM",
            "emphasis": "",
            "formats": [{"id": "4x5", "width": 1440, "height": 1800, "lines": ["Una frase diversa."], "text_scale": 1.0, "vertical_position": "center"}],
        }, source)
        self.assertEqual("VERBATIM", draft["content"]["transformation"])
    def test_graphic_mode_is_editable_but_constrained(self):
        source = manifest()
        draft = SERVER.validate_draft({
            "base_revision": 1,
            "presentation": {"logo_mode": "auto", "graphic_mode": "hidden"},
        }, source)
        self.assertEqual("hidden", draft["presentation"]["graphic_mode"])
        source["presentation"]["graphic_mode"] = "custom"
        self.assertTrue(SERVER.validate_manifest(source))

    def test_graphic_variant_is_direction_bound_and_defaults_for_legacy_manifests(self):
        source = manifest()
        self.assertEqual([], SERVER.validate_manifest(source))
        draft = SERVER.validate_draft({
            "base_revision": 1,
            "presentation": {**source["presentation"], "graphic_variant": "modules"},
        }, source)
        self.assertEqual("modules", draft["presentation"]["graphic_variant"])
        source["presentation"]["graphic_variant"] = "route_map"
        self.assertTrue(SERVER.validate_manifest(source))
    def test_output_mode_is_editable_but_constrained(self):
        source = manifest()
        draft = SERVER.validate_draft({
            "base_revision": 1,
            "presentation": {**source["presentation"], "output_mode": "1x1"},
        }, source)
        self.assertEqual("1x1", draft["presentation"]["output_mode"])
        source["presentation"]["output_mode"] = "pdf"
        self.assertTrue(SERVER.validate_manifest(source))

    def test_statement_accepts_highlight_in_review_draft(self):
        source = manifest()
        candidate = SERVER.validate_draft({
            "base_revision": 1,
            "styles": [{"start": 0, "end": 3, "type": "highlight"}],
        }, source)
        self.assertEqual([{"start": 0, "end": 3, "type": "highlight"}], candidate["content"]["styles"])

    def test_production_formats_follow_the_selected_output(self):
        source = manifest()
        source["formats"] = [
            source["formats"][0],
            {"id":"1x1","width":1080,"height":1080,"lines":["Una frase verificata."],"text_scale":1.0,"vertical_position":"center"},
            {"id":"9x16","width":1080,"height":1920,"lines":["Una frase verificata."],"text_scale":1.0,"vertical_position":"center"},
        ]
        source["presentation"]["output_mode"] = "1x1"
        mode, selected = SERVER.production_formats(source)
        self.assertEqual("1x1", mode)
        self.assertEqual(["1x1"], [item["id"] for item in selected])

    def test_generated_assets_are_allowlisted_and_cannot_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "output"
            output.mkdir()
            png = output / "quote.png"
            png.write_bytes(b"png")
            self.assertEqual(png.resolve(), SERVER.generated_asset_path(root, "/api/output/output/quote.png"))
            self.assertIsNone(SERVER.generated_asset_path(root, "/api/output/../quote.png"))
            self.assertIsNone(SERVER.generated_asset_path(root, "/api/output/output/quote.exe"))

    def test_persisted_outputs_restore_authenticated_download_links(self):
        outputs = [{
            "format": "1x1", "kind": "png", "filename": "quote card.png",
            "relative_path": "output/quote card.png",
            "absolute_path": "/tmp/output/quote card.png",
        }]
        result = SERVER.output_payload(outputs, "token+/=")
        self.assertEqual("1x1", result[0]["format"])
        self.assertEqual(
            "/api/output/output/quote%20card.png?token=token%2B%2F%3D",
            result[0]["url"],
        )
        self.assertEqual("/tmp/output/quote card.png", result[0]["absolute_path"])

    def test_legacy_persisted_output_recovers_its_absolute_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = SERVER.output_payload([{
                "format": "1x1", "kind": "png", "filename": "quote.png",
                "relative_path": "output/quote.png",
            }], "token", root)
            self.assertEqual(str((root / "output" / "quote.png").resolve()), result[0]["absolute_path"])

    def test_generate_production_pack_writes_a_fallback_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "manifest.json"
            source = manifest()
            source["presentation"]["output_mode"] = "4x5"
            manifest_path.write_text(json.dumps(source), encoding="utf-8")
            # No converter at all: the point of this test is the declared
            # SVG fallback, and on a machine with Chrome installed the
            # chain would legitimately succeed and never reach it.
            with mock.patch.object(SERVER.pack.raster, "BACKENDS", ()):
                result = SERVER.generate_production_pack(source, manifest_path, root / "session", None, None)
            self.assertEqual(["4x5"], [item["format"] for item in result["outputs"]])
            self.assertEqual("svg", result["outputs"][0]["kind"])
            self.assertTrue((root / "session" / "production" / result["outputs"][0]["relative_path"]).is_file())
            self.assertEqual(
                str((root / "session" / "production" / result["outputs"][0]["relative_path"]).resolve()),
                result["outputs"][0]["absolute_path"],
            )
            self.assertTrue(Path(result["qa_report"]).is_file())
    def test_rejects_mutable_or_invalid_visual_contract(self):
        item = manifest(); item["revision"] = 0; item["formats"][0]["text_scale"] = 1.2
        self.assertTrue(SERVER.validate_manifest(item))
    def test_draft_preserves_editorial_content(self):
        source = manifest(); draft = SERVER.validate_draft({"base_revision":1,"direction":"editorial","emphasis":"frase","presentation":source["presentation"],"formats":source["formats"]}, source)
        self.assertEqual(source["content"]["text"], draft["content"]["text"])
        self.assertEqual("frase", draft["content"]["emphasis"])
    def test_session_rejects_rebound_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); first, second = root / "one.json", root / "two.json"
            first.write_text(json.dumps(manifest()), encoding="utf-8"); second.write_text(json.dumps(manifest()), encoding="utf-8")
            session = root / "session"; session.mkdir()
            (session / "session-state.json").write_text(json.dumps({"manifest": str(first.resolve())}), encoding="utf-8")
            with self.assertRaises(ValueError): SERVER.create_server(second, root / "session")

    def test_profile_export_endpoint_downloads_a_portable_json(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(manifest()), encoding="utf-8")
            store = root / "profiles.json"
            saved = SERVER.brand_profiles.save_profile("Test Social", manifest()["brand"], store)
            server, token = SERVER.create_server(
                manifest_path, root / "session", profile_store=store,
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                port = server.server_address[1]
                url = (
                    f"http://127.0.0.1:{port}/api/profiles/export"
                    f"?profile_id={saved['id']}&token={token}"
                )
                with urlopen(url) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                    disposition = response.headers["Content-Disposition"]
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)
        self.assertEqual("quote-card-brand", payload["profile_type"])
        self.assertEqual("Test Social", payload["name"])
        self.assertNotIn("fingerprint", payload)
        self.assertEqual(
            'attachment; filename="test-social-quote-card-brand.json"',
            disposition,
        )

    def test_recorded_feedback_is_applied_before_returning(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(manifest()), encoding="utf-8")
            session_dir = root / "session"
            session_dir.mkdir()
            feedback_path = session_dir / "feedback.json"
            (session_dir / "session-state.json").write_text(json.dumps({
                "manifest": str(manifest_path.resolve()),
                "feedback_path": str(feedback_path.resolve()),
                "last_feedback_id": None,
                "applied_feedback_id": None,
            }), encoding="utf-8")
            item = manifest()
            feedback = {
                "feedback_id": "feedback-immediate", "submitted_at": "2026-08-11T00:00:00Z",
                "action": "feedback", "base_revision": 1, "editorial_responsibility": "user",
                "content": {
                    "text": item["content"]["text"],
                    "transformation": item["content"]["transformation"],
                    "evidence_status": item["content"]["evidence_status"],
                    "attribution": item["content"]["attribution"],
                    "styles": [], "declared_by": "user",
                },
                "direction": "editorial", "emphasis": item["content"]["emphasis"],
                "presentation": item["presentation"],
                "formats": [{
                    "id": "4x5", "lines": ["Una frase verificata."],
                    "text_scale": 1.0, "vertical_position": "center",
                }],
                "overall_note": "",
            }
            result = SERVER.record_and_apply_feedback(manifest_path, session_dir, feedback)
            self.assertTrue(result["changed"])
            updated = json.loads(manifest_path.read_text(encoding="utf-8"))
            state = json.loads((session_dir / "session-state.json").read_text(encoding="utf-8"))
            self.assertEqual(2, updated["revision"])
            self.assertEqual("editorial", updated["direction"])
            self.assertEqual(state["last_feedback_id"], state["applied_feedback_id"])

    def test_seven_lines_are_rejected_before_persistence_and_session_is_reusable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "manifest.json"
            source = manifest()
            manifest_path.write_text(json.dumps(source), encoding="utf-8")
            session_dir = root / "session"
            session_dir.mkdir()
            feedback_path = session_dir / "feedback.json"
            previous_feedback = {"feedback_id": "feedback-previous"}
            feedback_path.write_text(json.dumps(previous_feedback), encoding="utf-8")
            state_before = {
                "manifest": str(manifest_path.resolve()),
                "feedback_path": str(feedback_path.resolve()),
                "manifest_revision": 1,
                "last_feedback_id": "feedback-previous",
                "applied_feedback_id": "feedback-previous",
            }
            (session_dir / "session-state.json").write_text(
                json.dumps(state_before), encoding="utf-8",
            )

            invalid_draft = copy.deepcopy(source)
            invalid_draft["formats"][0]["lines"] = [
                "Una", "frase", "verificata.", "", "", "", "",
            ]
            with self.assertRaisesRegex(ValueError, "da 1 a 6"):
                SERVER.validate_draft({
                    "base_revision": 1,
                    "formats": invalid_draft["formats"],
                }, source)
            invalid_feedback = SERVER.approval_feedback(invalid_draft, 1)
            with self.assertRaisesRegex(SERVER.review_applier.ReviewError, "da 1 a 6"):
                SERVER.record_and_apply_feedback(manifest_path, session_dir, invalid_feedback)

            self.assertEqual(
                state_before,
                json.loads((session_dir / "session-state.json").read_text(encoding="utf-8")),
            )
            self.assertEqual(
                previous_feedback,
                json.loads(feedback_path.read_text(encoding="utf-8")),
            )
            self.assertEqual(1, json.loads(manifest_path.read_text(encoding="utf-8"))["revision"])

            valid_feedback = SERVER.approval_feedback(source, 1)
            applied = SERVER.record_and_apply_feedback(manifest_path, session_dir, valid_feedback)
            state_after = json.loads((session_dir / "session-state.json").read_text(encoding="utf-8"))
            self.assertTrue(applied["approval_requested"])
            self.assertEqual(state_after["last_feedback_id"], state_after["applied_feedback_id"])

    def test_failed_apply_rolls_back_manifest_feedback_and_pending_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "manifest.json"
            source = manifest()
            manifest_path.write_text(json.dumps(source), encoding="utf-8")
            session_dir = root / "session"
            session_dir.mkdir()
            feedback_path = session_dir / "feedback.json"
            previous_feedback = {"feedback_id": "feedback-previous"}
            feedback_path.write_text(json.dumps(previous_feedback), encoding="utf-8")
            state_before = {
                "manifest": str(manifest_path.resolve()),
                "feedback_path": str(feedback_path.resolve()),
                "manifest_revision": 1,
                "last_feedback_id": "feedback-previous",
                "applied_feedback_id": "feedback-previous",
            }
            (session_dir / "session-state.json").write_text(
                json.dumps(state_before), encoding="utf-8",
            )
            draft = copy.deepcopy(source)
            draft["direction"] = "editorial"
            feedback = SERVER.approval_feedback(draft, 1)
            expected = SERVER.review_applier.expected_manifest_after_feedback(source, feedback)

            def fail_after_manifest_write(*_args):
                SERVER.atomic_write_json(manifest_path, expected)
                raise SERVER.review_applier.ReviewError("errore applicazione simulato")

            with mock.patch.object(
                SERVER.review_applier, "apply_review", side_effect=fail_after_manifest_write,
            ):
                with self.assertRaisesRegex(
                    SERVER.review_applier.ReviewError, "errore applicazione simulato",
                ):
                    SERVER.record_and_apply_feedback(manifest_path, session_dir, feedback)

            self.assertEqual(source, json.loads(manifest_path.read_text(encoding="utf-8")))
            self.assertEqual(
                state_before,
                json.loads((session_dir / "session-state.json").read_text(encoding="utf-8")),
            )
            self.assertEqual(
                previous_feedback,
                json.loads(feedback_path.read_text(encoding="utf-8")),
            )

    def test_session_exposes_the_shared_line_limit(self):
        self.assertEqual(6, SERVER.MAX_LINES)
        self.assertEqual(SERVER.MAX_LINES, SERVER.review_applier.MAX_LINES)
        self.assertEqual(
            {"max_lines": SERVER.MAX_LINES},
            SERVER.session_model(manifest(), Path.cwd())["limits"],
        )

    def test_generate_rejects_seven_lines_without_poisoning_the_http_session(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(manifest()), encoding="utf-8")
            session_dir = root / "session"
            server, token = SERVER.create_server(manifest_path, session_dir)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                endpoint = f"http://127.0.0.1:{server.server_address[1]}"

                def post_generate(lines):
                    body = json.dumps({
                        "base_revision": 1,
                        "formats": [{
                            "id": "4x5", "width": 1440, "height": 1800,
                            "lines": lines, "text_scale": 1.0,
                            "vertical_position": "center",
                        }],
                    }).encode("utf-8")
                    return urlopen(Request(
                        f"{endpoint}/api/generate?token={token}",
                        data=body,
                        headers={"Content-Type": "application/json"},
                        method="POST",
                    ))

                with self.assertRaises(HTTPError) as rejected:
                    post_generate([
                        "Una", "frase", "verificata.", "", "", "", "",
                    ])
                self.assertEqual(422, rejected.exception.code)
                rejected.exception.close()

                with urlopen(f"{endpoint}/api/status?token={token}") as response:
                    status = json.loads(response.read().decode("utf-8"))
                self.assertFalse(status["feedback_pending"])
                self.assertIsNone(status["last_feedback_id"])

                fake_generation = {
                    "valid": True,
                    "state": "qa",
                    "formats": [],
                    "contact_sheet": "",
                    "qa_report": str(root / "qa.json"),
                    "warnings": [],
                    "outputs": [],
                    "production_manifest": str(root / "production-manifest.json"),
                    "production_root": str(root / "production"),
                }
                (root / "production").mkdir()
                with (
                    mock.patch.object(
                        SERVER, "generate_production_pack", return_value=fake_generation,
                    ),
                    mock.patch.object(SERVER, "chatbot_cli_path", return_value=None),
                ):
                    with post_generate(["Una frase verificata."]) as response:
                        generated = json.loads(response.read().decode("utf-8"))
                self.assertTrue(generated["applied"])
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

    def test_empty_emphasis_is_valid(self):
        item = manifest(); item["content"]["emphasis"] = ""
        self.assertEqual([], SERVER.validate_manifest(item))

    def test_draft_accepts_spacer_rows_and_inline_styles(self):
        source = manifest()
        draft = SERVER.validate_draft({
            "base_revision": 1,
            "emphasis": "",
            "styles": [{"start": 4, "end": 9, "type": "underline"}],
            "formats": [{
                "id": "4x5", "width": 1440, "height": 1800,
                "lines": ["Una", "", "frase verificata."],
                "text_scale": 1.0, "vertical_position": "center",
            }],
        }, source)
        self.assertEqual(["Una", "", "frase verificata."], draft["formats"][0]["lines"])
        self.assertEqual("underline", draft["content"]["styles"][0]["type"])

    def test_rejects_invalid_inline_style(self):
        item = manifest()
        item["content"]["styles"] = [{"start": 0, "end": 999, "type": "bold"}]
        self.assertTrue(SERVER.validate_manifest(item))

    def test_session_reports_missing_and_exact_font_faces(self):
        item = manifest()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            regular = root / "Regular.ttf"; regular.write_bytes(b"regular")
            italic = root / "Italic.ttf"; italic.write_bytes(b"italic")
            item["brand"]["font"].update({"regular_path": str(regular), "italic_path": str(italic)})
            model = SERVER.session_model(item, root)
        self.assertTrue(model["font_capabilities"]["styles"]["bold"]["available"])
        self.assertFalse(model["font_capabilities"]["styles"]["bold"]["exact"])
        self.assertTrue(model["font_capabilities"]["styles"]["italic"]["exact"])

    def test_session_exposes_only_a_valid_native_return_link(self):
        thread_id = "01a0150e-8a7c-7f73-a731-22f77de51643"
        return_url = SERVER.return_url_for_thread(thread_id)
        model = SERVER.session_model(manifest(), Path.cwd(), return_url)
        self.assertEqual(f"codex://threads/{thread_id}", model["return_url"])
        with self.assertRaises(ValueError):
            SERVER.return_url_for_thread("https://example.test/escape")

    def test_live_quality_gate_reports_checks(self):
        item = manifest()
        with tempfile.TemporaryDirectory() as directory:
            previews = SERVER.render_preview(item, Path(directory))
            qa = SERVER.preview_quality(item, previews, Path(directory))
        self.assertTrue(qa["passed"])
        self.assertIn("contrast", qa["checks"])
        self.assertIn("fitting", qa["checks"])
        self.assertEqual([], qa["warnings"])

    def test_square_contextual_fallback_fits_inside_the_field_sheet(self):
        item = manifest()
        item["direction"] = "contextual"
        item["content"].update({
            "text": "Il passaggio non è da uomo a macchina. È dal task all’obiettivo.",
            "emphasis": "",
        })
        item["formats"] = [{
            "id": "1x1", "width": 1080, "height": 1080,
            "lines": ["Il passaggio non è", "da uomo a macchina.", "È dal task", "all’obiettivo."],
            "text_scale": 1.0, "vertical_position": "center",
        }]
        with tempfile.TemporaryDirectory() as directory:
            previews = SERVER.render_preview(item, Path(directory))
            qa = SERVER.preview_quality(item, previews, Path(directory))
        self.assertTrue(qa["passed"])
        self.assertEqual(previews[0]["font_size"], previews[0]["maximum_font_size"])
        self.assertEqual(1.0, previews[0]["text_scale"])

    def test_preview_and_quality_gate_share_the_true_max_fit(self):
        item = manifest()
        item["direction"] = "editorial"
        item["formats"][0]["vertical_position"] = "lower"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            preview = SERVER.render_preview(item, root)[0]
            qa = SERVER.preview_quality(item, [preview], root)
            adapted = SERVER.pack.proof_manifest_for_format(item, item["formats"][0])
            adapted["canvas"] = {"width": 1440, "height": 1800}
            measurement = SERVER.pack.layout_measurement(
                item["formats"][0]["lines"], preview["font_size"], adapted, root,
                "editorial", 1440, 1800, "lower",
            )
        self.assertTrue(qa["passed"])
        self.assertTrue(measurement["fits"])
        self.assertEqual(preview["font_size"], preview["maximum_font_size"])
        self.assertIn("max_fit", preview["fitting"])

    def test_semantic_combinations_are_user_owned_not_quality_failures(self):
        item = manifest()
        item["content"].update({
            "transformation": "PARAPHRASE",
            "evidence_status": "CONFLICT",
            "attribution": {"label": "Ada", "role": "speaker"},
            })
        with tempfile.TemporaryDirectory() as directory:
            previews = SERVER.render_preview(item, Path(directory))
            qa = SERVER.preview_quality(item, previews, Path(directory))
        self.assertTrue(qa["passed"])

    def test_live_quality_gate_flags_contrast_and_auto_fits_overflow(self):
        item = manifest()
        item["brand"]["colors"]["background"] = item["brand"]["colors"]["primary"]
        item["content"].update({"text": "Supercalifragilistichespiralidoso.", "emphasis": ""})
        item["formats"][0]["lines"] = ["Supercalifragilistichespiralidoso."]
        item["formats"][0]["text_scale"] = 1.08
        with tempfile.TemporaryDirectory() as directory:
            previews = SERVER.render_preview(item, Path(directory))
            qa = SERVER.preview_quality(item, previews, Path(directory))
        self.assertFalse(qa["passed"])
        codes = {warning["code"] for warning in qa["warnings"]}
        self.assertTrue(any(code.startswith("visual_contrast") for code in codes))
        self.assertNotIn("text_fit", codes)
        self.assertTrue(previews[0]["auto_fitted"])
        self.assertLess(previews[0]["font_size"], previews[0]["requested_font_size"])
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "quality gate"):
                SERVER.ensure_approvable(item, Path(directory))

    def test_square_variants_share_one_auto_fit_contract(self):
        item = manifest()
        item["content"].update({
            "text": "L’intelligenza artificiale non sostituisce il lavoro: ne riscrive i confini.",
            "emphasis": "ne riscrive i confini.",
        })
        item["formats"] = [{
            "id": "1x1", "width": 1080, "height": 1080,
            "lines": ["L’intelligenza artificiale", "non sostituisce il lavoro:", "ne riscrive i confini."],
            "text_scale": 1.0, "vertical_position": "center",
        }]
        for direction in ("statement", "contextual"):
            item["direction"] = direction
            with tempfile.TemporaryDirectory() as directory:
                previews = SERVER.render_preview(item, Path(directory))
                qa = SERVER.preview_quality(item, previews, Path(directory))
            self.assertTrue(qa["passed"], (direction, qa["warnings"]))
            self.assertNotIn("text_fit", {warning["code"] for warning in qa["warnings"]})


class AltTextDraftTests(unittest.TestCase):
    def test_validate_manifest_accepts_optional_alt_text(self):
        item = manifest()
        item["content"]["alt_text"] = "Descrizione scelta a mano."
        self.assertEqual([], SERVER.validate_manifest(item))

    def test_validate_manifest_rejects_alt_text_over_the_ceiling(self):
        item = manifest()
        item["content"]["alt_text"] = "x" * (SERVER.ALT_TEXT_MAX_LENGTH + 1)
        self.assertTrue(SERVER.validate_manifest(item))

    def test_draft_carries_alt_text_override_and_trims_it(self):
        source = manifest()
        draft = SERVER.validate_draft({
            "base_revision": 1, "alt_text": "  Descrizione con spazi.  ",
        }, source)
        self.assertEqual("Descrizione con spazi.", draft["content"]["alt_text"])

    def test_draft_defaults_alt_text_to_empty(self):
        source = manifest()
        draft = SERVER.validate_draft({"base_revision": 1}, source)
        self.assertEqual("", draft["content"]["alt_text"])


class PreviewScoreTests(unittest.TestCase):
    def test_clean_card_scores_full_marks_in_every_category(self):
        item = manifest()
        with tempfile.TemporaryDirectory() as directory:
            previews = SERVER.render_preview(item, Path(directory))
            qa = SERVER.preview_quality(item, previews, Path(directory))
            score = SERVER.preview_score(item, previews, qa)
        self.assertTrue(qa["passed"])
        self.assertEqual(100, score["categories"]["contrast"])
        self.assertEqual(100, score["categories"]["fit"])
        self.assertEqual(100, score["categories"]["structure"])
        self.assertEqual(100, score["overall"])

    def test_low_contrast_and_auto_fit_pull_the_score_down(self):
        item = manifest()
        item["brand"]["colors"]["background"] = item["brand"]["colors"]["primary"]
        item["content"].update({"text": "Supercalifragilistichespiralidoso.", "emphasis": ""})
        item["formats"][0]["lines"] = ["Supercalifragilistichespiralidoso."]
        item["formats"][0]["text_scale"] = 1.08
        with tempfile.TemporaryDirectory() as directory:
            previews = SERVER.render_preview(item, Path(directory))
            qa = SERVER.preview_quality(item, previews, Path(directory))
            score = SERVER.preview_score(item, previews, qa)
        # A ratio of exactly 1:1 (identical colours) is the worst contrast
        # possible, but the score is a percentage of the AAA ceiling (7:1),
        # so even the floor lands at 1/7 rather than literal zero.
        self.assertLess(score["categories"]["contrast"], 20)
        self.assertLess(score["categories"]["fit"], 100)
        self.assertLess(score["categories"]["structure"], 100)
        self.assertLess(score["overall"], 100)


class MultiFormatZipTests(unittest.TestCase):
    def multi_format_manifest(self):
        source = manifest()
        source["formats"] = [
            source["formats"][0],
            {"id": "1x1", "width": 1080, "height": 1080, "lines": ["Una frase verificata."], "text_scale": 1.0, "vertical_position": "center"},
            {"id": "9x16", "width": 1080, "height": 1920, "lines": ["Una frase verificata."], "text_scale": 1.0, "vertical_position": "center"},
        ]
        source["presentation"]["output_mode"] = "all"
        return source

    def test_all_formats_are_bundled_into_one_zip(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "manifest.json"
            source = self.multi_format_manifest()
            manifest_path.write_text(json.dumps(source), encoding="utf-8")
            with mock.patch.object(SERVER.pack.raster, "BACKENDS", ()):
                generation = SERVER.generate_production_pack(source, manifest_path, root / "session", None, None)
            self.assertEqual(1, len(generation["outputs"]))
            output = generation["outputs"][0]
            self.assertEqual("zip", output["kind"])
            zip_path = Path(generation["production_root"]) / output["relative_path"]
            self.assertEqual(str(zip_path.resolve()), output["absolute_path"])
            self.assertTrue(zip_path.is_file())
            with zipfile.ZipFile(zip_path) as archive:
                names = archive.namelist()
            self.assertTrue(any(name.endswith("4x5.svg") for name in names))
            self.assertTrue(any(name.endswith("1x1.svg") for name in names))
            self.assertTrue(any(name.endswith("9x16.svg") for name in names))

    def test_single_format_selection_still_yields_one_plain_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "manifest.json"
            source = self.multi_format_manifest()
            source["presentation"]["output_mode"] = "4x5"
            manifest_path.write_text(json.dumps(source), encoding="utf-8")
            with mock.patch.object(SERVER.pack.raster, "BACKENDS", ()):
                generation = SERVER.generate_production_pack(source, manifest_path, root / "session", None, None)
            self.assertEqual(1, len(generation["outputs"]))
            self.assertEqual("svg", generation["outputs"][0]["kind"])
            self.assertEqual("4x5", generation["outputs"][0]["format"])


if __name__ == "__main__": unittest.main()
