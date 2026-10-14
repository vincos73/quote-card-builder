#!/usr/bin/env python3
"""Turn a rendered card SVG into a PNG, then check what came back.

Two facts drive this module.

First, PNG delivery used to depend on exactly one converter -- Node plus
sharp, at paths the caller had to supply -- and when it failed the error
was discarded, so "no PNG" arrived with no explanation. Several converters
are usually present on a machine; trying them in order costs nothing and
installs nothing.

Second, and less obvious: **rasterisers are not interchangeable**. On the
same card SVG, sharp (librsvg) and headless Chrome (Blink) disagree on
how to apply an em-based ``letter-spacing``; Chrome drew the widest row
~3% wider, landing it 0.3px from the safe-area edge that sharp cleared by
39px. So the order here is deliberate rather than opportunistic: the
backend that has always produced the shipped output is tried first, the
one actually used is reported so an artifact stays traceable, and
whatever comes back is measured before it is accepted.

The editable ribbon grammar has a browser-approved proof and embeds brand
fonts. For this grammar Chromium is the required baseline: librsvg ignores
those fonts and collapses spaces at independently styled text boundaries.
Ribbons therefore wait for fonts and images in Playwright and fail visibly
when this matching renderer is unavailable; legacy fallback order stays intact.
"""

from __future__ import annotations

import os
import re
import shutil
import struct
import subprocess
import sys
import zlib
from pathlib import Path
from typing import Any, Callable

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

CONVERSION_TIMEOUT_SECONDS = 120
# A rasteriser that silently produced a blank canvas is a worse outcome
# than one that failed: the file looks deliverable. Require that a real
# card covers at least this share of pixels with something other than its
# most common colour.
MIN_INK_COVERAGE = 0.005

CHROME_CANDIDATES = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
)


class RasterError(RuntimeError):
    """No backend produced an acceptable PNG; carries every attempt."""

    def __init__(self, attempts: list[tuple[str, str]]) -> None:
        self.attempts = attempts
        detail = "; ".join(f"{name}: {reason}" for name, reason in attempts) or "nessun backend disponibile"
        super().__init__(f"Conversione PNG non riuscita ({detail})")


# --------------------------------------------------------------------------
# Minimal PNG reader
#
# Pillow is not a dependency of this project and this module must not add
# one, so the few bytes needed to check a converter's work are decoded
# here: 8-bit non-interlaced greyscale/RGB/RGBA, which is what every
# backend below emits.
# --------------------------------------------------------------------------

_CHANNELS = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}


def png_dimensions(data: bytes) -> tuple[int, int]:
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Il file non è un PNG valido")
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    return a if pa <= pb and pa <= pc else (b if pb <= pc else c)


def decode_png(data: bytes) -> tuple[int, int, int, bytes]:
    """Return ``(width, height, channels, pixels)`` for a simple PNG."""
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Il file non è un PNG valido")
    width = height = depth = colour = 0
    idat = bytearray()
    offset = 8
    while offset + 8 <= len(data):
        (length,) = struct.unpack(">I", data[offset:offset + 4])
        kind = data[offset + 4:offset + 8]
        body = data[offset + 8:offset + 8 + length]
        offset += 12 + length
        if kind == b"IHDR":
            width, height, depth, colour, _, _, interlace = struct.unpack(">IIBBBBB", body[:13])
            if depth != 8 or interlace != 0 or colour not in _CHANNELS:
                raise ValueError("Formato PNG non supportato dal lettore interno")
        elif kind == b"IDAT":
            idat += body
        elif kind == b"IEND":
            break
    if not width or not height:
        raise ValueError("PNG privo di intestazione IHDR")
    channels = _CHANNELS[colour]
    raw = zlib.decompress(bytes(idat))
    stride = width * channels
    out = bytearray(height * stride)
    previous = bytearray(stride)
    position = 0
    for row in range(height):
        filter_type = raw[position]
        position += 1
        line = bytearray(raw[position:position + stride])
        position += stride
        if filter_type == 1:
            for i in range(channels, stride):
                line[i] = (line[i] + line[i - channels]) & 0xFF
        elif filter_type == 2:
            for i in range(stride):
                line[i] = (line[i] + previous[i]) & 0xFF
        elif filter_type == 3:
            for i in range(stride):
                left = line[i - channels] if i >= channels else 0
                line[i] = (line[i] + ((left + previous[i]) >> 1)) & 0xFF
        elif filter_type == 4:
            for i in range(stride):
                left = line[i - channels] if i >= channels else 0
                upper_left = previous[i - channels] if i >= channels else 0
                line[i] = (line[i] + _paeth(left, previous[i], upper_left)) & 0xFF
        elif filter_type != 0:
            raise ValueError(f"Filtro PNG {filter_type} non supportato")
        out[row * stride:(row + 1) * stride] = line
        previous = line
    return width, height, channels, bytes(out)


