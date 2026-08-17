import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


INSPECT = load_module("inspect_render", ROOT / "scripts" / "inspect_render.py")
RENDERER = INSPECT.proof
PACK = load_module("render_quote_card_pack", ROOT / "scripts" / "render_quote_card_pack.py")
SERVER = load_module("card_review_server", ROOT / "scripts" / "card_review_server.py")


def visual_manifest(text, lines, emphasis="", width=1440, height=1800):
    return {
        "schema_version": "0.2",
        "state": "contenuto_approvato",
        "content": {
            "text": text,
            "lines": lines,
            "transformation": "VERBATIM",
            "evidence_status": "VERIFIED",
            "emphasis": emphasis,
            "styles": [],
            "attribution": {"label": "example.test", "role": "publisher"},
        },
        "canvas": {"width": width, "height": height},
        "brand": {
            "name": "Test Brand",
            "colors": {
                "primary": "#072743", "accent": "#E3F4FF",
                "background": "#FEFDFB", "text": "#323232",
            },
            "font": {"family": "Test Sans"},
        },
        "source": {"title": "Test source", "locator": "test://source"},
    }


def synthetic_card(*, mark_d, mark_stroke, quote="Testo di prova"):
    """A minimal card with one quote row and one corner mark.

    Hand-built rather than rendered, so a detector can be exercised on a
    defect the current renderer cannot actually produce -- the point is to
    prove the detector fires, not to prove today's renderer is broken.
    """
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="1800" '
        'viewBox="0 0 1440 1800">'
        '<rect width="1440" height="1800" fill="#FEFDFB"/>'
        f'<path class="quote-corner-mark quote-corner-mark--top" d="{mark_d}" '
        f'fill="none" stroke="{mark_stroke}" stroke-width="5.0"/>'
        '<text class="quote" x="108.0" y="400.0" font-size="80.0" fill="#072743" '
        'style="letter-spacing:-0.025em">'
        f'<tspan x="108.0" y="400.0">{quote}</tspan></text>'
        '<text class="meta attribution source-field" x="1310.4" y="1647.0" '
        'text-anchor="end" font-size="40.3" fill="#323232">example.test</text>'
        '</svg>'
    )


MATRIX = [
    (direction, width, height, position)
    for direction in RENDERER.DIRECTIONS
    for width, height in ((1440, 1800), (1440, 1440), (1080, 1920))
    for position in ("upper", "center", "lower")
]

CONTENT = [
    ("il tuo brand esiste nello spazio latente di un LLM",
     ["il tuo brand esiste", "nello spazio latente", "di un LLM"], ""),
    ("Un agente non si commuove per il tuo claim: confronta.",
     ["Un agente non si commuove", "per il tuo claim:", "confronta."], "confronta."),
    ("Una frase con riga vuota.", ["Una frase", "", "con riga vuota."], ""),
    # One short word fitted to the whole card: the case that leaves a
    # corner module no room, and that shipped with the mark drawn on top
    # of the text until the module learned to size itself.
    ("Breve.", ["Breve."], ""),
]


class CleanRenderTests(unittest.TestCase):
    """A defect reported on a good card is worse than no check at all.

    If this suite ever goes noisy the gate stops being trusted, so the
    whole shipping matrix has to come back clean.
    """

    def test_every_shipping_combination_inspects_clean(self):
        for direction, width, height, position in MATRIX:
            for text, lines, emphasis in CONTENT:
                with self.subTest(direction=direction, canvas=(width, height),
                                  position=position, text=text[:24]):
                    manifest = visual_manifest(text, lines, emphasis, width, height)
                    size, _, _, _, _ = PACK.resolve_font_size(
                        lines, manifest, Path.cwd(), direction, width, height, 1.0, position,
                    )
                    svg = RENDERER.render_svg(
                        manifest, Path.cwd(), direction, font_size_override=size,
                        render_options={"vertical_position": position},
                    )
                    findings = INSPECT.inspect_render(
                        svg, direction, width, height, vertical_position=position,
                    )
                    self.assertEqual(
                        [], findings,
                        "\n".join(f"{f['code']}: {f['message']}" for f in findings),
                    )


