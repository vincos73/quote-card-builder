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

        self.assertIn('direction-graphic--contours', editorial)
        self.assertNotIn('PAGINA / 01', editorial)
        self.assertNotIn('class="source-bar"', editorial)
        self.assertIn('direction-graphic--echo', statement)
        self.assertNotIn('MANIFESTO / 02', statement)
        self.assertNotIn('class="source-bar"', statement)
        # With no quotation marks anywhere, the directions are told apart by
        # composition alone -- their graphic and, for Campo, its rule.
        self.assertIn('class="quote-index"', contextual)
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

    def test_no_direction_draws_a_quotation_mark_of_any_kind(self):
        # Neither the glyph pair nor the corner brackets that once stood in
        # for it. The setting that used to govern them is gone from the
        # model too, so there is nothing left to turn them back on.
        manifest = valid_visual_manifest()
        for direction in RENDERER.DIRECTIONS:
            with self.subTest(direction=direction):
                svg = RENDERER.render_svg(manifest, Path.cwd(), direction)
                self.assertNotIn("“", svg)
                self.assertNotIn("”", svg)
                self.assertNotIn("quote-corner-mark", svg)
                self.assertNotIn('class="marks"', svg)

    def test_campos_vertical_rule_survives_as_composition(self):
        # SKILL.md gives Campo "una sola regola verticale" as the direction's
        # signature. It was briefly wired to the quotation setting; it is
        # layout, not a mark standing in for one, so removing quotation
        # marks must not have taken it with them.
        svg = RENDERER.render_svg(valid_visual_manifest(), Path.cwd(), "contextual")
        self.assertIn('class="quote-index"', svg)

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
        # marker gets a bit more headroom (0.82) than the mixed-case case
        # (0.76) -- just enough to clear Arial Bold's ~0.72em cap-height.
        self.assertAlmostEqual(final_y - final_size * 0.82, float(marker.attrib["y"]), delta=0.1)
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
        manifest["direction"] = "editorial"
        manifest["content"]["emphasis"] = ""
        manifest["content"]["styles"] = [
            {"start": 0, "end": 9, "type": "bold"},
            {"start": 10, "end": 13, "type": "italic"},
            {"start": 14, "end": 16, "type": "underline"},
            {"start": 44, "end": 54, "type": "highlight"},
        ]
        self.assertEqual([], RENDERER.validate_visual_manifest(manifest, Path.cwd()))
        svg = RENDERER.render_svg(manifest, Path.cwd(), "editorial")
        self.assertIn('font-weight="700"', svg)
        self.assertIn('font-style="italic"', svg)
        self.assertIn('text-decoration:underline', svg)
        self.assertIn('class="highlight-marker"', svg)
        self.assertIn('rx="', svg)
        self.assertNotIn('paint-order="stroke fill"', svg)

    def test_statement_accepts_highlight_style(self):
        manifest = valid_visual_manifest()
        manifest["content"]["emphasis"] = ""
        manifest["content"]["styles"] = [{"start": 0, "end": 9, "type": "highlight"}]
        self.assertEqual([], RENDERER.validate_visual_manifest(manifest, Path.cwd()))
        svg = RENDERER.render_svg(manifest, Path.cwd(), "statement")
        self.assertIn('class="highlight-marker"', svg)

    def test_statement_highlight_band_is_measured_against_bold_glyphs(self):
        """Poster renders its entire quote block bold; the marker band behind
        a highlighted span must be sized against bold glyph widths, not the
        narrower regular-weight ones, or it trails short of the text."""
        narrow = RENDERER.visual_units("Un agente", bold=False)
        wide = RENDERER.visual_units("Un agente", bold=True)
        self.assertGreater(wide, narrow)

    def test_statement_highlighted_text_reads_against_the_accent_band(self):
        """Poster's plain quote text is background-colored (light) to read
        against the dark primary surface. A highlight band is painted in
        the accent color, so text sitting on it needs to switch to a color
        that reads against *that* surface instead, or it goes near-invisible
        (light text on a light-ish accent band)."""
        manifest = valid_visual_manifest()
        manifest["content"]["emphasis"] = ""
        manifest["content"]["styles"] = [{"start": 44, "end": 54, "type": "highlight"}]
        svg = RENDERER.render_svg(manifest, Path.cwd(), "statement")
        self.assertIn('fill="#072743"', svg)

    def test_statement_highlight_over_an_accented_row_emits_one_fill(self):
        """A row can already be legacy-accented (Poster's initial signature)
        when the user also highlights it; the two styles must not both try
        to set ``fill`` on the same tspan, or the SVG comes out malformed."""
        manifest = valid_visual_manifest()
        manifest["content"]["emphasis"] = ""
        manifest["content"]["styles"] = [
            {"start": 44, "end": 54, "type": "accent"},
            {"start": 44, "end": 54, "type": "highlight"},
        ]
        svg = RENDERER.render_svg(manifest, Path.cwd(), "statement")
        ET.fromstring(svg)  # raises if a duplicate attribute made it invalid
        self.assertNotIn('fill="#E3F4FF" fill=', svg)

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
                render_options={"logo_mode": "hidden"},
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


