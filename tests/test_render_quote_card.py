import importlib.util
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "render_quote_card.py"
SPEC = importlib.util.spec_from_file_location("render_quote_card", MODULE_PATH)
RENDERER = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(RENDERER)


def valid_visual_manifest():
    return {
        "schema_version": "0.2",
        "state": "contenuto_approvato",
        "content": {
            "text": "Un agente non si commuove per il tuo claim: confronta.",
            "lines": [
                "Un agente non si commuove",
                "per il tuo claim: confronta.",
            ],
            "transformation": "VERBATIM",
            "evidence_status": "VERIFIED",
            "use_quotation_marks": True,
            "emphasis": "confronta.",
            "attribution": {"label": "example.test", "role": "publisher"},
        },
        "canvas": {"width": 1440, "height": 1800},
        "direction": "statement",
        "brand": {
            "name": "Test Brand",
            "colors": {
                "primary": "#072743",
                "accent": "#E3F4FF",
                "background": "#FEFDFB",
                "text": "#323232",
            },
            "font": {"family": "Test Sans"},
        },
        "source": {"title": "Test source", "locator": "test://source"},
        "output": {"basename": "test-quote"},
    }


class VisualManifestTests(unittest.TestCase):
    def test_accepts_valid_manifest(self):
        manifest = valid_visual_manifest()
        self.assertEqual([], RENDERER.validate_visual_manifest(manifest, Path.cwd()))

    def test_rejects_changed_line_breaks(self):
        manifest = valid_visual_manifest()
        manifest["content"]["lines"][1] = "per il claim: confronta."
        codes = {error["code"] for error in RENDERER.validate_visual_manifest(manifest, Path.cwd())}
        self.assertIn("text_changed", codes)

    def test_rejects_unapproved_content(self):
        manifest = valid_visual_manifest()
        manifest["state"] = "candidati_pronti"
        codes = {error["code"] for error in RENDERER.validate_visual_manifest(manifest, Path.cwd())}
        self.assertIn("approval_required", codes)

    def test_renders_conflicted_content_when_user_declares_it(self):
        manifest = valid_visual_manifest()
        manifest["content"]["evidence_status"] = "CONFLICT"
        self.assertEqual([], RENDERER.validate_visual_manifest(manifest, Path.cwd()))

    def test_rejects_low_contrast_brand(self):
        manifest = valid_visual_manifest()
        manifest["brand"]["colors"]["primary"] = "#777777"
        manifest["brand"]["colors"]["background"] = "#888888"
        manifest["brand"]["colors"]["accent"] = "#999999"
        codes = {error["code"] for error in RENDERER.validate_visual_manifest(manifest, Path.cwd())}
        self.assertIn("contrast", codes)

    def test_rejects_unsafe_svg_logo(self):
        manifest = valid_visual_manifest()
        with tempfile.TemporaryDirectory() as temp_dir:
            logo = Path(temp_dir) / "logo.svg"
            logo.write_text('<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>', encoding="utf-8")
            manifest["brand"]["logo"] = {"dark_path": str(logo)}
            codes = {
                error["code"]
                for error in RENDERER.validate_visual_manifest(manifest, Path(temp_dir))
            }
        self.assertIn("unsafe_svg", codes)

    def test_renders_well_formed_svg_for_every_direction(self):
        manifest = valid_visual_manifest()
        for direction in RENDERER.DIRECTIONS:
            svg = RENDERER.render_svg(manifest, Path.cwd(), direction)
            root = ET.fromstring(svg)
            self.assertEqual("{http://www.w3.org/2000/svg}svg", root.tag)
            self.assertIn("Un agente non si commuove", svg)
            self.assertIn("confronta.", svg)
            self.assertIn("example.test", svg)

    def test_directions_have_distinct_semantic_signs(self):
        manifest = valid_visual_manifest()
        editorial = RENDERER.render_svg(manifest, Path.cwd(), "editorial")
        statement = RENDERER.render_svg(manifest, Path.cwd(), "statement")
        contextual = RENDERER.render_svg(manifest, Path.cwd(), "contextual")

        self.assertIn('class="quote-corner-mark quote-corner-mark--top"', editorial)
        self.assertIn('direction-graphic--contours', editorial)
        self.assertNotIn('PAGINA / 01', editorial)
        self.assertNotIn('class="source-bar"', editorial)
        self.assertIn('class="marks"', statement)
        self.assertIn('direction-graphic--echo', statement)
        self.assertNotIn('MANIFESTO / 02', statement)
        self.assertNotIn('class="source-bar"', statement)
        self.assertIn('class="marks"', contextual)
        self.assertIn('direction-graphic--field', contextual)
        self.assertNotIn('DOSSIER / 03', contextual)
        self.assertNotIn('class="source-bar"', contextual)
        self.assertNotIn("ESTRATTO VERIFICATO", contextual)

    def test_untreated_first_preview_has_one_distinct_typographic_cue_per_direction(self):
        manifest = valid_visual_manifest()
        manifest["content"].update({
            "text": "Prima riga. Seconda riga. Terza riga.",
            "lines": ["Prima riga.", "Seconda riga.", "Terza riga."],
            "emphasis": "",
            "styles": [],
        })
        # The cue is computed once on the canonical joined text (the final
        # clause, snapped to a word boundary), not per-format wrapped lines,
        # so the same words emphasise across 4:5/1:1/9:16 alike.
        self.assertEqual(
            [{"start": 20, "end": 37, "type": "bold"}],
            RENDERER.initial_direction_styles(manifest["content"]["text"], "editorial"),
        )
        editorial = RENDERER.render_svg(manifest, Path.cwd(), "editorial")
        statement = RENDERER.render_svg(manifest, Path.cwd(), "statement")
        contextual = RENDERER.render_svg(manifest, Path.cwd(), "contextual")
        self.assertIn('<tspan font-weight="700">Terza riga.</tspan>', editorial)
        self.assertIn('fill="#E3F4FF"', statement)
        self.assertIn('class="highlight-marker"', contextual)

    def test_arial_neutral_baseline_uses_the_cross_platform_stack(self):
        manifest = valid_visual_manifest()
        manifest["brand"]["font"]["family"] = "Arial"
        svg = RENDERER.render_svg(manifest, Path.cwd(), "editorial")
        self.assertIn("font-family:'Arial','Helvetica Neue',Helvetica,sans-serif", svg)

    def test_direction_graphic_can_be_hidden_without_changing_direction(self):
        manifest = valid_visual_manifest()
        for direction in RENDERER.DIRECTIONS:
            svg = RENDERER.render_svg(
                manifest,
                Path.cwd(),
                direction,
                render_options={"graphic_mode": "hidden"},
            )
            self.assertNotIn('class="direction-graphic', svg)
            self.assertIn(f"Quote card {direction}", svg)

    def test_all_quote_marks_respect_the_user_toggle(self):
        manifest = valid_visual_manifest()
        for direction in RENDERER.DIRECTIONS:
            svg = RENDERER.render_svg(
                manifest,
                Path.cwd(),
                direction,
                render_options={"show_quotation_marks": False},
            )
            self.assertNotIn('class="marks"', svg)

    def test_statement_uses_a_dense_poster_stack_and_scaled_emphasis(self):
        manifest = valid_visual_manifest()
        manifest["content"].update({
            "text": "Il passaggio non è da uomo a macchina. È dal task all’obiettivo.",
            "lines": ["Il passaggio non è", "da uomo a macchina.", "È dal task all’obiettivo."],
            "emphasis": "",
            "styles": [{"start": 45, "end": 64, "type": "bold"}],
        })
        svg = RENDERER.render_svg(manifest, Path.cwd(), "statement")
        root = ET.fromstring(svg)
        quote = root.find(".//{http://www.w3.org/2000/svg}text[@data-layout='statement-poster']")
        self.assertIsNotNone(quote)
        rows = list(quote)
        self.assertEqual(3, len(rows))
        accent_rows = [row for row in rows if row.attrib.get("fill") == "#E3F4FF"]
        self.assertEqual(1, len(accent_rows))
        self.assertGreater(float(accent_rows[0].attrib["font-size"]), float(rows[0].attrib["font-size"]))
        self.assertIn("IL PASSAGGIO NON È", svg)
        self.assertIn("Il passaggio non è da uomo a macchina.", svg)

    def test_auto_graphics_match_the_three_mockup_systems(self):
        manifest = valid_visual_manifest()

        editorial = RENDERER.render_svg(manifest, Path.cwd(), "editorial")
        self.assertEqual(6, editorial.count('class="contour-path contour-path--top"'))
        self.assertEqual(6, editorial.count('class="contour-path contour-path--bottom"'))
        self.assertNotIn('class="page-spine"', editorial)

        statement = RENDERER.render_svg(manifest, Path.cwd(), "statement")
        self.assertEqual(8, statement.count('class="echo-ring"'))
        self.assertNotIn('class="registration-mark"', statement)

        contextual = RENDERER.render_svg(manifest, Path.cwd(), "contextual")
        self.assertEqual(20, contextual.count('class="field-dot field-dot--top"'))
        self.assertEqual(20, contextual.count('class="field-dot field-dot--bottom"'))
        self.assertIn('class="field-sheet"', contextual)
        self.assertNotIn('<g class="source-panel">', contextual)

    def test_editorial_and_contextual_source_fields_are_right_aligned(self):
        manifest = valid_visual_manifest()
        for direction, expected_x in (("editorial", 1440 * 0.91), ("contextual", 1440 * 0.88)):
            svg = RENDERER.render_svg(manifest, Path.cwd(), direction)
            root = ET.fromstring(svg)
            field = root.find(".//{http://www.w3.org/2000/svg}text[@class='meta attribution source-field']")
            self.assertIsNotNone(field)
            self.assertEqual("end", field.attrib.get("text-anchor"))
            self.assertAlmostEqual(expected_x, float(field.attrib["x"]))

    def test_statement_source_field_is_always_right_aligned(self):
        manifest = valid_visual_manifest()
        svg = RENDERER.render_svg(manifest, Path.cwd(), "statement")
        root = ET.fromstring(svg)
        field = root.find(".//{http://www.w3.org/2000/svg}text[@class='meta attribution source-field']")
        self.assertIsNotNone(field)
        self.assertEqual("end", field.attrib.get("text-anchor"))
        self.assertAlmostEqual(1440 * 0.945, float(field.attrib["x"]))
        self.assertNotIn('class="data source-note"', svg)

    def test_multiword_emphasis_can_cross_a_manual_line_break(self):
        manifest = valid_visual_manifest()
        manifest["content"]["emphasis"] = "commuove per il tuo"
        svg = RENDERER.render_svg(manifest, Path.cwd(), "statement")
        self.assertIn('>COMMUOVE</tspan>', svg)
        self.assertIn('>PER IL TUO</tspan>', svg)
        self.assertEqual(2, svg.count('font-weight="700" fill="#E3F4FF"'))

    def test_spacer_line_is_valid_and_keeps_a_full_vertical_row(self):
        manifest = valid_visual_manifest()
        manifest["content"]["text"] = "Una frase verificata."
        manifest["content"]["lines"] = [
            "Una frase",
            "",
            "verificata.",
        ]
        manifest["content"]["emphasis"] = "verificata."
        self.assertEqual([], RENDERER.validate_visual_manifest(manifest, Path.cwd()))
        svg = RENDERER.render_svg(manifest, Path.cwd(), "statement")
        quote = ET.fromstring(svg).find(".//{http://www.w3.org/2000/svg}text[@class='quote']")
        self.assertIsNotNone(quote)
        rows = list(quote)
        self.assertEqual(3, len(rows))
        self.assertEqual("", "".join(rows[1].itertext()))
        first_y, third_y = float(rows[0].attrib["y"]), float(rows[2].attrib["y"])
        self.assertGreater(third_y - first_y, 150)

    def test_statement_highlight_tracks_baseline_after_spacer(self):
        manifest = valid_visual_manifest()
        manifest["content"]["text"] = "Una frase verificata."
        manifest["content"]["lines"] = ["Una frase", "", "verificata."]
        manifest["content"]["emphasis"] = ""
        manifest["content"]["styles"] = [{"start": 11, "end": 15, "type": "highlight"}]
        root = ET.fromstring(RENDERER.render_svg(manifest, Path.cwd(), "statement"))
        marker = root.find(".//{http://www.w3.org/2000/svg}rect[@class='highlight-marker']")
        quote = root.find(".//{http://www.w3.org/2000/svg}text[@class='quote']")
        self.assertIsNotNone(marker)
        self.assertIsNotNone(quote)
        rows = list(quote)
        self.assertEqual(3, len(rows))
        final_row = rows[2]
        final_y = float(final_row.attrib["y"])
        final_size = float(final_row.attrib["font-size"])
        # Poster text is uppercased, and uppercase glyphs have a taller
        # cap-height relative to font-size than mixed-case text, so the
        # marker gets more headroom (1.02) than the mixed-case case (0.76).
        self.assertAlmostEqual(final_y - final_size * 1.02, float(marker.attrib["y"]), delta=0.1)
        self.assertGreater(float(marker.attrib["x"]), float(final_row.attrib["x"]))
        self.assertLess(float(marker.attrib["width"]), RENDERER.visual_units("verificata.") * final_size)

    def test_statement_highlight_keeps_text_white_on_accent_band(self):
        manifest = valid_visual_manifest()
        manifest["content"]["emphasis"] = ""
        manifest["content"]["styles"] = [{"start": 44, "end": 54, "type": "highlight"}]
        svg = RENDERER.render_svg(manifest, Path.cwd(), "statement")
        self.assertIn('fill="#FEFDFB" font-weight="700"><tspan', svg)
        self.assertNotIn('fill="#E3F4FF" font-weight="700"><tspan', svg)

    def test_inline_text_styles_are_rendered_together(self):
        manifest = valid_visual_manifest()
        manifest["content"]["emphasis"] = ""
        manifest["content"]["styles"] = [
            {"start": 0, "end": 9, "type": "bold"},
            {"start": 10, "end": 13, "type": "italic"},
            {"start": 14, "end": 16, "type": "underline"},
            {"start": 44, "end": 54, "type": "highlight"},
        ]
        self.assertEqual([], RENDERER.validate_visual_manifest(manifest, Path.cwd()))
        svg = RENDERER.render_svg(manifest, Path.cwd(), "statement")
        self.assertIn('font-weight="700"', svg)
        self.assertIn('font-style="italic"', svg)
        self.assertIn('text-decoration:underline', svg)
        self.assertIn('class="highlight-marker"', svg)
        self.assertIn('rx="', svg)
        self.assertNotIn('paint-order="stroke fill"', svg)

    def test_accent_style_colors_selected_glyphs(self):
        manifest = valid_visual_manifest()
        manifest["content"]["emphasis"] = ""
        manifest["content"]["styles"] = [{"start": 0, "end": 9, "type": "accent"}]
        self.assertEqual([], RENDERER.validate_visual_manifest(manifest, Path.cwd()))
        svg = RENDERER.render_svg(manifest, Path.cwd(), "statement")
        self.assertIn('<tspan fill="#E3F4FF">', svg)

    def test_embeds_a_supplied_italic_face(self):
        manifest = valid_visual_manifest()
        manifest["content"]["emphasis"] = ""
        manifest["content"]["styles"] = [{"start": 10, "end": 13, "type": "italic"}]
        with tempfile.TemporaryDirectory() as temp_dir:
            italic = Path(temp_dir) / "Test-Italic.ttf"
            italic.write_bytes(b"test-font")
            manifest["brand"]["font"]["italic_path"] = str(italic)
            self.assertEqual([], RENDERER.validate_visual_manifest(manifest, Path(temp_dir)))
            svg = RENDERER.render_svg(manifest, Path(temp_dir), "statement")
        self.assertIn("font-weight:400;font-style:italic", svg)
        self.assertIn('font-style="italic"', svg)

    def test_rejects_style_range_outside_current_text(self):
        manifest = valid_visual_manifest()
        manifest["content"]["styles"] = [{"start": 0, "end": 999, "type": "bold"}]
        codes = {error["code"] for error in RENDERER.validate_visual_manifest(manifest, Path.cwd())}
        self.assertIn("range", codes)

    def test_logo_has_explicit_geometry(self):
        manifest = valid_visual_manifest()
        with tempfile.TemporaryDirectory() as temp_dir:
            logo = Path(temp_dir) / "logo.svg"
            logo.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 100"><rect width="400" height="100"/></svg>',
                encoding="utf-8",
            )
            manifest["brand"]["logo"] = {
                "dark_path": str(logo),
                "light_path": str(logo),
            }
            svg = RENDERER.render_svg(manifest, Path(temp_dir), "statement")
        self.assertRegex(svg, r'<image [^>]*width="288\.0" [^>]*height="72\.0"')

    def test_render_options_hide_logo_and_quotes(self):
        manifest = valid_visual_manifest()
        with tempfile.TemporaryDirectory() as temp_dir:
            logo = Path(temp_dir) / "logo.svg"
            logo.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 100"><rect width="400" height="100"/></svg>',
                encoding="utf-8",
            )
            manifest["brand"]["logo"] = {"light_path": str(logo)}
            svg = RENDERER.render_svg(
                manifest,
                Path(temp_dir),
                "statement",
                render_options={"logo_mode": "hidden", "show_quotation_marks": False},
            )
        self.assertNotIn("<image", svg)
        self.assertNotIn('class="marks"', svg)

    def test_vertical_position_changes_quote_geometry(self):
        manifest = valid_visual_manifest()
        upper = RENDERER.render_svg(
            manifest, Path.cwd(), "statement", render_options={"vertical_position": "upper"}
        )
        lower = RENDERER.render_svg(
            manifest, Path.cwd(), "statement", render_options={"vertical_position": "lower"}
        )
        self.assertNotEqual(upper, lower)

    def test_cli_generates_three_proofs_and_contact_sheet(self):
        manifest = valid_visual_manifest()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            manifest_path = temp_path / "manifest.json"
            output_dir = temp_path / "output"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            exit_code = RENDERER.main(
                [
                    str(manifest_path),
                    "--output-dir",
                    str(output_dir),
                    "--all-directions",
                    "--png",
                    "never",
                ]
            )
            self.assertEqual(0, exit_code)
            for direction in RENDERER.DIRECTIONS:
                self.assertTrue((output_dir / f"test-quote-{direction}.svg").is_file())
            self.assertTrue((output_dir / "test-quote-directions.html").is_file())
            qa_report = json.loads((output_dir / "test-quote-qa.json").read_text(encoding="utf-8"))
            self.assertEqual("passed", qa_report["status"])
            self.assertTrue(qa_report["checks"]["text_unchanged"])


if __name__ == "__main__":
    unittest.main()