class DefectDetectionTests(unittest.TestCase):
    """Each detector is exercised against the defect class it exists for."""

    def test_oversized_text_is_reported_as_leaving_the_safe_area(self):
        # Overriding the fitted size is the cheapest faithful stand-in for
        # the real bug: a fitter that under-measures a row hands the
        # renderer a size too large for the guide, exactly as happened when
        # Poster measured an emphasised row at 1.0x and drew it at 1.12x.
        text, lines = "il tuo brand esiste nello spazio latente", ["il tuo brand esiste", "nello spazio latente"]
        for direction in RENDERER.DIRECTIONS:
            with self.subTest(direction=direction):
                manifest = visual_manifest(text, lines)
                fitted, _, _, _, _ = PACK.resolve_font_size(
                    lines, manifest, Path.cwd(), direction, 1440, 1800, 1.0, "center",
                )
                svg = RENDERER.render_svg(
                    manifest, Path.cwd(), direction, font_size_override=fitted * 1.35,
                )
                codes = {f["code"] for f in INSPECT.inspect_render(svg, direction, 1440, 1800)}
                self.assertIn("text_outside_safe_area", codes)

    def test_a_mark_sitting_on_the_words_is_reported(self):
        # The corner mark's arms land inside the first row's box.
        svg = synthetic_card(mark_d="M 200 420 V 380 H 240", mark_stroke="#072743")
        codes = {f["code"] for f in INSPECT.inspect_render(svg, "editorial", 1440, 1800)}
        self.assertIn("decoration_overlaps_text", codes)

    def test_a_mark_clear_of_the_words_is_not_reported(self):
        svg = synthetic_card(mark_d="M 60 200 V 160 H 100", mark_stroke="#072743")
        codes = {f["code"] for f in INSPECT.inspect_render(svg, "editorial", 1440, 1800)}
        self.assertNotIn("decoration_overlaps_text", codes)

    def test_an_unreadable_mark_is_reported(self):
        # Accent on the light page: the pairing the manifest validator
        # never checked, which shipped decorative strokes at ~1.1:1.
        svg = synthetic_card(mark_d="M 60 200 V 160 H 100", mark_stroke="#E3F4FF")
        findings = INSPECT.inspect_render(svg, "editorial", 1440, 1800)
        self.assertIn("decoration_contrast", {f["code"] for f in findings})
        self.assertTrue(any("1." in f["message"] for f in findings))

    def test_a_readable_mark_is_not_reported(self):
        svg = synthetic_card(mark_d="M 60 200 V 160 H 100", mark_stroke="#072743")
        codes = {f["code"] for f in INSPECT.inspect_render(svg, "editorial", 1440, 1800)}
        self.assertNotIn("decoration_contrast", codes)

    def _outlined_card(self, stroke, font_size=80.0):
        """One quote row whose closing word is hollow rather than filled."""
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="1800">'
            '<rect width="1440" height="1800" fill="#FFFFFF"/>'
            f'<text class="quote" x="108.0" y="400.0" font-size="{font_size}" fill="#072743">'
            f'<tspan x="108.0" y="400.0">Testo di <tspan fill="none" stroke="{stroke}" '
            f'stroke-width="2.8">prova</tspan></tspan></text></svg>'
        )

    def test_an_outlined_span_is_graded_on_its_stroke_not_its_missing_fill(self):
        """fill="none" is not a colour. Reading only fill left the one
        treatment with the least ink on the page unchecked entirely."""
        findings = INSPECT.inspect_render(self._outlined_card("#767676"), "editorial", 1440, 1800)
        self.assertIn("outline_contrast", {f["code"] for f in findings})

    def test_an_outline_is_held_above_the_floor_a_filled_glyph_passes(self):
        """#767676 on white clears the 4.5:1 text floor, so the same colour
        filled draws no finding -- hollow, it must still be refused."""
        self.assertGreater(RENDERER.contrast_ratio("#767676", "#FFFFFF"), INSPECT.TEXT_CONTRAST)
        filled = self._outlined_card("#767676").replace('fill="none" stroke=', 'fill=')
        self.assertEqual([], INSPECT.inspect_render(filled, "editorial", 1440, 1800))

    def test_a_dark_outline_on_the_page_passes(self):
        findings = INSPECT.inspect_render(self._outlined_card("#072743"), "editorial", 1440, 1800)
        self.assertEqual([], findings)

    def test_an_outline_too_small_to_stay_open_is_reported(self):
        """Below roughly 4.5% of the card's width a hairline closes the
        counters up, whatever the contrast ratio says."""
        small = self._outlined_card("#072743", font_size=40.0)
        codes = {f["code"] for f in INSPECT.inspect_render(small, "editorial", 1440, 1800)}
        self.assertIn("outline_too_small", codes)
        self.assertNotIn("outline_contrast", codes)

    def test_malformed_svg_is_reported_rather_than_raising(self):
        findings = INSPECT.inspect_render("<svg><unclosed>", "editorial", 1440, 1800)
        self.assertEqual(["svg_invalid"], [f["code"] for f in findings])