PACK_PATH = Path(__file__).parents[1] / "scripts" / "render_quote_card_pack.py"
PACK_SPEC = importlib.util.spec_from_file_location("render_quote_card_pack", PACK_PATH)
PACK = importlib.util.module_from_spec(PACK_SPEC)
assert PACK_SPEC and PACK_SPEC.loader
PACK_SPEC.loader.exec_module(PACK)

SVG_NS = "{http://www.w3.org/2000/svg}"
GEOMETRY_CASES = [
    (direction, width, height, position)
    for direction in RENDERER.DIRECTIONS
    for width, height in ((1440, 1800), (1440, 1440), (1080, 1920))
    for position in ("upper", "center", "lower")
]

# Poster measures row width with max(), so an emphasised row only affects
# the fit when it is also the *widest* row. A fixture whose emphasis lands
# on a short row cannot expose a strong-row scaling bug at all -- the
# default manifest is exactly that shape, which is why the second case
# below (the quote that actually shipped broken) has to be here.
OVERFLOW_CASES = [
    (
        "emphasis on the widest row, via the auto-signature path",
        "il tuo brand esiste nello spazio latente di un LLM",
        ["il tuo brand esiste", "nello spazio latente", "di un LLM"],
        "",
    ),
    (
        "explicit emphasis on the widest row",
        "Non conta il claim ma la distribuzione dentro il modello",
        ["Non conta il claim", "ma la distribuzione", "dentro il modello"],
        "ma la distribuzione dentro il modello",
    ),
]