def ink_coverage(width: int, height: int, channels: int, pixels: bytes) -> float:
    """Share of pixels differing from the image's most common colour.

    Sampled rather than exhaustive: this only has to tell a real card from
    an empty canvas, and a full scan of a 1440x1800 image in pure Python
    is slow enough to be felt in the live editor.
    """
    step = max(1, (width * height) // 40000)
    counts: dict[bytes, int] = {}
    samples: list[bytes] = []
    for index in range(0, width * height, step):
        pixel = pixels[index * channels:index * channels + 3]
        samples.append(pixel)
        counts[pixel] = counts.get(pixel, 0) + 1
    if not samples:
        return 0.0
    background = max(counts, key=lambda key: counts[key])
    return sum(1 for pixel in samples if pixel != background) / len(samples)


def verify_png(path: Path, width: int, height: int) -> list[str]:
    """Report why a produced PNG is not deliverable, if it is not."""
    problems: list[str] = []
    try:
        data = path.read_bytes()
    except OSError as error:
        return [f"PNG illeggibile: {error}"]
    if not data:
        return ["PNG vuoto"]
    try:
        actual_width, actual_height = png_dimensions(data)
    except ValueError as error:
        return [str(error)]
    if (actual_width, actual_height) != (width, height):
        problems.append(
            f"dimensioni {actual_width}x{actual_height} invece di {width}x{height}"
        )
    try:
        decoded_width, decoded_height, channels, pixels = decode_png(data)
        coverage = ink_coverage(decoded_width, decoded_height, channels, pixels)
        if coverage < MIN_INK_COVERAGE:
            problems.append(
                f"immagine praticamente vuota ({coverage * 100:.2f}% di pixel non uniformi): "
                "il convertitore non ha disegnato testo o grafica"
            )
    except (ValueError, zlib.error) as error:
        # An unreadable interior is not automatically a defect: the header
        # may be fine and the encoding simply outside this small reader.
        problems.append(f"contenuto PNG non verificabile: {error}")
    return problems


# --------------------------------------------------------------------------
# Backends
# --------------------------------------------------------------------------


def _run(command: list[str], env: dict[str, str] | None = None) -> None:
    subprocess.run(
        command, check=True, env=env, timeout=CONVERSION_TIMEOUT_SECONDS,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )


def _sharp(svg: Path, png: Path, width: int, height: int, options: dict[str, Any]) -> None:
    node, node_modules = options.get("node"), options.get("node_modules")
    if not (node and node_modules and Path(node).is_file() and Path(node_modules).is_dir()):
        raise FileNotFoundError("node o node_modules non disponibili")
    env = os.environ.copy()
    env["NODE_PATH"] = str(node_modules)
    _run(
        [str(node), str(SCRIPT_DIR / "svg_to_png.cjs"), str(svg), str(png), str(width), str(height)],
        env=env,
    )


def _chrome_binary() -> str | None:
    for candidate in CHROME_CANDIDATES:
        if Path(candidate).is_file():
            return candidate
    return shutil.which("google-chrome") or shutil.which("chromium")


def _chrome(svg: Path, png: Path, width: int, height: int, options: dict[str, Any]) -> None:
    binary = _chrome_binary()
    if not binary:
        raise FileNotFoundError("nessun browser Chromium disponibile")
    _run([
        binary, "--headless", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
        "--force-device-scale-factor=1", f"--window-size={width},{height}",
        f"--screenshot={png}", svg.resolve().as_uri(),
    ])


def _chrome_ribbons(svg: Path, png: Path, width: int, height: int, options: dict[str, Any]) -> None:
    """Use the same Blink engine as the editor, after embedded fonts load.

    The CLI screenshot backend above cannot await document.fonts.ready.
    Ribbons need Playwright's explicit font/image wait and element capture;
    librsvg/sharp silently substitute the embedded brand font and collapse
    spaces on independently formatted live SVG text fragments.
    """
    node, node_modules = options.get("node"), options.get("node_modules")
    if not (node and node_modules and Path(node).is_file() and Path(node_modules).is_dir()):
        raise FileNotFoundError("Nastri richiede Node e Playwright configurati per conservare l'anteprima")
    binary = options.get("browser") or _chrome_binary()
    if not binary or not Path(binary).is_file():
        raise FileNotFoundError("nessun browser Chromium disponibile per la prova Nastri")
    env = os.environ.copy()
    env["NODE_PATH"] = str(node_modules)
    _run([str(node), str(SCRIPT_DIR / "svg_to_png.cjs"), str(svg), str(png),
          str(width), str(height), "chrome", str(binary)], env=env)


def _rsvg(svg: Path, png: Path, width: int, height: int, options: dict[str, Any]) -> None:
    binary = shutil.which("rsvg-convert")
    if not binary:
        raise FileNotFoundError("rsvg-convert non disponibile")
    _run([binary, "-w", str(width), "-h", str(height), "-o", str(png), str(svg)])


def _magick(svg: Path, png: Path, width: int, height: int, options: dict[str, Any]) -> None:
    binary = shutil.which("magick") or shutil.which("convert")
    if not binary:
        raise FileNotFoundError("ImageMagick non disponibile")
    command = [binary]
    if binary.endswith("magick"):
        command.append("convert")
    _run([*command, "-background", "none", "-density", "144",
          str(svg), "-resize", f"{width}x{height}!", str(png)])


def _cairosvg(svg: Path, png: Path, width: int, height: int, options: dict[str, Any]) -> None:
    try:
        import cairosvg  # noqa: PLC0415  (optional, probed at call time)
    except ImportError as error:
        raise FileNotFoundError("cairosvg non disponibile") from error
    cairosvg.svg2png(
        url=str(svg), write_to=str(png), output_width=width, output_height=height
    )


# Order is a compatibility decision, not a preference: sharp has produced
# every shipped PNG so far, so it stays first and existing output does not
# change. The rest exist so a machine without Node still delivers a PNG --
# with the backend recorded, because their text metrics differ slightly.
# The backend every shipped PNG has been produced with. Anything else
# is a working substitute, not an equivalent one -- see the module
# docstring -- so callers are expected to surface when it was used.
PRIMARY_BACKEND = "sharp"


def primary_backend(visual_grammar: str | None = None) -> str:
    """Compatibility baseline for this grammar's preview/export pairing."""
    return "chrome" if visual_grammar in {"ribbons", "urban"} else PRIMARY_BACKEND


def _svg_grammar(svg_path: Path) -> str | None:
    # Only inspect the root tag, before the large embedded font payload.
    # The renderer writes this marker itself; text content cannot select a
    # converter by mentioning the same string inside the card.
    try:
        with svg_path.open("r", encoding="utf-8") as source:
            head = source.read(4096)
    except (OSError, UnicodeError):
        return None
    root = re.search(r"<svg\b[^>]*>", head)
    if root:
        match = re.search(r"\bdata-visual-grammar\s*=\s*([\"'])(ribbons|urban)\1", root.group())
        if match: return match.group(2)
    return None

BACKENDS: tuple[tuple[str, Callable[..., None]], ...] = (
    ("sharp", _sharp),
    ("chrome", _chrome),
    ("rsvg-convert", _rsvg),
    ("cairosvg", _cairosvg),
    ("imagemagick", _magick),
)


def rasterize(
    svg_path: Path, png_path: Path, width: int, height: int, **options: Any
) -> str:
    """Convert ``svg_path`` to ``png_path``; return the backend that worked.

    A backend counts as successful only when what it produced passes
    verify_png, so a converter that writes a blank or mis-sized canvas is
    treated as a failure and the next one is tried.

    Parametric grammars (or their renderer-owned SVG root marker)
    requires Chromium through Playwright; no legacy-font fallback is accepted.
    """
    attempts: list[tuple[str, str]] = []
    visual_grammar = options.get("visual_grammar") or _svg_grammar(svg_path)
    # Parametric grammars have verified browser font metrics. Reject unavailable Chromium
    # rather than delivering an unapproved font/spacing substitution.
    backends = (("chrome", _chrome_ribbons),) if visual_grammar in {"ribbons", "urban"} else BACKENDS
    for name, backend in backends:
        try:
            backend(svg_path, png_path, width, height, options)
        except FileNotFoundError as error:
            attempts.append((name, f"non disponibile ({error})"))
            continue
        except subprocess.TimeoutExpired:
            attempts.append((name, f"scaduto dopo {CONVERSION_TIMEOUT_SECONDS}s"))
            continue
        except subprocess.CalledProcessError as error:
            detail = (error.stderr or "").strip().splitlines()
            # The Node/Playwright stack ends with an unhelpful file location;
            # retain its actual failure rather than losing the explanation.
            if not detail:
                reason = f"uscita {error.returncode}"
            else:
                reason = detail[0] if visual_grammar in {"ribbons", "urban"} else detail[-1]
            attempts.append((name, reason))
            continue
        except (OSError, ValueError) as error:
            attempts.append((name, str(error)))
            continue
        problems = verify_png(png_path, width, height)
        if problems:
            attempts.append((name, "; ".join(problems)))
            png_path.unlink(missing_ok=True)
            continue
        return name
    raise RasterError(attempts)


def available_backends(**options: Any) -> list[str]:
    """Names of backends whose tool is present, without converting."""
    node, node_modules = options.get("node"), options.get("node_modules")
    present: list[str] = []
    if node and node_modules and Path(node).is_file() and Path(node_modules).is_dir():
        present.append("sharp")
    if _chrome_binary():
        present.append("chrome")
    if shutil.which("rsvg-convert"):
        present.append("rsvg-convert")
    try:
        import cairosvg  # noqa: F401,PLC0415

        present.append("cairosvg")
    except ImportError:
        pass
    if shutil.which("magick") or shutil.which("convert"):
        present.append("imagemagick")
    return present
