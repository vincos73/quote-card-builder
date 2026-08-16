import importlib.util
import struct
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location("rasterize", ROOT / "scripts" / "rasterize.py")
RASTER = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(RASTER)


def png_bytes(width, height, pixel=(0x2B, 0x18, 0x30), stripe=None):
    """A real PNG: filter 0 rows, 8-bit RGB, no interlace.

    ``stripe`` paints a different colour on every eighth row so the image
    has genuine ink, which is what separates a rendered card from a
    converter that produced an empty canvas.
    """
    rows = []
    for y in range(height):
        colour = stripe if (stripe and y % 8 == 0) else pixel
        rows.append(b"\x00" + bytes(colour) * width)
    raw = b"".join(rows)

    def chunk(kind, body):
        payload = kind + body
        return struct.pack(">I", len(body)) + payload + struct.pack(">I", zlib.crc32(payload) & 0xFFFFFFFF)

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


class PngReaderTests(unittest.TestCase):
    """Pillow is not a dependency, so the reader used to check a
    converter's work is implemented here and has to be correct."""

    def test_dimensions_come_from_the_header(self):
        self.assertEqual((1440, 1800), RASTER.png_dimensions(png_bytes(1440, 1800)))

    def test_decode_returns_every_pixel(self):
        width, height, channels, pixels = RASTER.decode_png(png_bytes(4, 3))
        self.assertEqual((4, 3, 3), (width, height, channels))
        self.assertEqual(4 * 3 * 3, len(pixels))
        self.assertEqual(bytes((0x2B, 0x18, 0x30)), pixels[:3])

    def test_non_png_input_is_rejected(self):
        for payload in (b"", b"not a png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 4):
            with self.subTest(payload=payload[:12]):
                with self.assertRaises(ValueError):
                    RASTER.png_dimensions(payload)

    def test_ink_coverage_separates_a_drawing_from_an_empty_canvas(self):
        _, _, channels, flat = RASTER.decode_png(png_bytes(200, 200))
        self.assertEqual(0.0, RASTER.ink_coverage(200, 200, channels, flat))
        _, _, channels, drawn = RASTER.decode_png(png_bytes(200, 200, stripe=(0xB9, 0xD9, 0x36)))
        self.assertGreater(RASTER.ink_coverage(200, 200, channels, drawn), RASTER.MIN_INK_COVERAGE)


class VerifyPngTests(unittest.TestCase):
    """A converter that writes a blank or mis-sized file is worse than one
    that fails: the result looks deliverable."""

    def _write(self, directory, name, payload):
        path = Path(directory) / name
        path.write_bytes(payload)
        return path

    def test_a_real_card_is_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write(directory, "ok.png", png_bytes(1440, 1800, stripe=(0xB9, 0xD9, 0x36)))
            self.assertEqual([], RASTER.verify_png(path, 1440, 1800))

    def test_defective_output_is_rejected_with_a_reason(self):
        cases = {
            "blank.png": (png_bytes(1440, 1800), "vuota"),
            "small.png": (png_bytes(800, 1000, stripe=(0xB9, 0xD9, 0x36)), "dimensioni"),
            "corrupt.png": (b"not a png at all", "non è un PNG valido"),
            "empty.png": (b"", "PNG vuoto"),
        }
        with tempfile.TemporaryDirectory() as directory:
            for name, (payload, expected) in cases.items():
                with self.subTest(case=name):
                    path = self._write(directory, name, payload)
                    problems = RASTER.verify_png(path, 1440, 1800)
                    self.assertTrue(problems, f"{name} should have been rejected")
                    self.assertTrue(
                        any(expected in problem for problem in problems),
                        f"{name}: {problems}",
                    )

    def test_a_missing_file_is_reported_rather_than_raising(self):
        self.assertTrue(RASTER.verify_png(Path("/nonexistent/none.png"), 1440, 1800))


class BackendChainTests(unittest.TestCase):
    """Backends are stubbed: the chain's logic is what is under test, not
    whichever converters happen to be installed on this machine."""

    def _backend(self, name, *, ok=True, payload=None, error=None):
        def run(_svg, png, width, height, _options):
            if error is not None:
                raise error
            png.write_bytes(payload if payload is not None else png_bytes(width, height, stripe=(1, 2, 3)))
        run.__name__ = name
        return (name, run if ok else run)

    def test_the_first_working_backend_wins(self):
        with tempfile.TemporaryDirectory() as directory:
            svg, png = Path(directory) / "a.svg", Path(directory) / "a.png"
            svg.write_text("<svg/>", encoding="utf-8")
            chain = (self._backend("first"), self._backend("second"))
            with mock.patch.object(RASTER, "BACKENDS", chain):
                self.assertEqual("first", RASTER.rasterize(svg, png, 64, 64))

    def test_an_unavailable_backend_is_skipped(self):
        with tempfile.TemporaryDirectory() as directory:
            svg, png = Path(directory) / "a.svg", Path(directory) / "a.png"
            svg.write_text("<svg/>", encoding="utf-8")
            chain = (
                self._backend("missing", error=FileNotFoundError("assente")),
                self._backend("working"),
            )
            with mock.patch.object(RASTER, "BACKENDS", chain):
                self.assertEqual("working", RASTER.rasterize(svg, png, 64, 64))

    def test_a_backend_that_writes_a_bad_png_does_not_count_as_success(self):
        # The core reason verification lives inside the chain: a converter
        # can exit 0 and still leave an empty canvas behind.
        with tempfile.TemporaryDirectory() as directory:
            svg, png = Path(directory) / "a.svg", Path(directory) / "a.png"
            svg.write_text("<svg/>", encoding="utf-8")
            chain = (
                self._backend("blank", payload=png_bytes(64, 64)),
                self._backend("real"),
            )
            with mock.patch.object(RASTER, "BACKENDS", chain):
                self.assertEqual("real", RASTER.rasterize(svg, png, 64, 64))
            self.assertEqual([], RASTER.verify_png(png, 64, 64))

    def test_total_failure_reports_every_attempt(self):
        with tempfile.TemporaryDirectory() as directory:
            svg, png = Path(directory) / "a.svg", Path(directory) / "a.png"
            svg.write_text("<svg/>", encoding="utf-8")
            chain = (
                self._backend("alpha", error=FileNotFoundError("non installato")),
                self._backend("beta", error=OSError("esploso")),
            )
            with mock.patch.object(RASTER, "BACKENDS", chain):
                with self.assertRaises(RASTER.RasterError) as caught:
                    RASTER.rasterize(svg, png, 64, 64)
            message = str(caught.exception)
            # The old code swallowed the converter's error entirely; every
            # reason has to survive to the caller now.
            self.assertIn("alpha", message)
            self.assertIn("non installato", message)
            self.assertIn("beta", message)
            self.assertIn("esploso", message)
            self.assertEqual(["alpha", "beta"], [name for name, _ in caught.exception.attempts])

    def test_sharp_stays_the_preferred_backend(self):
        # Backend choice is a compatibility decision: sharp produced every
        # PNG shipped so far and other rasterisers differ measurably.
        self.assertEqual("sharp", RASTER.PRIMARY_BACKEND)
        self.assertEqual("sharp", RASTER.BACKENDS[0][0])

    def test_available_backends_needs_both_node_and_modules_for_sharp(self):
        with tempfile.TemporaryDirectory() as directory:
            node = Path(directory) / "node"
            node.write_text("#!/bin/sh\n", encoding="utf-8")
            modules = Path(directory) / "node_modules"
            modules.mkdir()
            self.assertIn("sharp", RASTER.available_backends(node=node, node_modules=modules))
            self.assertNotIn("sharp", RASTER.available_backends(node=node))
            self.assertNotIn("sharp", RASTER.available_backends())


class RealBackendTests(unittest.TestCase):
    """One end-to-end conversion when a converter really exists, so the
    stubs above cannot all agree on a wrong contract."""

    def test_an_installed_backend_converts_a_real_card_svg(self):
        available = RASTER.available_backends()
        if not available:
            self.skipTest("nessun convertitore installato su questa macchina")
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="240" height="300" '
            'viewBox="0 0 240 300">'
            '<rect width="240" height="300" fill="#2B1830"/>'
            '<rect x="20" y="40" width="200" height="120" fill="#B9D936"/>'
            '</svg>'
        )
        with tempfile.TemporaryDirectory() as directory:
            svg_path = Path(directory) / "card.svg"
            png_path = Path(directory) / "card.png"
            svg_path.write_text(svg, encoding="utf-8")
            backend = RASTER.rasterize(svg_path, png_path, 240, 300)
            self.assertIn(backend, available)
            self.assertEqual([], RASTER.verify_png(png_path, 240, 300))
            self.assertEqual((240, 300), RASTER.png_dimensions(png_path.read_bytes()))


if __name__ == "__main__":
    unittest.main()