class LayoutGeometryTests(unittest.TestCase):
    """The renderer and the fitting/QA pass must agree on where text goes.

    Both modules used to keep private copies of every margin, baseline and
    line ratio, synchronised by hand. Three shipped bugs came from those
    copies disagreeing: a stale font-size ceiling, two different safe-area
    margins, and a fitting pass that measured a Poster row at 1.0x which
    then rendered at 1.12x and ran past the guide. These tests fail if the
    two ever diverge again.
    """

    def _quote_element(self, svg):
        root = ET.fromstring(svg)
        quote = root.find(f".//{SVG_NS}text[@class='quote']")
        self.assertIsNotNone(quote, "every direction must emit a .quote text element")
        return quote

    def test_rendered_text_origin_matches_the_shared_geometry_table(self):
        for direction, width, height, position in GEOMETRY_CASES:
            with self.subTest(direction=direction, canvas=(width, height), position=position):
                manifest = valid_visual_manifest()
                manifest["canvas"] = {"width": width, "height": height}
                geometry = RENDERER.direction_geometry(direction, width, height, position)
                quote = self._quote_element(RENDERER.render_svg(
                    manifest, Path.cwd(), direction,
                    render_options={"vertical_position": position},
                ))
                self.assertAlmostEqual(geometry["text_x"], float(quote.attrib["x"]), delta=0.1)
                self.assertAlmostEqual(geometry["start_y"], float(quote.attrib["y"]), delta=0.1)

    def test_rendered_rows_never_exceed_the_direction_safe_width(self):
        """Measure what was actually drawn, not what the fitter believed.

        Reading each row's own font-size back out of the SVG is what makes
        this independent of the fitter: a row that renders larger than it
        was measured at (the Poster overflow bug) shows up here even when
        the fitter's own bookkeeping says everything fits.
        """
        cases = [
            (direction, width, height, position, label, text, lines, emphasis)
            for direction, width, height, position in GEOMETRY_CASES
            for label, text, lines, emphasis in OVERFLOW_CASES
        ]
        for direction, width, height, position, label, text, lines, emphasis in cases:
            with self.subTest(direction=direction, canvas=(width, height),
                              position=position, case=label):
                manifest = valid_visual_manifest()
                manifest["canvas"] = {"width": width, "height": height}
                manifest["content"].update(
                    {"text": text, "lines": lines, "emphasis": emphasis, "styles": []}
                )
                size, _, _, _, _ = PACK.resolve_font_size(
                    lines, manifest, Path.cwd(), direction, width, height, 1.0, position,
                )
                geometry = RENDERER.direction_geometry(direction, width, height, position)
                quote = self._quote_element(RENDERER.render_svg(
                    manifest, Path.cwd(), direction, font_size_override=size,
                    render_options={"vertical_position": position},
                ))
                default_size = float(quote.attrib.get("font-size", size))
                for row in quote.findall(f"{SVG_NS}tspan"):
                    text = "".join(row.itertext())
                    if not text.strip():
                        continue
                    row_size = float(row.attrib.get("font-size", default_size))
                    drawn = (
                        RENDERER.visual_units(text) * row_size
                        + geometry["tracking_em"] * row_size * max(0, len(text) - 1)
                    )
                    self.assertLessEqual(
                        drawn, geometry["text_width"] + 0.5,
                        f"{text!r} renders {drawn:.1f}px wide in a "
                        f"{geometry['text_width']:.1f}px safe area",
                    )

    def test_fitting_and_rendering_share_one_geometry_source(self):
        """Guard the wiring itself, not just today's numbers.

        Perturbing the shared table must move both the fitted size and the
        rendered baseline. If either module reintroduced a private copy,
        one of them would ignore the change and this test would fail.
        """
        # PACK imports render_quote_card through sys.path, so it holds its
        # own module instance rather than this file's importlib-loaded
        # RENDERER. Drive both sides through PACK.proof so the assertion is
        # about one shared table, not about two copies that happen to match.
        renderer = PACK.proof
        direction, width, height = "statement", 1440, 1800
        manifest = valid_visual_manifest()
        manifest["canvas"] = {"width": width, "height": height}
        lines = manifest["content"]["lines"]
        baseline_size, _, _, _, _ = PACK.resolve_font_size(
            lines, manifest, Path.cwd(), direction, width, height, 1.0, "center",
        )
        original = dict(renderer.DIRECTION_GEOMETRY[direction])
        try:
            renderer.DIRECTION_GEOMETRY[direction] = {**original, "inset": original["inset"] * 2}
            narrowed_size, _, _, _, _ = PACK.resolve_font_size(
                lines, manifest, Path.cwd(), direction, width, height, 1.0, "center",
            )
            quote = self._quote_element(renderer.render_svg(
                manifest, Path.cwd(), direction, font_size_override=narrowed_size,
            ))
            self.assertLess(narrowed_size, baseline_size, "a tighter inset must shrink the fitted size")
            self.assertAlmostEqual(width * original["inset"] * 2, float(quote.attrib["x"]), delta=0.1)
        finally:
            renderer.DIRECTION_GEOMETRY[direction] = original


if __name__ == "__main__":
    unittest.main()
