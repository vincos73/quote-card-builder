#!/usr/bin/env python3
"""Render deterministic 4:5 quote-card proofs from a visual manifest 0.2."""

from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import math
import re
import struct
import sys
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Callable

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
import rasterize

DIRECTIONS = ("editorial", "statement", "contextual")
TRANSFORMATIONS = {"VERBATIM", "EDITED", "PARAPHRASE", "AI_GENERATED"}
EVIDENCE_STATUSES = {"VERIFIED", "USER_SUPPLIED", "UNVERIFIED", "CONFLICT"}
ATTRIBUTION_ROLES = {"speaker", "author", "publisher", "none"}
STYLE_TYPES = {"bold", "italic", "underline", "highlight", "accent", "outline"}
# Hollow-glyph stroke as a fraction of the row's own font size, so the same
# span reads identically at every format's fitted size -- and in a Poster row
# drawn 1.12x larger than its neighbours. Expressed here and resolved to
# absolute user units at draw time: em-relative stroke-width is legal CSS but
# not equally supported across the three rasterisers this project targets.
OUTLINE_STROKE_EM = 0.035
SYSTEM_CARD_FONTS = {"arial"}
# Not a design suggestion: a defensive ceiling only, so malformed/pasted
# input can't produce a pathological line array. The real constraint is
# vertical/horizontal fit, already enforced by the safe-area QA checks.
MAX_LINES = 40
HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")
UNSAFE_SVG = re.compile(r"<(?:script|foreignObject)\b|\bon\w+\s*=", re.IGNORECASE)

# Single source of truth for per-direction text geometry, as ratios of the
# canvas. render_svg draws from it and render_quote_card_pack fits and
# QA-measures against it, so the size a card is *fitted* at and the size it
# is *drawn* at cannot drift apart.
#
# Every value here used to be written twice, once per module, kept in sync
# by hand. Three shipped bugs came from those copies disagreeing: a stale
# font-size ceiling, two different safe-margin values, and a fitting pass
# that measured a row at 1.0x which then rendered at 1.12x and overflowed.
# Add a direction here, not in either module's branches.
DIRECTION_GEOMETRY = {
    # inset: left/right text margin. start_y: first baseline.
    # fit_height: vertical budget the fitter may fill.
    "editorial": {"inset": 0.075, "start_y": 0.36, "fit_height": 0.54, "line_ratio": 1.05},
    "statement": {"inset": 0.072, "start_y": 0.31, "fit_height": 0.58, "line_ratio": 1.15},
    "contextual": {"inset": 0.17, "start_y": 0.40, "fit_height": 0.50, "line_ratio": 1.06,
                   "right_inset": 0.12},
}
# The quote is drawn at this tracking in every direction; width estimates
# must include it or they over-predict and under-size the fitted font.
QUOTE_TRACKING_EM = -0.025
# Poster rows carrying emphasis render 1.12x larger than plain rows.
STATEMENT_STRONG_MULTIPLIER = 1.12
VERTICAL_OFFSETS = {"upper": -0.075, "center": 0.0, "lower": 0.075}


def direction_geometry(
    direction: str, width: int, height: int, vertical_position: str = "center"
) -> dict[str, float]:
    """Resolve DIRECTION_GEOMETRY into absolute pixels for one canvas.

    Both the renderer and the fitting/QA pass call this, so neither can
    hold a private copy of a margin or baseline that the other disagrees
    with.
    """
    spec = DIRECTION_GEOMETRY[direction]
    inset = width * spec["inset"]
    right_inset = width * spec.get("right_inset", spec["inset"])
    return {
        "text_x": inset,
        "text_width": width - inset - right_inset,
        "start_y": height * spec["start_y"] + VERTICAL_OFFSETS.get(vertical_position, 0.0) * height,
        "fit_height": height * spec["fit_height"],
        "line_ratio": spec["line_ratio"],
        "tracking_em": QUOTE_TRACKING_EM,
    }