class MeasurementTests(unittest.TestCase):
    def test_text_width_accounts_for_tracking(self):
        wide = INSPECT.text_width("ABCDEF", 100.0, 0.0)
        tight = INSPECT.text_width("ABCDEF", 100.0, -0.025)
        self.assertLess(tight, wide)
        self.assertAlmostEqual(wide - tight, 0.025 * 100.0 * 5, places=6)

    def test_end_anchored_text_is_measured_leftwards(self):
        svg = synthetic_card(mark_d="M 60 200 V 160 H 100", mark_stroke="#072743")
        import xml.etree.ElementTree as ET

        boxes = INSPECT.text_boxes(ET.fromstring(svg))
        attribution = next(b for b in boxes if "attribution" in b["classes"])
        self.assertLess(attribution["box"][0], 1310.4)
        self.assertAlmostEqual(1310.4, attribution["box"][2], delta=0.5)

    def test_ground_resolution_prefers_the_last_painted_rect(self):
        grounds = [((0, 0, 100, 100), "#FFFFFF"), ((0, 0, 100, 100), "#000000")]
        self.assertEqual("#000000", INSPECT.ground_for((10, 10, 20, 20), grounds))
        self.assertEqual("", INSPECT.ground_for((500, 500, 510, 510), grounds))

    def test_nested_tspan_fill_override_is_measured_as_its_own_box(self):
        """A highlighted span switches its own fill so it reads against its
        marker band; the checker has to see that override, not the row's
        base fill, or it grades the wrong color against the wrong ground."""
        import xml.etree.ElementTree as ET

        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="1800">'
            '<text class="quote" x="0" y="100" font-size="80" fill="#FEFDFB">'
            '<tspan x="0" y="100" fill="#FEFDFB">BE <tspan fill="#072743">FREE</tspan></tspan>'
            '</text></svg>'
        )
        boxes = INSPECT.text_boxes(ET.fromstring(svg))
        fills = {box["text"]: box["fill"] for box in boxes}
        self.assertEqual("#FEFDFB", fills["BE "])
        self.assertEqual("#072743", fills["FREE"])

    def test_splitting_a_row_for_fill_preserves_total_tracking_width(self):
        """Tracking is a per-gap cost, not a per-character one. Measuring a
        row's segments separately (for their different fills) must still
        add up to what measuring the whole row in one piece would give, or
        a fill override quietly shifts every following box out of place."""
        import xml.etree.ElementTree as ET

        whole = INSPECT.text_width("BE FREE", 80.0, -0.025)
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="1800">'
            '<text class="quote" x="0" y="100" font-size="80" fill="#FEFDFB" '
            'style="letter-spacing:-0.025em">'
            '<tspan x="0" y="100" fill="#FEFDFB">BE <tspan fill="#072743">FREE</tspan></tspan>'
            '</text></svg>'
        )
        boxes = INSPECT.text_boxes(ET.fromstring(svg))
        split_total = max(b["box"][2] for b in boxes) - min(b["box"][0] for b in boxes)
        self.assertAlmostEqual(whole, split_total, places=6)


class QualityGateTests(unittest.TestCase):
    """The gate must actually refuse a defective render, not just log it."""

    def _manifest(self):
        return {
            "schema_version": "0.4", "state": "contenuto_approvato", "revision": 1,
            "content": {
                "text": "Una frase verificata.", "transformation": "VERBATIM",
                "evidence_status": "VERIFIED", "emphasis": "verificata",
                "attribution": {"label": "example.test", "role": "publisher"},
            },
            "direction": "statement",
            "presentation": {"logo_mode": "auto", "graphic_mode": "auto"},
            "formats": [{"id": "4x5", "width": 1440, "height": 1800,
                         "lines": ["Una frase verificata."], "text_scale": 1.0,
                         "vertical_position": "center"}],
            "brand": {"name": "Test", "colors": {
                "primary": "#072743", "accent": "#E3F4FF",
                "background": "#FEFDFB", "text": "#323232"},
                "font": {"family": "Test Sans"}},
            "source": {"title": "Source", "locator": "test://source"},
            "output": {"basename": "quote"},
        }

    def test_render_inspection_is_part_of_the_gate(self):
        manifest = self._manifest()
        previews = SERVER.render_preview(manifest, Path.cwd())
        qa = SERVER.preview_quality(manifest, previews, Path.cwd())
        self.assertIn("render", qa["checks"])
        self.assertTrue(qa["passed"], qa["warnings"])

    def test_gate_passes_a_poster_highlight_over_an_already_accented_row(self):
        """End to end: Poster's own quote text is background-colored to read
        on its dark surface, so a highlighted span switches to the primary
        color to read against its accent band instead. The live gate has to
        recognize that switched color, not the row's base one, or a
        perfectly readable highlight gets reported as failing contrast."""
        manifest = self._manifest()
        manifest["content"]["emphasis"] = ""
        manifest["content"]["styles"] = [{"start": 0, "end": 21, "type": "highlight"}]
        previews = SERVER.render_preview(manifest, Path.cwd())
        qa = SERVER.preview_quality(manifest, previews, Path.cwd())
        self.assertTrue(qa["passed"], qa["warnings"])

    def test_gate_fails_when_the_rendered_card_is_defective(self):
        manifest = self._manifest()
        previews = SERVER.render_preview(manifest, Path.cwd())
        previews[0]["svg"] = synthetic_card(
            mark_d="M 200 420 V 380 H 240", mark_stroke="#E3F4FF",
        )
        qa = SERVER.preview_quality(manifest, previews, Path.cwd())
        codes = {warning["code"] for warning in qa["warnings"]}
        self.assertFalse(qa["passed"])
        self.assertIn("decoration_overlaps_text", codes)
        self.assertIn("decoration_contrast", codes)


if __name__ == "__main__":
    unittest.main()