def normalize_spaces(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", value).split())


def add_error(errors: list[dict[str, str]], path: str, code: str, message: str) -> None:
    errors.append({"path": path, "code": code, "message": message})


def validate_text_styles(
    styles: Any, text: str, errors: list[dict[str, str]], path: str = "content.styles"
) -> None:
    if not isinstance(styles, list) or len(styles) > 64:
        add_error(errors, path, "styles", "Usare una lista con al massimo 64 intervalli di formattazione.")
        return
    for index, style in enumerate(styles):
        item_path = f"{path}[{index}]"
        if not isinstance(style, dict) or set(style) != {"start", "end", "type"}:
            add_error(errors, item_path, "shape", "Ogni intervallo richiede start, end e type.")
            continue
        start, end, kind = style.get("start"), style.get("end"), style.get("type")
        if not isinstance(start, int) or isinstance(start, bool) or not isinstance(end, int) or isinstance(end, bool):
            add_error(errors, item_path, "offset", "Start ed end devono essere interi.")
        elif not 0 <= start < end <= len(text):
            add_error(errors, item_path, "range", "L'intervallo deve ricadere nel testo corrente.")
        if kind not in STYLE_TYPES:
            add_error(errors, f"{item_path}.type", "enum", "Usare bold, italic, underline, highlight, accent o outline.")


def require_dict(value: Any, path: str, errors: list[dict[str, str]]) -> dict[str, Any]:
    if not isinstance(value, dict):
        add_error(errors, path, "type", "Deve essere un oggetto.")
        return {}
    return value


def require_string(
    obj: dict[str, Any], key: str, path: str, errors: list[dict[str, str]], *, allow_empty: bool = False
) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        add_error(errors, f"{path}.{key}", "required", "Deve essere una stringa non vuota.")
        return ""
    return value


def resolve_asset(path_value: str, manifest_dir: Path) -> Path:
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = manifest_dir / path
    return path.resolve()


def parse_hex(color: str) -> tuple[int, int, int]:
    return tuple(int(color[index : index + 2], 16) for index in (1, 3, 5))  # type: ignore[return-value]


def relative_luminance(color: str) -> float:
    channels = []
    for value in parse_hex(color):
        channel = value / 255
        channels.append(channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast_ratio(first: str, second: str) -> float:
    light, dark = sorted((relative_luminance(first), relative_luminance(second)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


def validate_visual_manifest(data: Any, manifest_dir: Path) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    root = require_dict(data, "$", errors)
    if not root:
        return errors

    if root.get("schema_version") != "0.2":
        add_error(errors, "schema_version", "unsupported", "La versione visuale supportata è 0.2.")
    if root.get("state") != "contenuto_approvato":
        add_error(errors, "state", "approval_required", "La prova richiede contenuto_approvato.")

    content = require_dict(root.get("content"), "content", errors)
    text = require_string(content, "text", "content", errors)
    lines = content.get("lines")
    if (
        not isinstance(lines, list)
        or not 1 <= len(lines) <= MAX_LINES
        or any(not isinstance(line, str) for line in lines if isinstance(lines, list))
        or (isinstance(lines, list) and not any(line.strip() for line in lines if isinstance(line, str)))
    ):
        add_error(errors, "content.lines", "lines", f"Inserire almeno una riga di testo (fino a {MAX_LINES}, oltre è lo spazio del formato a decidere se il testo entra).")
        lines = []
    if lines and normalize_spaces(" ".join(lines)) != normalize_spaces(text):
        add_error(
            errors,
            "content.lines",
            "text_changed",
            "Gli a capo non ricostruiscono esattamente il testo approvato.",
        )

    transformation = content.get("transformation")
    evidence_status = content.get("evidence_status")
    if transformation not in TRANSFORMATIONS:
        add_error(errors, "content.transformation", "enum", "Trasformazione non ammessa.")
    if evidence_status not in EVIDENCE_STATUSES:
        add_error(errors, "content.evidence_status", "enum", "Stato della prova non ammesso.")

    emphasis = content.get("emphasis", "")
    if not isinstance(emphasis, str):
        add_error(errors, "content.emphasis", "type", "Deve essere una stringa.")
        emphasis = ""
    if emphasis and emphasis not in text:
        add_error(errors, "content.emphasis", "not_found", "L'enfasi deve coincidere con il testo approvato.")

    styles = content.get("styles")
    if styles is not None:
        validate_text_styles(styles, text, errors)

    attribution = require_dict(content.get("attribution"), "content.attribution", errors)
    role = attribution.get("role")
    if role not in ATTRIBUTION_ROLES:
        add_error(errors, "content.attribution.role", "enum", "Ruolo di attribuzione non ammesso.")
    label = attribution.get("label", "")
    if role != "none" and (not isinstance(label, str) or not label.strip()):
        add_error(errors, "content.attribution.label", "required", "Il ruolo richiede un'etichetta.")

    canvas = require_dict(root.get("canvas"), "canvas", errors)
    width = canvas.get("width")
    height = canvas.get("height")
    if not isinstance(width, int) or isinstance(width, bool) or width < 800:
        add_error(errors, "canvas.width", "range", "La larghezza deve essere un intero di almeno 800 px.")
    if not isinstance(height, int) or isinstance(height, bool) or height < 1000:
        add_error(errors, "canvas.height", "range", "L'altezza deve essere un intero di almeno 1000 px.")
    if isinstance(width, int) and isinstance(height, int) and not math.isclose(width / height, 4 / 5, rel_tol=0.001):
        add_error(errors, "canvas", "ratio", "Il renderer 0.2 accetta soltanto il rapporto 4:5.")

    direction = root.get("direction")
    if direction not in DIRECTIONS:
        add_error(errors, "direction", "enum", "Direzione non ammessa.")

    brand = require_dict(root.get("brand"), "brand", errors)
    require_string(brand, "name", "brand", errors)
    colors = require_dict(brand.get("colors"), "brand.colors", errors)
    for key in ("primary", "accent", "background", "text"):
        value = colors.get(key)
        if not isinstance(value, str) or not HEX_COLOR.fullmatch(value):
            add_error(errors, f"brand.colors.{key}", "color", "Usare un colore #RRGGBB.")

    font = require_dict(brand.get("font"), "brand.font", errors)
    require_string(font, "family", "brand.font", errors)
    for key in ("regular_path", "medium_path", "bold_path", "italic_path"):
        value = font.get(key)
        if value is not None:
            if not isinstance(value, str) or not value.strip():
                add_error(errors, f"brand.font.{key}", "type", "Il percorso deve essere una stringa.")
            elif not resolve_asset(value, manifest_dir).is_file():
                add_error(errors, f"brand.font.{key}", "missing", "Il file del font non esiste.")

    logo = brand.get("logo", {})
    if logo is not None:
        logo = require_dict(logo, "brand.logo", errors)
        for key in ("dark_path", "light_path"):
            value = logo.get(key)
            if value is not None:
                if not isinstance(value, str) or not value.strip():
                    add_error(errors, f"brand.logo.{key}", "type", "Il percorso deve essere una stringa.")
                else:
                    asset = resolve_asset(value, manifest_dir)
                    if not asset.is_file():
                        add_error(errors, f"brand.logo.{key}", "missing", "Il file del logo non esiste.")
                    elif asset.suffix.lower() == ".svg":
                        try:
                            if UNSAFE_SVG.search(asset.read_text(encoding="utf-8")):
                                add_error(errors, f"brand.logo.{key}", "unsafe_svg", "Il logo SVG contiene elementi non ammessi.")
                        except UnicodeDecodeError:
                            add_error(errors, f"brand.logo.{key}", "svg_encoding", "Il logo SVG non è UTF-8.")

    if all(
        isinstance(colors.get(key), str) and HEX_COLOR.fullmatch(colors[key])
        for key in ("primary", "accent", "background", "text")
    ):
        checks = {
            "editorial_text": (colors["primary"], colors["background"]),
            "statement_text": (colors["background"], colors["primary"]),
            "statement_emphasis": (colors["accent"], colors["primary"]),
            "contextual_text": (colors["primary"], colors["background"]),
        }
        for name, (foreground, background) in checks.items():
            ratio = contrast_ratio(foreground, background)
            if ratio < 4.5:
                add_error(
                    errors,
                    f"brand.colors.{name}",
                    "contrast",
                    f"Contrasto insufficiente: {ratio:.2f}:1, richiesto 4.5:1.",
                )

    output = root.get("output", {})
    if output is not None:
        output = require_dict(output, "output", errors)
        basename = output.get("basename", "quote-card")
        if not isinstance(basename, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", basename):
            add_error(errors, "output.basename", "basename", "Usare lettere, numeri, punto, trattino o underscore.")

    return errors


def file_data_uri(path: Path) -> str:
    suffix = path.suffix.lower()
    mime = {
        ".svg": "image/svg+xml",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".ttf": "font/ttf",
        ".otf": "font/otf",
        ".woff": "font/woff",
        ".woff2": "font/woff2",
    }.get(suffix, "application/octet-stream")
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def font_css(font: dict[str, Any], manifest_dir: Path) -> str:
    family = html.escape(font["family"], quote=True)
    declarations = []
    for key, weight, style in (
        ("regular_path", 400, "normal"),
        ("medium_path", 500, "normal"),
        ("bold_path", 700, "normal"),
        ("italic_path", 400, "italic"),
    ):
        value = font.get(key)
        if value:
            uri = file_data_uri(resolve_asset(value, manifest_dir))
            declarations.append(
                f"@font-face{{font-family:'{family}';src:url('{uri}');font-weight:{weight};font-style:{style};}}"
            )
    return "".join(declarations)


def card_font_stack(family: str) -> str:
    """Return a predictable Mac/Windows stack for the neutral card baseline."""
    escaped = html.escape(family, quote=True)
    if family.strip().casefold() in SYSTEM_CARD_FONTS:
        return "'Arial','Helvetica Neue',Helvetica,sans-serif"
    return f"'{escaped}',sans-serif"


def logo_data(brand: dict[str, Any], manifest_dir: Path, *, light: bool) -> tuple[str, float] | None:
    logo = brand.get("logo") or {}
    key = "light_path" if light else "dark_path"
    value = logo.get(key) or logo.get("dark_path") or logo.get("light_path")
    if not value:
        return None
    path = resolve_asset(value, manifest_dir)
    aspect_ratio = 4.0
    if path.suffix.lower() == ".svg":
        try:
            root = ET.fromstring(path.read_text(encoding="utf-8"))
            view_box = root.get("viewBox", "").replace(",", " ").split()
            if len(view_box) == 4:
                view_width = float(view_box[2])
                view_height = float(view_box[3])
                if view_width > 0 and view_height > 0:
                    aspect_ratio = view_width / view_height
        except (ET.ParseError, OSError, ValueError):
            aspect_ratio = 4.0
    return file_data_uri(path), aspect_ratio


_FONT_METRICS_CACHE: dict[str, dict[str, float] | None] = {}
_ACTIVE_CHAR_WIDTHS: dict[str, float] | None = None
_ACTIVE_BOLD_CHAR_WIDTHS: dict[str, float] | None = None


def _ttf_table_directory(data: bytes) -> dict[str, tuple[int, int]]:
    num_tables = struct.unpack(">H", data[4:6])[0]
    tables: dict[str, tuple[int, int]] = {}
    offset = 12
    for _ in range(num_tables):
        tag = data[offset:offset + 4].decode("ascii", errors="replace")
        table_offset, length = struct.unpack(">II", data[offset + 8:offset + 16])
        tables[tag] = (table_offset, length)
        offset += 16
    return tables


def _ttf_cmap_format4(data: bytes, off: int) -> dict[int, int]:
    seg_count_x2 = struct.unpack(">H", data[off + 6:off + 8])[0]
    seg_count = seg_count_x2 // 2
    end_codes_off = off + 14
    end_codes = struct.unpack(f">{seg_count}H", data[end_codes_off:end_codes_off + seg_count_x2])
    start_codes_off = end_codes_off + seg_count_x2 + 2
    start_codes = struct.unpack(f">{seg_count}H", data[start_codes_off:start_codes_off + seg_count_x2])
    id_delta_off = start_codes_off + seg_count_x2
    id_deltas = struct.unpack(f">{seg_count}h", data[id_delta_off:id_delta_off + seg_count_x2])
    id_range_off_off = id_delta_off + seg_count_x2
    id_range_offsets = struct.unpack(f">{seg_count}H", data[id_range_off_off:id_range_off_off + seg_count_x2])
    mapping: dict[int, int] = {}
    for i in range(seg_count):
        start, end, delta, range_off = start_codes[i], end_codes[i], id_deltas[i], id_range_offsets[i]
        if start == 0xFFFF and end == 0xFFFF:
            continue
        for code in range(start, end + 1):
            if range_off == 0:
                glyph = (code + delta) & 0xFFFF
            else:
                addr = id_range_off_off + i * 2 + range_off + (code - start) * 2
                if addr + 2 > len(data):
                    continue
                raw = struct.unpack(">H", data[addr:addr + 2])[0]
                glyph = (raw + delta) & 0xFFFF if raw != 0 else 0
            if glyph != 0:
                mapping[code] = glyph
    return mapping


def _load_ttf_char_widths(path: Path) -> dict[str, float]:
    """Read real per-character advance widths (em fractions) straight out of
    a TrueType/OpenType font's cmap/hmtx tables. Pure stdlib, no dependency
    on Pillow or fontTools: parses the sfnt tables by hand.
    """
    data = path.read_bytes()
    tables = _ttf_table_directory(data)
    head_off, _ = tables["head"]
    units_per_em = struct.unpack(">H", data[head_off + 18:head_off + 20])[0]
    hhea_off, _ = tables["hhea"]
    num_h_metrics = struct.unpack(">H", data[hhea_off + 34:hhea_off + 36])[0]
    hmtx_off, _ = tables["hmtx"]
    advance_widths = []
    pos = hmtx_off
    for _ in range(num_h_metrics):
        advance_widths.append(struct.unpack(">H", data[pos:pos + 2])[0])
        pos += 4

    cmap_off, _ = tables["cmap"]
    num_subtables = struct.unpack(">H", data[cmap_off + 2:cmap_off + 4])[0]
    subtable_off = None
    for i in range(num_subtables):
        rec_off = cmap_off + 4 + i * 8
        platform_id, encoding_id, sub_off = struct.unpack(">HHI", data[rec_off:rec_off + 8])
        fmt = struct.unpack(">H", data[cmap_off + sub_off:cmap_off + sub_off + 2])[0]
        if fmt == 4 and (platform_id, encoding_id) in {(3, 1), (0, 3)}:
            subtable_off = cmap_off + sub_off
            break
    if subtable_off is None:
        raise ValueError("no usable (platform 3,1) cmap format 4 subtable")
    unicode_to_glyph = _ttf_cmap_format4(data, subtable_off)

    widths: dict[str, float] = {}
    for codepoint, glyph in unicode_to_glyph.items():
        aw = advance_widths[glyph] if glyph < len(advance_widths) else advance_widths[-1]
        widths[chr(codepoint)] = aw / units_per_em
    return widths


def _system_font_candidates(family: str) -> list[Path]:
    if family.strip().casefold() not in SYSTEM_CARD_FONTS:
        return []
    return [
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("/usr/share/fonts/truetype/msttcorefonts/Arial.ttf"),
    ]


def _system_bold_font_candidates(family: str) -> list[Path]:
    if family.strip().casefold() not in SYSTEM_CARD_FONTS:
        return []
    return [
        Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf"),
        Path("/usr/share/fonts/truetype/msttcorefonts/Arial_Bold.ttf"),
    ]


def _resolve_char_widths(candidates: list[Path]) -> dict[str, float] | None:
    for candidate in candidates:
        cache_key = str(candidate)
        if cache_key not in _FONT_METRICS_CACHE:
            widths: dict[str, float] | None
            try:
                widths = _load_ttf_char_widths(candidate) if candidate.is_file() else None
            except Exception:
                widths = None
            _FONT_METRICS_CACHE[cache_key] = widths
        if _FONT_METRICS_CACHE[cache_key]:
            return _FONT_METRICS_CACHE[cache_key]
    return None


def activate_font_metrics(font: dict[str, Any], manifest_dir: Path) -> None:
    """Point visual_units() at real glyph advance widths for this render's
    brand font when a real font file can be located and parsed. Falls back
    silently to the generic character-category heuristic otherwise (unknown
    family, unreadable file, unsupported cmap format) -- this must never be
    the reason a render fails.

    Also loads bold glyph widths separately when available (brand
    ``bold_path`` or the system bold face), so callers that render at
    font-weight 700 -- the Poster/statement direction renders its entire
    quote block bold -- can measure against the true, wider bold glyphs
    instead of under-measuring with regular-weight metrics. Regular glyphs
    are narrower than bold ones at the same point size, so reusing regular
    metrics for bold text systematically undersizes anything measured from
    them, such as a highlight marker band trailing short of the glyphs it
    is meant to cover.
    """
    global _ACTIVE_CHAR_WIDTHS, _ACTIVE_BOLD_CHAR_WIDTHS
    _ACTIVE_CHAR_WIDTHS = None
    _ACTIVE_BOLD_CHAR_WIDTHS = None
    candidates: list[Path] = []
    regular_path = font.get("regular_path")
    if regular_path:
        try:
            candidates.append(resolve_asset(regular_path, manifest_dir))
        except Exception:
            pass
    candidates.extend(_system_font_candidates(font.get("family", "")))
    _ACTIVE_CHAR_WIDTHS = _resolve_char_widths(candidates)

    bold_candidates: list[Path] = []
    bold_path = font.get("bold_path")
    if bold_path:
        try:
            bold_candidates.append(resolve_asset(bold_path, manifest_dir))
        except Exception:
            pass
    bold_candidates.extend(_system_bold_font_candidates(font.get("family", "")))
    _ACTIVE_BOLD_CHAR_WIDTHS = _resolve_char_widths(bold_candidates)


def font_metrics_active() -> bool:
    """True when visual_units() is currently backed by real glyph widths
    parsed from a font file, rather than the generic character heuristic."""
    return _ACTIVE_CHAR_WIDTHS is not None


def visual_units(value: str, *, bold: bool = False) -> float:
    active = _ACTIVE_BOLD_CHAR_WIDTHS if bold and _ACTIVE_BOLD_CHAR_WIDTHS is not None else _ACTIVE_CHAR_WIDTHS
    if active is not None:
        units = 0.0
        for char in value:
            if char in active:
                units += active[char]
            elif char.isspace():
                units += active.get(" ", 0.28)
            else:
                units += 0.6
        return units
    units = 0.0
    for char in value:
        if char.isspace():
            units += 0.45
        elif unicodedata.east_asian_width(char) in {"W", "F"}:
            units += 1.0
        elif char in "ilIjtfr.,:;'!|":
            units += 0.42
        elif char in "mwMW@%":
            units += 0.95
        else:
            units += 0.66
    # Bold glyphs run wider than regular at the same point size; without
    # real glyph metrics to measure against, approximate that with a
    # modest across-the-board expansion rather than reusing the regular
    # heuristic unchanged, which would undersize anything measured for
    # bold-rendered text (e.g. a Poster highlight marker band).
    return units * 1.07 if bold else units


def fitted_font_size(
    lines: list[str], available_width: float, available_height: float, maximum: float,
    *, letter_spacing_em: float = 0.0,
) -> float:
    """Largest size at which every line's *rendered* width (including
    tracking) still fits ``available_width``. Tracking is per line -- a
    line with more characters accrues more negative tracking, which is
    exactly what ``highlight_rects``'s ``measured()`` computes at draw
    time, so this bound matches what actually gets drawn instead of
    over-estimating width and picking a smaller size than necessary.
    """
    def width_units(line: str) -> float:
        return visual_units(line) + letter_spacing_em * max(0, len(line) - 1)

    max_units = max(width_units(line) for line in lines)
    width_size = available_width / max(max_units, 1e-6)
    height_size = available_height / (len(lines) * 1.18)
    return max(48, min(maximum, width_size, height_size))


def statement_visual_lines(lines: list[str], width: int, height: int) -> list[str]:
    """Add poster-style soft wraps without removing any user-authored hard break."""
    # Keep semantic phrases together so the max-fit can scale the poster
    # without creating weak one-word rows.
    target_units = 16.0 if width / height >= 0.75 else 12.0
    maximum_rows = 7 if width / height >= 0.75 else 8

    def wrap(limit: float) -> list[str]:
        rows: list[str] = []
        for line in lines:
            if not line:
                rows.append("")
                continue
            words = line.split()
            current: list[str] = []
            for word in words:
                candidate = " ".join((*current, word))
                if current and visual_units(candidate.upper()) > limit:
                    rows.append(" ".join(current))
                    current = [word]
                else:
                    current.append(word)
            rows.append(" ".join(current))
        return rows

    visual = wrap(target_units)
    while len(visual) > maximum_rows:
        target_units *= 1.12
        visual = wrap(target_units)
    return visual


def statement_strong_rows(
    lines: list[str], styles: list[dict[str, Any]] | None, emphasis: str
) -> set[int]:
    strong: set[int] = set()
    cursor = 0
    has_text = False
    emphasis_start = " ".join(line for line in lines if line).find(emphasis) if emphasis else -1
    emphasis_end = emphasis_start + len(emphasis) if emphasis_start >= 0 else -1
    for index, line in enumerate(lines):
        if not line:
            continue
        if has_text:
            cursor += 1
        line_start, line_end = cursor, cursor + len(line)
        # "outline" is deliberately absent: it changes a glyph's shape, not
        # its weight, so it must not promote a Poster row to 1.12x and
        # re-open the fit that statement_fitted_font_size just closed.
        if styles and any(
            style["type"] in {"bold", "highlight", "accent"}
            and style["end"] > line_start
            and style["start"] < line_end
            for style in styles
        ):
            strong.add(index)
        elif emphasis_start >= 0 and emphasis_end > line_start and emphasis_start < line_end:
            strong.add(index)
        cursor = line_end
        has_text = True
    # No last-line fallback here: both call sites already guarantee a
    # meaningful default (initial_direction_styles) whenever styles and
    # emphasis are both genuinely absent, before this function ever runs.
    # A "not styles and not emphasis" fallback fired here too, so a style
    # range that exists but happens to land only on a line-join space
    # (e.g. after removing emphasis right at a line break) got silently
    # overridden back onto the last line instead of leaving no row strong.
    return strong


def default_emphasis_span(text: str) -> tuple[int, int] | None:
    """Pick a stable, meaning-based emphasis span on the canonical joined
    text: the final clause, snapped outward to word boundaries.

    Computed once on ``content.text`` -- never on a specific format's
    wrapped ``lines`` -- so the same words are emphasised in 4:5, 1:1 and
    9:16 alike. A row-position rule (e.g. "the second row") drifts because
    each format re-wraps that same text into a different number of rows.
    """
    stripped = text.strip()
    if not stripped:
        return None
    target = max(0, round(len(stripped) * 0.6))
    start = target
    while start > 0 and not stripped[start - 1].isspace():
        start -= 1
    while start < len(stripped) and stripped[start].isspace():
        start += 1
    end = len(stripped)
    if start >= end:
        last_space = stripped.rstrip().rfind(" ")
        start = last_space + 1 if last_space >= 0 else 0
    return (start, end)


def initial_direction_styles(text: str, direction: str) -> list[dict[str, Any]]:
    """Give an untouched first preview one expressive, direction-specific cue.

    Anchored to ``default_emphasis_span`` on the canonical text, so the span
    is identical across every format; only the style ``type`` varies by
    direction. Used only when no user-owned inline treatment or legacy
    emphasis exists -- a manual selection always replaces the first-run cue.
    """
    span = default_emphasis_span(text)
    if span is None:
        return []
    start, end = span
    style_type = "bold" if direction == "editorial" else "accent" if direction == "statement" else "highlight"
    return [{"start": start, "end": end, "type": style_type}]


def statement_row_multipliers(lines: list[str], strong_rows: set[int]) -> list[float]:
    """Per-row vertical weight: blank rows are spacers, emphasised rows grow.

    Fitting and drawing must agree on these or a row measured at 1.0x
    renders at 1.12x and runs past the safe area -- which is exactly the
    bug this shared helper exists to prevent.
    """
    return [
        1.4 if not line else STATEMENT_STRONG_MULTIPLIER if index in strong_rows else 1.0
        for index, line in enumerate(lines)
    ]


def statement_fitted_font_size(
    lines: list[str], strong_rows: set[int], width: int, height: int
) -> float:
    geometry = direction_geometry("statement", width, height)
    line_ratio = geometry["line_ratio"]
    width_limits = [
        geometry["text_width"] / max(
            visual_units(line.upper())
            * (STATEMENT_STRONG_MULTIPLIER if index in strong_rows else 1.0),
            1,
        )
        for index, line in enumerate(lines)
        if line
    ]
    vertical_multipliers = statement_row_multipliers(lines, strong_rows)
    vertical_units = sum(vertical_multipliers[:-1]) * line_ratio + vertical_multipliers[-1]
    height_limit = geometry["fit_height"] / max(vertical_units, 1)
    return max(48, min(width * 0.12, height_limit, *width_limits))


def statement_block_height(font_size: float, lines: list[str], strong_rows: set[int]) -> float:
    multipliers = statement_row_multipliers(lines, strong_rows)
    if not multipliers:
        return 0.0
    line_ratio = DIRECTION_GEOMETRY["statement"]["line_ratio"]
    return (
        sum(font_size * multiplier * line_ratio for multiplier in multipliers[:-1])
        + font_size * multipliers[-1]
    )


def emphasized_lines(
    lines: list[str], emphasis: str, emphasis_color: str,
    text_transform: Callable[[str], str] | None = None,
) -> list[str]:
    """Render one exact emphasis phrase, including when it crosses line breaks."""
    joined = " ".join(lines)
    start = joined.find(emphasis) if emphasis else -1
    transform = text_transform or (lambda value: value)
    if start < 0:
        return [html.escape(transform(line)) for line in lines]
    end = start + len(emphasis)
    rendered: list[str] = []
    cursor = 0
    for line in lines:
        line_start, line_end = cursor, cursor + len(line)
        overlap_start, overlap_end = max(start, line_start), min(end, line_end)
        if overlap_start < overlap_end:
            local_start, local_end = overlap_start - line_start, overlap_end - line_start
            rendered.append(
                f"{html.escape(transform(line[:local_start]))}"
                f"<tspan font-weight=\"700\" fill=\"{emphasis_color}\">"
                f"{html.escape(transform(line[local_start:local_end]))}</tspan>"
                f"{html.escape(transform(line[local_end:]))}"
            )
        else:
            rendered.append(html.escape(transform(line)))
        cursor = line_end + 1
    return rendered


def styled_lines(
    lines: list[str], styles: list[dict[str, Any]], highlight_color: str,
    text_transform: Callable[[str], str] | None = None, highlight_mode: str = "marker",
    highlight_text_color: str | None = None, *, text_color: str | None = None,
    font_size: float = 0.0, row_font_sizes: list[float] | None = None,
) -> list[str]:
    """Render user-owned inline styles against text offsets, preserving spacer rows.

    ``text_color`` and the row sizes are only consulted by the ``outline``
    treatment, which draws hollow glyphs: it needs the ink colour the span
    would otherwise have been filled with, and the size that span is drawn
    at, to pick a stroke width proportional to the glyphs it traces.
    """
    transform = text_transform or (lambda value: value)
    rendered: list[str] = []
    cursor = 0
    has_text = False
    for row_index, line in enumerate(lines):
        if not line:
            rendered.append("")
            continue
        row_size = (
            row_font_sizes[row_index]
            if row_font_sizes is not None and row_index < len(row_font_sizes)
            else font_size
        )
        if has_text:
            cursor += 1
        line_start, line_end = cursor, cursor + len(line)
        boundaries = {0, len(line)}
        for style in styles:
            if style["end"] <= line_start or style["start"] >= line_end:
                continue
            boundaries.add(max(0, style["start"] - line_start))
            boundaries.add(min(len(line), style["end"] - line_start))
        points = sorted(boundaries)
        fragments: list[str] = []
        for index in range(len(points) - 1):
            local_start, local_end = points[index], points[index + 1]
            global_start, global_end = line_start + local_start, line_start + local_end
            active = {
                style["type"]
                for style in styles
                if style["start"] <= global_start and style["end"] >= global_end
            }
            value = html.escape(transform(line[local_start:local_end]))
            if not active:
                fragments.append(value)
                continue
            attributes: list[str] = []
            declarations: list[str] = []
            if "bold" in active:
                attributes.append('font-weight="700"')
            if "italic" in active:
                attributes.append('font-style="italic"')
            if "underline" in active:
                declarations.extend((
                    "text-decoration:underline",
                    "text-decoration-thickness:.07em",
                    "text-underline-offset:.12em",
                ))
            # At most one fill wins per span. Highlights are rendered as
            # marker bands behind the text by ``highlight_rects``; this
            # tspan draws no stroke or band of its own, but its glyph fill
            # still needs to read against that band, which is not
            # necessarily the same color the rest of the line (off the
            # band) is using -- including an "accent"-colored glyph, which
            # would otherwise blend straight into an accent-colored band.
            #
            # The editor keeps these three mutually exclusive, so the order
            # below only settles hand-written manifests. Highlight wins over
            # outline deliberately: hollow glyphs on a marker band are the
            # least legible combination either treatment can produce.
            if "highlight" in active and highlight_text_color:
                attributes.append(f'fill="{highlight_text_color}"')
            elif "outline" in active:
                # Hollow: no fill at all, the whole glyph carried by a stroke
                # in the ink colour the span would otherwise have used, so
                # outline stays a change of shape and never of palette.
                attributes.append('fill="none"')
                attributes.append(f'stroke="{text_color or highlight_color}"')
                attributes.append(f'stroke-width="{OUTLINE_STROKE_EM * row_size:.2f}"')
                attributes.append('stroke-linejoin="round"')
            elif "accent" in active:
                attributes.append(f'fill="{highlight_color}"')
            if declarations:
                attributes.append(f'style="{";".join(declarations)}"')
            fragments.append(f"<tspan {' '.join(attributes)}>{value}</tspan>")
        rendered.append("".join(fragments))
        cursor = line_end
        has_text = True
    return rendered


def highlight_rects(
    lines: list[str], styles: list[dict[str, Any]], *, x: float, y: float,
    font_size: float, line_height: float, color: str,
    text_transform: Callable[[str], str] | None = None,
    anchor: str = "start", row_sizes: list[float] | None = None,
    row_baselines: list[float] | None = None, letter_spacing_em: float = 0.0,
    bold: bool = False,
) -> str:
    """Draw continuous marker bands behind highlighted text spans.

    SVG text strokes hug every glyph. A real highlight is a single rectangular
    band spanning the selected words, so it is emitted as geometry before the
    text element and remains visually continuous over spaces.
    """
    transform = text_transform or (lambda value: value)

    def measured(value: str, size: float) -> float:
        """Match the SVG text width, including the poster's negative tracking."""
        transformed = transform(value)
        glyph_width = visual_units(transformed, bold=bold) * size
        tracking = letter_spacing_em * size * max(0, len(transformed) - 1)
        return max(0.0, glyph_width + tracking)

    rendered: list[str] = []
    cursor = 0
    has_text = False
    for index, line in enumerate(lines):
        if not line:
            continue
        if has_text:
            cursor += 1
        line_start, line_end = cursor, cursor + len(line)
        row_size = row_sizes[index] if row_sizes and index < len(row_sizes) else font_size
        line_y = (
            row_baselines[index]
            if row_baselines is not None and index < len(row_baselines)
            else y + index * line_height
        )
        intervals: list[tuple[int, int]] = []
        for style in styles:
            if style.get("type") != "highlight":
                continue
            start = max(line_start, int(style["start"]))
            end = min(line_end, int(style["end"]))
            if start < end:
                intervals.append((start - line_start, end - line_start))
        intervals.sort()
        merged: list[list[int]] = []
        for start, end in intervals:
            if merged and start <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], end)
            else:
                merged.append([start, end])
        full_width = measured(line, row_size)
        for local_start, local_end in merged:
            before = measured(line[:local_start], row_size)
            width = max(1.0, measured(line[local_start:local_end], row_size))
            if anchor == "end":
                start_x = x - full_width + before
            elif anchor == "middle":
                start_x = x - full_width / 2 + before
            else:
                start_x = x + before
            # Leading edge is an exact fit: it lines up with the start of
            # the text block, and bleeding past that breaks the alignment
            # rather than reading as a highlighter stroke. Trailing edge
            # gets real overshoot, as a highlighter does when the pen
            # lifts -- proportional to size so it scales with the card.
            width += row_size * 0.18
            # Uppercase glyphs (poster) have a taller cap-height relative to
            # font-size than mixed-case text, so the marker needs a bit more
            # headroom than the mixed-case band or capital tops poke out
            # above it -- but Arial Bold's cap-height is already ~0.72em, so
            # the band only needs to clear that by a small margin, not the
            # much larger one this used to carry.
            is_uppercase = text_transform is str.upper
            marker_y = line_y - row_size * (0.82 if is_uppercase else 0.76)
            marker_h = row_size * (0.88 if is_uppercase else 0.82)
            rendered.append(
                f'<rect class="highlight-marker" x="{start_x:.1f}" y="{marker_y:.1f}" '
                f'width="{width:.1f}" height="{marker_h:.1f}" rx="0" '
                f'fill="{color}" opacity="0.88"/>'
            )
        cursor = line_end
        has_text = True
    return "".join(rendered)


def text_block(
    lines: list[str], *, x: float, y: float, font_size: float, line_height: float,
    color: str, emphasis: str, emphasis_color: str, styles: list[dict[str, Any]] | None = None,
    highlight_color: str | None = None, anchor: str = "start",
    text_transform: Callable[[str], str] | None = None, extra_style: str = "",
) -> str:
    rendered = []
    formatted = (
        emphasized_lines(lines, emphasis, emphasis_color, text_transform)
        if styles is None
        else styled_lines(
            lines, styles, highlight_color or emphasis_color, text_transform,
            text_color=color, font_size=font_size,
        )
    )
    markers = (
        highlight_rects(
            lines, styles, x=x, y=y, font_size=font_size, line_height=line_height,
            color=highlight_color or emphasis_color, text_transform=text_transform,
            anchor=anchor,
            letter_spacing_em=QUOTE_TRACKING_EM if "letter-spacing:-0.025em" in extra_style else 0.0,
        )
        if styles else ""
    )
    for index, content in enumerate(formatted):
        line_y = y + index * line_height
        rendered.append(f'<tspan x="{x:.1f}" y="{line_y:.1f}">{content}</tspan>')
    style = f' style="{html.escape(extra_style, quote=True)}"' if extra_style else ""
    text_element = (
        f'<text class="quote" x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
        f'font-size="{font_size:.1f}" fill="{color}"{style}>{"".join(rendered)}</text>'
    )
    return f"{markers}{text_element}"


def statement_text_block(
    lines: list[str], *, x: float, y: float, font_size: float, color: str,
    emphasis: str, emphasis_color: str, strong_rows: set[int],
    styles: list[dict[str, Any]] | None = None, highlight_color: str | None = None,
    highlight_text_color: str | None = None,
) -> str:
    statement_line_ratio = DIRECTION_GEOMETRY["statement"]["line_ratio"]
    formatted = (
        emphasized_lines(lines, emphasis, emphasis_color, str.upper)
        if styles is None
        else styled_lines(
            lines, styles, highlight_color or emphasis_color,
            text_transform=str.upper, highlight_mode="slab",
            highlight_text_color=highlight_text_color,
            text_color=color, font_size=font_size,
            # Poster rows are not all the same size: an emphasised row is
            # drawn 1.12x larger, and a hollow span inside it has to be
            # traced with a stroke scaled to that row, not to the base size.
            row_font_sizes=[
                font_size * multiplier
                for multiplier in statement_row_multipliers(lines, strong_rows)
            ],
        )
    )
    rows: list[str] = []
    row_sizes: list[float] = []
    row_baselines: list[float] = []
    highlight_rows: set[int] = set()
    style_cursor = 0
    has_text = False
    for index, line in enumerate(lines):
        if not line:
            continue
        if has_text:
            style_cursor += 1
        line_end = style_cursor + len(line)
        if styles and any(
            style.get("type") == "highlight"
            and style.get("end", 0) > style_cursor
            and style.get("start", 0) < line_end
            for style in styles
        ):
            highlight_rows.add(index)
        style_cursor = line_end
        has_text = True
    cursor_y = y
    for index, content in enumerate(formatted):
        multiplier = 1.4 if not lines[index] else 1.12 if index in strong_rows else 1.0
        size = font_size * multiplier
        row_sizes.append(size)
        row_baselines.append(cursor_y)
        # A highlight is a background marker, never an accent-colored glyph:
        # keeping the row white preserves contrast against the accent band.
        fill = color if index in highlight_rows else emphasis_color if index in strong_rows else color
        weight = ' font-weight="700"' if index in strong_rows else ""
        rows.append(
            f'<tspan x="{x:.1f}" y="{cursor_y:.1f}" font-size="{size:.1f}" fill="{fill}"{weight}>{content}</tspan>'
        )
        cursor_y += size * statement_line_ratio
    markers = (
        highlight_rects(
            lines, styles or [], x=x, y=y, font_size=font_size,
            line_height=font_size * statement_line_ratio, color=highlight_color or emphasis_color,
            text_transform=str.upper, row_sizes=row_sizes, row_baselines=row_baselines,
            letter_spacing_em=QUOTE_TRACKING_EM, bold=True,
        )
        if styles else ""
    )
    text_element = (
        f'<text class="quote" data-layout="statement-poster" x="{x:.1f}" y="{y:.1f}" '
        f'style="font-weight:700;letter-spacing:-0.025em" fill="{color}">{"".join(rows)}</text>'
    )
    return f"{markers}{text_element}"


def legible_color(preferred: str, fallback: str, surface: str, *, minimum: float = 3.0) -> str:
    """Pick ``preferred`` for a decorative/line element only if it actually
    reads against ``surface`` at the WCAG non-text floor (3:1); otherwise
    fall back to ``fallback`` (always ``primary``, itself already validated
    at 4.5:1 against every surface a brand profile can supply).

    This replaces alpha-blending a brand color into the surface to fake a
    lighter weight: that composites an unapproved third hue and does
    nothing for contrast when the two colors are already close in
    lightness. Visual weight should be tuned with area (stroke width,
    element count), never with opacity on top of a legibility problem.
    """
    return preferred if contrast_ratio(preferred, surface) >= minimum else fallback


def direction_graphic(
    direction: str, *, width: int, height: int, colors: dict[str, str], enabled: bool
) -> str:
    """Render one product-specific visual grammar for each direction.

    Every stroke and fill here is a full-opacity brand color: opacity is
    never used to soften a color's presence, because alpha-blending one
    brand color over another invents a third, unapproved hue and can
    silently erase contrast that validation already checked for the flat
    colors. Visual weight is tuned with area (stroke width, element count)
    instead.
    """
    if not enabled:
        return ""
    if direction == "editorial":
        # The page itself is `colors["background"]`; pick whichever brand
        # color actually reads against it instead of assuming accent does.
        stroke_color = legible_color(colors["accent"], colors["primary"], colors["background"])
        paths: list[str] = []
        for index in range(6):
            top_x = width * (0.89 + index * 0.026)
            top_y = -height * 0.07 + index * height * 0.018
            paths.append(
                f'<path class="contour-path contour-path--top" d="M {top_x:.1f} {top_y:.1f} '
                f'C {top_x - width * 0.12:.1f} {top_y + height * 0.05:.1f}, '
                f'{top_x - width * 0.15:.1f} {top_y + height * 0.14:.1f}, '
                f'{top_x - width * 0.07:.1f} {top_y + height * 0.21:.1f} '
                f'S {top_x + width * 0.055:.1f} {top_y + height * 0.29:.1f}, '
                f'{top_x:.1f} {top_y + height * 0.39:.1f}"/>'
            )
            bottom_y = height * (0.67 + index * 0.019)
            paths.append(
                f'<path class="contour-path contour-path--bottom" d="M {-width * 0.045:.1f} {bottom_y:.1f} '
                f'C {width * 0.075:.1f} {bottom_y + height * 0.04:.1f}, '
                f'{width * 0.13:.1f} {bottom_y + height * 0.10:.1f}, '
                f'{width * 0.08:.1f} {bottom_y + height * 0.17:.1f} '
                f'S {-width * 0.015:.1f} {bottom_y + height * 0.27:.1f}, '
                f'{width * 0.055:.1f} {bottom_y + height * 0.37:.1f}"/>'
            )
        return (
            '<g class="direction-graphic direction-graphic--contours" fill="none" '
            f'stroke="{stroke_color}" stroke-width="{max(2.0, width * 0.0022):.1f}">{"".join(paths)}</g>'
        )
    if direction == "statement":
        # Concentric rings radiating from two opposite corners, like an
        # echo/ripple. Stroke width tapers outward (never opacity) to read
        # as a fade while every ring stays a full-opacity brand color.
        ring_color = colors["accent"]
        corners = [(width, 0.0), (0.0, height)]
        ring_count = 4
        base_radius = width * 0.05
        step = width * 0.07
        max_stroke = width * 0.016
        min_stroke = max(2.0, width * 0.003)
        rings: list[str] = []
        for cx, cy in corners:
            for i in range(ring_count):
                radius = base_radius + i * step
                fade = i / (ring_count - 1)
                stroke = max_stroke + (min_stroke - max_stroke) * fade
                rings.append(
                    f'<circle class="echo-ring" cx="{cx:.1f}" cy="{cy:.1f}" r="{radius:.1f}" '
                    f'fill="none" stroke="{ring_color}" stroke-width="{stroke:.1f}"/>'
                )
        return '<g class="direction-graphic direction-graphic--echo">' + "".join(rings) + '</g>'
    # Contextual/Frame: dots sit over the accent field; "statement_emphasis"
    # already guarantees primary reads at >=4.5:1 against accent, so draw
    # them at full opacity rather than blending a third hue.
    dots: list[str] = []
    gap = width * 0.027
    for row in range(4):
        for column in range(5):
            dots.append(
                f'<circle class="field-dot field-dot--top" cx="{width * 0.825 + column * gap:.1f}" '
                f'cy="{height * 0.035 + row * gap:.1f}" r="{max(2.5, width * 0.0027):.1f}"/>'
            )
            dots.append(
                f'<circle class="field-dot field-dot--bottom" cx="{width * 0.02 + column * gap:.1f}" '
                f'cy="{height * 0.87 + row * gap:.1f}" r="{max(2.5, width * 0.0027):.1f}"/>'
            )
    return (
        '<g class="direction-graphic direction-graphic--field" '
        f'fill="{colors["primary"]}">{"".join(dots)}</g>'
    )


def logo_image(
    asset: tuple[str, float] | None,
    *,
    x: float,
    y: float,
    width: float,
    filter_value: str = "",
) -> str:
    if not asset:
        return ""
    uri, aspect_ratio = asset
    height = width / aspect_ratio
    effect = f' style="filter:{html.escape(filter_value, quote=True)}"' if filter_value else ""
    return (
        f'<image href="{uri}" x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" '
        f'height="{height:.1f}" preserveAspectRatio="xMinYMid meet"{effect}/>'
    )


def measured_text_width(text: str, font_size: float, *, letter_spacing_em: float = 0.0) -> float:
    """Rendered pixel width of ``text`` at ``font_size``, tracking included --
    the same estimate ``fitted_font_size`` and ``highlight_rects`` use, so a
    mark or rule anchored with this lines up with what actually gets drawn.
    """
    return visual_units(text) * font_size + letter_spacing_em * font_size * max(0, len(text) - 1)


def last_text_line(lines: list[str]) -> str:
    return next((line for line in reversed(lines) if line), "")


def render_svg(
    data: dict[str, Any],
    manifest_dir: Path,
    direction: str,
    *,
    font_size_override: float | None = None,
    render_options: dict[str, Any] | None = None,
) -> str:
    width = data["canvas"]["width"]
    height = data["canvas"]["height"]
    content = data["content"]
    brand = data["brand"]
    colors = brand["colors"]
    family = brand["font"]["family"]
    font_stack = card_font_stack(family)
    activate_font_metrics(brand["font"], manifest_dir)
    lines = content["lines"]
    emphasis = content.get("emphasis", "")
    styles = content.get("styles")
    # An empty list is ambiguous by itself -- it means both "never touched"
    # and "user removed every style". styles_customized disambiguates: only
    # apply the first-run auto-signature cue when the user has never acted
    # on formatting at all.
    if not styles and not emphasis and not content.get("styles_customized"):
        styles = initial_direction_styles(content["text"], direction)
    attribution = content["attribution"].get("label", "")
    source = data.get("source") or {}
    options = {**(data.get("presentation") or {}), **(render_options or {})}
    logo_mode = options.get("logo_mode", "auto")
    graphic_mode = options.get("graphic_mode", "auto")
    graphic = direction_graphic(
        direction, width=width, height=height, colors=colors, enabled=graphic_mode != "hidden"
    )
    vertical_position = options.get("vertical_position", "center")
    geometry = direction_geometry(direction, width, height, vertical_position)
    safe = width * 0.085
    css = (
        font_css(brand["font"], manifest_dir)
        + f".quote{{font-family:{font_stack};font-weight:500;font-synthesis:weight;letter-spacing:-0.018em;}}"
        + f".meta{{font-family:{font_stack};font-weight:500;letter-spacing:0.08em;}}"
        + ".data{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-weight:600;letter-spacing:0.08em;}"
    )

    if direction == "editorial":
        background = colors["background"]
        quote_color = colors["primary"]
        quote_x = geometry["text_x"]
        font_size = font_size_override or fitted_font_size(
            lines, geometry["text_width"], geometry["fit_height"], float(max(width, height)),
            letter_spacing_em=geometry["tracking_em"],
        )
        line_height = font_size * geometry["line_ratio"]
        block_height = line_height * max(0, len(lines) - 1) + font_size
        start_y = geometry["start_y"]
        logo = "" if logo_mode == "hidden" else logo_image(
            logo_data(brand, manifest_dir, light=False),
            x=width * 0.07, y=height * 0.055, width=width * 0.21,
        )
        quote = text_block(
            lines, x=quote_x, y=start_y, font_size=font_size, line_height=line_height,
            color=quote_color, emphasis=emphasis, emphasis_color=quote_color,
            styles=styles, highlight_color=colors["accent"],
            extra_style="font-weight:400;letter-spacing:-0.025em"
        )
        # Always the guide's fixed bottom margin, independent of text
        # length or font size -- a stable anchor rather than one that
        # drifts with content.
        attribution_y = height * 0.915
        body = (
            f'<rect width="{width}" height="{height}" fill="{background}"/>'
            f'{graphic}{logo}{quote}'
            f'<text class="meta attribution source-field" x="{width * 0.91:.1f}" y="{attribution_y:.1f}" '
            f'text-anchor="end" font-size="{width * 0.028:.1f}" fill="{colors["text"]}">'
            f'{html.escape(attribution)}</text>'
        )
    elif direction == "statement":
        background = colors["primary"]
        quote_color = colors["background"]
        # DIRECTION_GEOMETRY["statement"]["inset"] matches the editor's own
        # safe-area guide (.safe-area { inset: 7% } in styles.css); fitting
        # reads the same entry, so text can no longer be sized against a
        # narrower margin than the guide the user actually sees.
        statement_safe = geometry["text_x"]
        poster_lines = statement_visual_lines(lines, width, height)
        strong_rows = statement_strong_rows(poster_lines, styles, emphasis)
        font_size = font_size_override or statement_fitted_font_size(
            poster_lines, strong_rows, width, height
        )
        start_y = geometry["start_y"]
        has_light_logo = bool((brand.get("logo") or {}).get("light_path"))
        logo = "" if logo_mode == "hidden" else logo_image(
            logo_data(brand, manifest_dir, light=True),
            x=statement_safe,
            y=height * 0.055,
            width=width * 0.20,
            filter_value="" if has_light_logo else "brightness(0) invert(1)",
        )
        quote = statement_text_block(
            poster_lines, x=statement_safe, y=start_y, font_size=font_size,
            color=quote_color, emphasis=emphasis, emphasis_color=colors["accent"],
            strong_rows=strong_rows, styles=styles, highlight_color=colors["accent"],
            highlight_text_color=colors["primary"],
        )
        block_height = statement_block_height(font_size, poster_lines, strong_rows)
        # Always the guide's fixed bottom margin, independent of text.
        statement_attribution_y = height * 0.915
        body = (
            f'<rect width="{width}" height="{height}" fill="{background}"/>'
            f'{graphic}{logo}{quote}'
            f'<text class="meta attribution source-field" x="{width * 0.945:.1f}" y="{statement_attribution_y:.1f}" '
            f'text-anchor="end" font-size="{width * 0.028:.1f}" fill="{colors["background"]}">'
            f'{html.escape(attribution)}</text>'
        )
    else:
        background = colors["accent"]
        sheet_x = width * 0.073
        sheet_y = height * 0.061
        sheet_width = width * 0.854
        sheet_height = height * 0.878
        content_x = geometry["text_x"]
        content_right = content_x + geometry["text_width"]
        font_size = font_size_override or fitted_font_size(
            lines, geometry["text_width"], geometry["fit_height"], float(max(width, height)),
            letter_spacing_em=geometry["tracking_em"],
        )
        line_height = font_size * geometry["line_ratio"]
        block_height = line_height * max(0, len(lines) - 1) + font_size
        start_y = geometry["start_y"]
        logo = "" if logo_mode == "hidden" else logo_image(
            logo_data(brand, manifest_dir, light=False),
            x=width * 0.12, y=height * 0.10, width=width * 0.20,
        )
        quote = text_block(
            lines, x=content_x, y=start_y, font_size=font_size, line_height=line_height,
            color=colors["primary"], emphasis=emphasis, emphasis_color=colors["primary"],
            styles=styles, highlight_color=colors["accent"],
            extra_style="font-weight:400;letter-spacing:-0.025em"
        )
        bar_y = start_y - font_size * 0.84
        bar_height = block_height + font_size * 0.16
        # Campo's own composition: SKILL.md lists the single vertical rule
        # as the direction's signature, so it is part of the layout rather
        # than a mark standing in for anything.
        marks = (
            f'<rect class="quote-index" x="{width * 0.12:.1f}" y="{bar_y:.1f}" '
            f'width="{max(8.0, width * 0.008):.1f}" height="{bar_height:.1f}" '
            f'rx="{width * 0.004:.1f}" fill="{colors["primary"]}"/>'
        )
        # Always the guide's fixed bottom margin, independent of text.
        field_attribution_y = height * 0.88
        body = (
            f'<rect width="{width}" height="{height}" fill="{background}"/>'
            f'<rect class="field-sheet" x="{sheet_x:.1f}" y="{sheet_y:.1f}" '
            f'width="{sheet_width:.1f}" height="{sheet_height:.1f}" fill="{colors["background"]}"/>'
            f'{graphic}'
            f'{logo}{marks}'
            f'{quote}'
            f'<text class="meta attribution source-field" x="{content_right:.1f}" y="{field_attribution_y:.1f}" '
            f'text-anchor="end" font-size="{width * 0.028:.1f}" fill="{colors["text"]}">'
            f'{html.escape(attribution)}</text>'
        )

    title = f"Quote card {direction} — {brand['name']}"
    description = f"{content['text']} — {attribution}" if attribution else content["text"]
    source_description = source.get("title") or source.get("label") or source.get("locator")
    if source_description:
        description = f"{description}. Fonte: {source_description}"
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">'
        f'<title id="title">{html.escape(title)}</title><desc id="desc">{html.escape(description)}</desc>'
        f'<style>{css}</style>{body}</svg>\n'
    )


def write_contact_sheet(paths: list[Path], output_path: Path, title: str) -> None:
    cards = "".join(
        f'<figure><img src="{html.escape(path.name, quote=True)}" alt="{html.escape(path.stem)}"><figcaption>{html.escape(path.stem)}</figcaption></figure>'
        for path in paths
    )
    document = f"""<!doctype html>
<html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><style>
body{{margin:0;padding:32px;background:#e9edf0;font-family:system-ui,sans-serif;color:#1d2730}}
h1{{font-size:22px;margin:0 0 24px}}main{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:24px}}
figure{{margin:0;background:white;padding:14px;border-radius:14px;box-shadow:0 8px 24px #0012}}
img{{display:block;width:100%;height:auto}}figcaption{{padding:12px 2px 2px;font-weight:650}}
</style></head><body><h1>{html.escape(title)}</h1><main>{cards}</main></body></html>"""
    output_path.write_text(document, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--all-directions", action="store_true")
    parser.add_argument("--png", choices=("never", "auto", "required"), default="auto")
    parser.add_argument("--node", type=Path)
    parser.add_argument("--node-modules", type=Path)
    args = parser.parse_args(argv)

    try:
        manifest_path = args.manifest.resolve()
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"valid": False, "errors": [{"path": "$", "code": "read", "message": str(exc)}]}, ensure_ascii=False, indent=2))
        return 1

    errors = validate_visual_manifest(data, manifest_path.parent)
    if errors:
        print(json.dumps({"valid": False, "errors": errors}, ensure_ascii=False, indent=2))
        return 1

    args.output_dir.mkdir(parents=True, exist_ok=True)
    directions = DIRECTIONS if args.all_directions else (data["direction"],)
    basename = (data.get("output") or {}).get("basename", "quote-card")
    svg_paths: list[Path] = []
    png_paths: list[Path] = []

    for direction in directions:
        svg_path = args.output_dir / f"{basename}-{direction}.svg"
        svg_path.write_text(render_svg(data, manifest_path.parent, direction), encoding="utf-8")
        svg_paths.append(svg_path)

        if args.png != "never":
            png_path = args.output_dir / f"{basename}-{direction}.png"
            try:
                rasterize.rasterize(
                    svg_path, png_path,
                    data["canvas"]["width"], data["canvas"]["height"],
                    node=args.node, node_modules=args.node_modules,
                )
                png_paths.append(png_path)
            except rasterize.RasterError as error:
                # Report why, rather than the bare "non disponibile" that
                # used to hide the converter's own error message.
                if args.png == "required":
                    print(json.dumps({"valid": False, "errors": [{"path": "output", "code": "png_unavailable", "message": str(error)}]}, ensure_ascii=False, indent=2))
                    return 1

    contact_sheet = None
    if len(svg_paths) > 1:
        contact_sheet = args.output_dir / f"{basename}-directions.html"
        write_contact_sheet(svg_paths, contact_sheet, f"Quote Card Builder — {data['brand']['name']}")

    colors = data["brand"]["colors"]
    qa_report = args.output_dir / f"{basename}-qa.json"
    qa_data = {
        "schema_version": "0.2",
        "status": "passed",
        "state": "prova_visuale_pronta",
        "content_sha256": hashlib.sha256(data["content"]["text"].encode("utf-8")).hexdigest(),
        "checks": {
            "content_approved": True,
            "text_unchanged": True,
            "canvas_4_5": True,
            "width": data["canvas"]["width"],
            "height": data["canvas"]["height"],
            "contrast": {
                "primary_on_background": round(contrast_ratio(colors["primary"], colors["background"]), 2),
                "background_on_primary": round(contrast_ratio(colors["background"], colors["primary"]), 2),
                "accent_on_primary": round(contrast_ratio(colors["accent"], colors["primary"]), 2),
            },
            "directions_rendered": list(directions),
            "visual_inspection_required": True,
        },
        "files": {
            "svg": [str(path) for path in svg_paths],
            "png": [str(path) for path in png_paths],
            "contact_sheet": str(contact_sheet) if contact_sheet else None,
        },
    }
    qa_report.write_text(json.dumps(qa_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result = {
        "valid": True,
        "state": "prova_visuale_pronta",
        "svg": [str(path) for path in svg_paths],
        "png": [str(path) for path in png_paths],
        "contact_sheet": str(contact_sheet) if contact_sheet else None,
        "qa_report": str(qa_report),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
