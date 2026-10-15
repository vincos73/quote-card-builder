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
import random
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
from urban_artwork import XEROX_COLORS, artwork_data_uri, is_xerox
from visual_grammars import (
    cubic_point, demo_compositions, normalize_composition, normalize_grammar_presentation,
)

DIRECTIONS = ("editorial", "statement", "contextual")
GRAPHIC_VARIANTS = {
    "editorial": {"default", "rhythm_lines", "cover", "cutouts", "gradient"},
    "statement": {"default", "modules"},
    "contextual": {"default", "route_map", "constellations"},
}
TRANSFORMATIONS = {"VERBATIM", "EDITED", "PARAPHRASE", "AI_GENERATED"}
EVIDENCE_STATUSES = {"VERIFIED", "USER_SUPPLIED", "UNVERIFIED", "CONFLICT"}
ATTRIBUTION_ROLES = {"speaker", "author", "publisher", "none"}
STYLE_TYPES = {"bold", "italic", "underline", "highlight", "accent", "outline", "size"}
# Hollow-glyph stroke as a fraction of the row's own font size, so the same
# span reads identically at every format's fitted size -- and in a Poster row
# drawn 1.12x larger than its neighbours. Expressed here and resolved to
# absolute user units at draw time: em-relative stroke-width is legal CSS but
# not equally supported across the three rasterisers this project targets.
OUTLINE_STROKE_EM = 0.035
SYSTEM_CARD_FONTS = {"arial"}
# Generous enough for a short descriptive sentence plus a source citation,
# tight enough to keep an accidental essay out of an accessibility field.
ALT_TEXT_MAX_LENGTH = 400
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
COVER_BAND_RATIO = 0.09
# Attribution must remain legible after the 1440px card is scaled down in an
# iframe or social feed. The preferred size is shared by every direction and
# output format; unusually long labels are fitted rather than clipped.
ATTRIBUTION_FONT_SIZE_RATIO = 0.0325
ATTRIBUTION_TRACKING_EM = 0.08


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


def presentation_geometry(
    data: dict[str, Any], direction: str, width: int, height: int,
    vertical_position: str = "center", render_options: dict[str, Any] | None = None,
) -> dict[str, float]:
    """Apply motif-specific reservations without altering the motif itself."""
    geometry = direction_geometry(direction, width, height, vertical_position)
    options = {**(data.get("presentation") or {}), **(render_options or {})}
    if (
        direction == "editorial"
        and options.get("graphic_mode", "auto") != "hidden"
        and options.get("graphic_variant", "default") == "default"
    ):
        left_inset = width * 0.145
        right_inset = width * DIRECTION_GEOMETRY["editorial"]["inset"]
        geometry["text_x"] = left_inset
        geometry["text_width"] = width - left_inset - right_inset
    if (cutouts_enabled(direction, options) and options.get("logo_mode", "auto") != "hidden"
            and data.get("brand", {}).get("logo")):
        geometry["start_y"] += height * 0.08
    return geometry


def graphic_variant_allowed(direction: str, variant: str) -> bool:
    """Return whether a motif belongs to the selected visual direction."""

    return variant in GRAPHIC_VARIANTS.get(direction, set())


def graphic_seed_allowed(seed: Any) -> bool:
    return isinstance(seed, int) and not isinstance(seed, bool) and 0 <= seed <= 999999


def cover_enabled(direction: str, presentation: dict[str, Any]) -> bool:
    return (direction == "editorial" and presentation.get("graphic_variant") == "cover"
            and presentation.get("graphic_mode", "auto") != "hidden")


def cover_layout(height: int) -> dict[str, float]:
    """Shared reservations for the two bands, logo and attribution."""
    return {"band_height": height * COVER_BAND_RATIO, "logo_y": height * 0.12,
            "text_top": height * 0.12, "text_bottom": height * 0.80,
            "attribution_y": height * 0.865}


def cutouts_layout(height: int) -> dict[str, float]:
    """Text reservations matching the clear center of Cutouts."""
    return {"text_top": height * 0.23, "text_bottom": height * 0.84}


def cutouts_enabled(direction: str, presentation: dict[str, Any]) -> bool:
    return (direction == "editorial" and presentation.get("graphic_variant") == "cutouts"
            and presentation.get("graphic_mode", "auto") != "hidden")


def cover_logo_width(width: int, height: int, aspect_ratio: float) -> float:
    """Keep tall logos inside Cover's header reservation."""
    return min(width * 0.21, height * 0.08 * aspect_ratio)


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
        expected = {"start", "end", "type", "scale"} if isinstance(style, dict) and style.get("type") == "size" else {"start", "end", "type"}
        if not isinstance(style, dict) or set(style) != expected:
            add_error(errors, item_path, "shape", "Ogni intervallo richiede start, end e type.")
            continue
        start, end, kind = style.get("start"), style.get("end"), style.get("type")
        if not isinstance(start, int) or isinstance(start, bool) or not isinstance(end, int) or isinstance(end, bool):
            add_error(errors, item_path, "offset", "Start ed end devono essere interi.")
        elif not 0 <= start < end <= len(text):
            add_error(errors, item_path, "range", "L'intervallo deve ricadere nel testo corrente.")
        if not isinstance(kind, str) or kind not in STYLE_TYPES:
            add_error(errors, f"{item_path}.type", "enum", "Usare bold, italic, underline, highlight, accent, outline o size.")
        if kind == "size":
            scale = style.get("scale")
            if (not isinstance(scale, (int, float)) or isinstance(scale, bool)
                    or not math.isfinite(scale) or not .5 <= scale <= 2.5):
                add_error(errors, f"{item_path}.scale", "range", "Usare una scala da 0.5 a 2.5.")


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
        or not lines
        or any(not isinstance(line, str) for line in lines if isinstance(lines, list))
        or (isinstance(lines, list) and not any(line.strip() for line in lines if isinstance(line, str)))
    ):
        add_error(
            errors,
            "content.lines",
            "lines",
            "Inserire almeno una riga di testo.",
        )
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

    if "alt_text" in content:
        alt_text = content.get("alt_text")
        if not isinstance(alt_text, str):
            add_error(errors, "content.alt_text", "type", "Deve essere una stringa.")
        elif len(alt_text) > ALT_TEXT_MAX_LENGTH:
            add_error(errors, "content.alt_text", "length", f"Non può superare {ALT_TEXT_MAX_LENGTH} caratteri.")

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
    if isinstance(width, int) and isinstance(height, int):
        ratio = width / height
        if not any(math.isclose(ratio, expected, rel_tol=0.001) for expected in (4 / 5, 1.0)):
            add_error(errors, "canvas", "ratio", "Il renderer accetta soltanto i rapporti 4:5 o 1:1.")

    direction = root.get("direction")
    if direction not in DIRECTIONS:
        add_error(errors, "direction", "enum", "Direzione non ammessa.")

    presentation = root.get("presentation", {})
    if not isinstance(presentation, dict):
        add_error(errors, "presentation", "type", "La presentazione deve essere un oggetto.")
    else:
        try:
            normalize_grammar_presentation(presentation)
        except ValueError as error:
            add_error(errors, "presentation.composition", "grammar", str(error))
        if presentation.get("visual_grammar") not in {"ribbons", "urban"} and any(
            isinstance(style, dict) and style.get("type") == "size"
            for style in (styles if isinstance(styles, list) else [])
        ):
            add_error(errors, "content.styles", "grammar", "La dimensione locale richiede una grammatica visuale.")
        if not graphic_seed_allowed(presentation.get("graphic_seed", 0)):
            add_error(errors, "presentation.graphic_seed", "range", "Usare un seed intero da 0 a 999999.")
        graphic_mode = presentation.get("graphic_mode", "auto")
        if graphic_mode not in {"auto", "hidden"}:
            add_error(errors, "presentation.graphic_mode", "enum", "Usare auto o hidden.")
        graphic_variant = presentation.get("graphic_variant", "default")
        if not isinstance(graphic_variant, str) or not graphic_variant_allowed(direction, graphic_variant):
            add_error(
                errors,
                "presentation.graphic_variant",
                "enum",
                "Il motivo non appartiene alla direzione selezionata.",
            )

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
        # Validate the selected composition rather than rejecting a brand for
        # a colour pair that this card never paints. Editorial/Gradient uses
        # its full-field surface, checked conservatively below.
        graphic_variant = presentation.get("graphic_variant", "default") if isinstance(presentation, dict) else "default"
        if isinstance(presentation, dict) and presentation.get("visual_grammar") in {"ribbons", "urban"}:
            composition = presentation.get("composition") or {}
            foreground = colors.get(composition.get("text_role", "text"), colors["text"])
            background = colors.get(composition.get("background_role", "background"), colors["background"])
            checks = {"ribbons_text": (foreground, background)}
        elif (direction == "editorial" and graphic_variant == "gradient"
                and presentation.get("graphic_mode", "auto") != "hidden"):
            checks: dict[str, tuple[str, str]] = {}
            safety = gradient_render_safety(
                brand, manifest_dir,
                logo_mode=presentation.get("logo_mode", "auto"),
            )
            if not safety["passed"]:
                add_error(
                    errors, "presentation.graphic_variant", "gradient_contrast",
                    "Il gradiente non garantisce contrasto su tutta la superficie o sul logo.",
                )
        elif direction == "statement":
            checks = {
                "statement_text": (colors["background"], colors["primary"]),
                "statement_emphasis": (colors["accent"], colors["primary"]),
            }
        elif direction == "contextual":
            checks = {
                "contextual_text": (colors["primary"], colors["background"]),
                "contextual_graphic": (colors["primary"], colors["accent"]),
            }
        else:
            checks = {"editorial_text": (colors["primary"], colors["background"])}
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
        ("bold_italic_path", 700, "italic"),
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


def gradient_logo_ink_colours(
    brand: dict[str, Any], manifest_dir: Path, *, logo_mode: str = "auto",
) -> tuple[list[str], str]:
    """Read flat SVG logo paints for Gradient's full-field contrast check."""
    if logo_mode == "hidden" or not (brand.get("logo") or {}):
        return [], "not_present"
    logo = brand.get("logo") or {}
    value = logo.get("dark_path") or logo.get("light_path")
    if not value:
        return [], "not_present"
    path = resolve_asset(value, manifest_dir)
    if path.suffix.lower() != ".svg":
        return [], "unverifiable_raster_logo"
    try:
        root = ET.fromstring(path.read_text(encoding="utf-8"))
    except (ET.ParseError, OSError, UnicodeDecodeError):
        return [], "unverifiable_svg_logo"
    paints: set[str] = set()
    unresolved = False
    for element in root.iter():
        tag = element.tag.rsplit("}", 1)[-1]
        if tag in {"style", "image", "use", "filter", "mask", "pattern", "linearGradient", "radialGradient"}:
            unresolved = True
        for opacity_key in ("opacity", "fill-opacity", "stroke-opacity"):
            opacity = element.attrib.get(opacity_key)
            if opacity is not None and opacity.strip() not in {"1", "1.0", "100%"}:
                unresolved = True
        if element.attrib.get("filter") or element.attrib.get("mask") or element.attrib.get("clip-path"):
            unresolved = True
        style = element.attrib.get("style", "")
        for key, value in re.findall(r"([\w-]+)\s*:\s*([^;]+)", style):
            key, value = key.lower(), value.strip()
            if key in {"opacity", "fill-opacity", "stroke-opacity"} and value not in {"1", "1.0", "100%"}:
                unresolved = True
            if key in {"filter", "mask", "clip-path"}:
                unresolved = True
        for key in ("fill", "stroke"):
            value = element.attrib.get(key, "").strip()
            if HEX_COLOR.fullmatch(value):
                paints.add(value.upper())
            elif value and value.lower() not in {"none", "transparent"}:
                unresolved = True
        for value in re.findall(r"(?:fill|stroke)\s*:\s*([^;\s]+)", style, flags=re.IGNORECASE):
            if HEX_COLOR.fullmatch(value):
                paints.add(value.upper())
            elif value.lower() not in {"none", "transparent"}:
                unresolved = True
        if tag in {"path", "rect", "circle", "ellipse", "polygon", "polyline", "text"}:
            has_paint = any(key in element.attrib for key in ("fill", "stroke")) or bool(
                re.search(r"(?:fill|stroke)\s*:", style, flags=re.IGNORECASE)
            )
            if not has_paint:
                unresolved = True
    if unresolved or not paints:
        return sorted(paints), "unverifiable_svg_logo"
    return sorted(paints), "verified_svg_logo"


def gradient_ink_colours(
    brand: dict[str, Any], manifest_dir: Path, *, logo_mode: str = "auto",
) -> tuple[list[str], str]:
    logo_inks, status = gradient_logo_ink_colours(brand, manifest_dir, logo_mode=logo_mode)
    return [brand["colors"]["primary"].upper(), brand["colors"]["text"].upper(), *logo_inks], status


def gradient_render_safety(
    brand: dict[str, Any], manifest_dir: Path, *, logo_mode: str = "auto",
) -> dict[str, Any]:
    inks, logo_status = gradient_ink_colours(brand, manifest_dir, logo_mode=logo_mode)
    report = gradient_contrast_report(brand["colors"], inks)
    return {**report, "logo_status": logo_status,
            "passed": report["passed"] and logo_status not in {"unverifiable_raster_logo", "unverifiable_svg_logo"}}


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
    # Authored hard breaks are unbounded. Keep a tiny positive floor only so
    # pathological but text-length-bounded input still produces valid SVG;
    # ordinary copy remains governed by the width/height max-fit above.
    return max(1, min(maximum, width_size, height_size))


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

    # A hard break is authored content: it cannot be merged to satisfy the
    # preferred poster row count. In particular, more hard rows than the
    # preferred maximum used to make the widening loop impossible to satisfy.
    target_rows = max(maximum_rows, len(lines))
    visual = wrap(target_units)
    for _ in range(64):
        if len(visual) <= target_rows:
            return visual
        target_units *= 1.12
        visual = wrap(target_units)

    # Deterministic safety net for pathological input: disable soft wrapping
    # while preserving every user-authored hard row exactly and always terminate.
    return list(lines)


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
    # Manifesto starts neutral. Accent is an explicit editorial treatment,
    # never a direction-owned default: a user should be able to switch to
    # Poster without seeing an unrequested word recoloured.
    if direction == "statement":
        return []
    span = default_emphasis_span(text)
    if span is None:
        return []
    start, end = span
    style_type = "bold" if direction == "editorial" else "highlight"
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
    return max(1, min(width * 0.12, height_limit, *width_limits))


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
            # Give the marker a small overshoot on both sides. Without a
            # leading pad, antialiasing can leave the first glyph visibly
            # outside the highlight, especially for italic or outlined text.
            width += row_size * 0.18
            side_pad = row_size * 0.06
            start_x -= side_pad
            width += side_pad * 2
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
        # Row strength controls scale only. Colour belongs to the exact
        # selected span emitted by styled_lines/emphasized_lines; colouring
        # the whole strong row made ordinary bold text look accented.
        fill = color
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


GRADIENT_TEXT_CONTRAST = 4.5


def _mix_color(first: str, second: str, amount: float) -> str:
    amount = max(0.0, min(1.0, amount))
    channels = [round(a + (b - a) * amount) for a, b in zip(parse_hex(first), parse_hex(second))]
    return "#" + "".join(f"{value:02X}" for value in channels)


def _gradient_contrast_bound(colours: list[str], inks: list[str]) -> dict[str, Any]:
    channels = [parse_hex(colour) for colour in colours]
    lower = "#" + "".join(f"{min(values):02X}" for values in zip(*channels))
    upper = "#" + "".join(f"{max(values):02X}" for values in zip(*channels))
    lower_luminance, upper_luminance = relative_luminance(lower), relative_luminance(upper)
    ratios: dict[str, float] = {}
    for ink in inks:
        ink_luminance = relative_luminance(ink)
        if lower_luminance <= ink_luminance <= upper_luminance:
            ratios[ink] = 1.0
        else:
            ratios[ink] = min(contrast_ratio(ink, lower), contrast_ratio(ink, upper))
    return {
        "lower": lower,
        "upper": upper,
        "ratios": ratios,
        "minimum": min(ratios.values()),
        "passed": all(value >= GRADIENT_TEXT_CONTRAST for value in ratios.values()),
    }


def _most_contrasting_surface(inks: list[str], background: str) -> str:
    extremes = ("#FFFFFF", "#000000")
    target = max(extremes, key=lambda colour: min(contrast_ratio(ink, colour) for ink in inks))
    maximum = min(contrast_ratio(ink, target) for ink in inks)
    desired = min(6.0, max(GRADIENT_TEXT_CONTRAST, maximum - 0.08))
    if _gradient_contrast_bound([background], inks)["minimum"] >= desired:
        return background.upper()
    low, high = 0.0, 1.0
    for _ in range(24):
        middle = (low + high) / 2
        candidate = _mix_color(background, target, middle)
        if _gradient_contrast_bound([candidate], inks)["minimum"] >= desired:
            high = middle
        else:
            low = middle
    return _mix_color(background, target, high)


def _gradient_safe_tint(candidate: str, base: str, inks: list[str], accepted: list[str]) -> str:
    if _gradient_contrast_bound([base, *accepted, candidate], inks)["passed"]:
        return candidate.upper()
    low, high = 0.0, 1.0
    for _ in range(24):
        middle = (low + high) / 2
        tint = _mix_color(base, candidate, middle)
        if _gradient_contrast_bound([base, *accepted, tint], inks)["passed"]:
            low = middle
        else:
            high = middle
    return _mix_color(base, candidate, low)


def gradient_palette(colors: dict[str, str], ink_colours: list[str] | None = None) -> dict[str, str]:
    inks = [colour.upper() for colour in (ink_colours or [colors["primary"]])]
    base = _most_contrasting_surface(inks, colors["background"].upper())
    bridge_source = _mix_color(colors["primary"], colors["accent"], 0.50)
    sky_limit = _gradient_safe_tint(colors["accent"].upper(), base, inks, [])
    sky = _mix_color(base, sky_limit, 0.82)
    bloom_limit = _gradient_safe_tint(colors["primary"].upper(), base, inks, [sky])
    bloom = _mix_color(base, bloom_limit, 0.28)
    bridge_limit = _gradient_safe_tint(bridge_source, base, inks, [sky, bloom])
    bridge = _mix_color(base, bridge_limit, 0.34)
    return {"base": base, "sky": sky, "bloom": bloom, "bridge": bridge}


def gradient_contrast_report(colors: dict[str, str], ink_colours: list[str] | None = None) -> dict[str, Any]:
    inks = [colour.upper() for colour in (ink_colours or [colors["primary"]])]
    palette = gradient_palette(colors, inks)
    bound = _gradient_contrast_bound(list(palette.values()), inks)
    return {
        "inks": inks,
        "floor": GRADIENT_TEXT_CONTRAST,
        "colours": palette,
        "envelope": {"lower": bound["lower"], "upper": bound["upper"]},
        "ratios": {ink: round(value, 2) for ink, value in bound["ratios"].items()},
        "minimum": round(bound["minimum"], 2),
        "passed": bound["passed"],
    }


def gradient_graphic(
    width: int, height: int, colors: dict[str, str], seed: int, *, ink_colours: list[str] | None = None,
    logo_status: str = "not_present",
) -> str:
    entropy = _graphic_entropy(seed, "gradient")
    inks = [colour.upper() for colour in (ink_colours or [colors["primary"]])]
    palette = gradient_palette(colors, inks)
    identifier = hashlib.sha256(
        f"gradient-v1:{seed}:{width}:{height}:{','.join(palette.values())}".encode("ascii")
    ).hexdigest()[:12]
    field_count = 2 + entropy[0] % 2
    angle = -34 + entropy[1] / 255 * 68
    base_angle = 18 + entropy[2] / 255 * 38
    centers = [
        (0.10 + entropy[3] / 255 * 0.38, -0.04 + entropy[4] / 255 * 0.36),
        (0.50 + entropy[5] / 255 * 0.42, 0.54 + entropy[6] / 255 * 0.42),
        (0.26 + entropy[7] / 255 * 0.50, 0.28 + entropy[8] / 255 * 0.42),
    ]
    radii = [0.50 + entropy[9] / 255 * 0.36, 0.54 + entropy[10] / 255 * 0.38,
             0.38 + entropy[11] / 255 * 0.36]
    field_names = ("sky", "bloom", "bridge")
    definitions = [
        f'<linearGradient id="gradient-base-{identifier}" x1="0" y1="0" x2="1" y2="1" '
        f'gradientTransform="rotate({base_angle:.1f} .5 .5)"><stop offset="0" stop-color="{palette["base"]}"/>'
        f'<stop offset="1" stop-color="{_mix_color(palette["base"], palette["sky"], 0.22)}"/></linearGradient>'
    ]
    fields: list[str] = []
    for index in range(field_count):
        name = field_names[index]
        cx, cy = centers[index]
        radius = radii[index]
        field_id = f"gradient-field-{index}-{identifier}"
        rotation = angle + (entropy[12 + index] / 255 - .5) * 24
        middle = _mix_color(palette[name], palette["base"], 0.38 + entropy[15 + index] / 255 * .18)
        definitions.append(
            f'<radialGradient id="{field_id}" cx="{cx:.3f}" cy="{cy:.3f}" r="{radius:.3f}" '
            f'gradientTransform="rotate({rotation:.1f} .5 .5)"><stop offset="0" stop-color="{palette[name]}"/>'
            f'<stop offset="0.48" stop-color="{middle}" stop-opacity="{0.50 + entropy[18 + index] / 255 * .26:.3f}"/>'
            f'<stop offset="1" stop-color="{palette["base"]}" stop-opacity="0"/></radialGradient>'
        )
        fields.append(
            f'<rect class="gradient-field gradient-field--{name}" width="{width}" height="{height}" '
            f'fill="url(#{field_id})"/>'
        )
    return (
        f'<g class="direction-graphic direction-graphic--gradient" data-generator="gradient-v1" '
        f'data-seed="{seed}" data-field-count="{field_count}" data-gradient-inks="{",".join(inks)}" '
        f'data-gradient-floor="{GRADIENT_TEXT_CONTRAST:.1f}" data-gradient-logo-status="{logo_status}"><defs>{"".join(definitions)}</defs>'
        f'<rect class="gradient-surface" width="{width}" height="{height}" fill="url(#gradient-base-{identifier})"/>'
        f'{"".join(fields)}</g>'
    )


def cover_graphic(width: int, height: int, colors: dict[str, str], seed: int) -> str:
    """Cover v1: stable normalized mosaics, shared across all aspect ratios.

    Keep this algorithm version intact for saved cards. A future visual
    grammar should use a new variant ID rather than reinterpret these seeds.
    """
    entropy = hashlib.sha256(f"quote-cover-v1:{seed}".encode("ascii")).digest()
    palette = [colors["primary"], colors["accent"], colors["background"]]
    weights = [8 + value % 12 for value in entropy[:6]]
    total = sum(weights)
    band_height = cover_layout(height)["band_height"]
    parts = []
    for band in range(2):
        y = 0.0 if band == 0 else height - band_height
        parts.append(f'<rect class="cover-band" x="0" y="{y:.3f}" width="{width}" '
                     f'height="{band_height:.3f}" fill="{colors["background"]}"/>')
        x = 0.0
        order = range(6) if band == 0 else reversed(range(6))
        for index in order:
            right = x + width * weights[index] / total
            split = (entropy[6 + index + band * 6] % 4) / 3
            first = (index + entropy[18 + band]) % 3
            second = (first + 1 + entropy[20 + index] % 2) % 3
            for top, fraction, color in ((0, split, first), (split, 1 - split, second)):
                if fraction:
                    parts.append(f'<rect class="cover-tile" x="{x:.3f}" y="{y + top * band_height:.3f}" '
                                 f'width="{right - x:.3f}" height="{fraction * band_height:.3f}" '
                                 f'fill="{palette[color]}"/>')
            x = right
    return (f'<g class="direction-graphic direction-graphic--cover" '
            f'data-generator="cover-v1" data-seed="{seed}">' + "".join(parts) + '</g>')


def _graphic_entropy(seed: int, label: str) -> bytes:
    return hashlib.sha256(f"quote-{label}-v1:{seed}".encode("ascii")).digest()


def cutouts_graphic(width: int, height: int, colors: dict[str, str], seed: int) -> str:
    """Flat, asymmetric edge polygons with a clear ivory center."""
    entropy = _graphic_entropy(seed, "cutouts")
    accent = colors["accent"]
    primary = colors["primary"]
    right = width
    bottom = height
    polys = [
        ((0, 0), (width * (.24 + entropy[0] / 1400), 0),
         (width * (.08 + entropy[1] / 3000), height * (.07 + .10 * entropy[2] / 255)), (0, height * (.09 + .09 * entropy[3] / 255))),
        ((right, 0), (right - width * (.58 + entropy[4] / 1800), 0),
         (right - width * (.18 + entropy[5] / 1800), height * (.12 + .08 * entropy[6] / 255)),
         (right, height * (.14 + .08 * entropy[7] / 255))),
        ((right, bottom), (right - width * (.25 + entropy[8] / 1500), bottom),
         (right - width * (.15 + entropy[9] / 1800), height * (.88 + .07 * entropy[10] / 255)),
         (right, height * (.84 + .07 * entropy[11] / 255))),
    ]
    fills = (accent, primary, accent)
    elements = []
    for index, points in enumerate(polys):
        point_string = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
        elements.append(f'<polygon class="cutout cutout--{index + 1}" points="{point_string}" fill="{fills[index]}"/>')
    return (f'<g class="direction-graphic direction-graphic--cutouts" '
            f'data-generator="cutouts-v1" data-seed="{seed}">' + "".join(elements) + '</g>')


def constellations_graphic(width: int, height: int, colors: dict[str, str], seed: int) -> str:
    """Sparse diagonal node networks tucked into the two opposite corners."""
    entropy = _graphic_entropy(seed, "constellations")
    stroke = colors["primary"]
    radius = max(3.0, width * .004)
    groups = []
    for corner, mirror in (("top", False), ("bottom", True)):
        offset = 0 if not mirror else 16
        base_x, base_y = width * .84, height * .06
        points = [(base_x, base_y), (width * (.90 + entropy[offset] / 5000), height * (.12 + entropy[offset + 1] / 5000)),
                  (width * (.78 + entropy[offset + 2] / 5000), height * (.16 + entropy[offset + 3] / 5000)),
                  (width * (.91 + entropy[offset + 4] / 5000), height * (.21 + entropy[offset + 5] / 5000)),
                  (width * (.84 + entropy[offset + 6] / 5000), height * (.25 + entropy[offset + 7] / 5000)),
                  (width * (.96 - entropy[offset + 8] / 5000), height * (.07 + entropy[offset + 9] / 5000)),
                  (width * (.74 + entropy[offset + 10] / 5000), height * (.08 + entropy[offset + 11] / 5000)),
                  (width * (.95 - entropy[offset + 12] / 6000), height * (.28 + entropy[offset + 13] / 6000))]
        if mirror:
            points = [(width - x, height - y) for x, y in points]
        topology = entropy[offset + 14] % 4
        edges = (((0, 1), (1, 2), (2, 3), (3, 4), (4, 5)) if topology == 0 else
                 ((0, 1), (0, 2), (1, 3), (1, 4), (2, 5)) if topology == 1 else
                 ((0, 1), (1, 2), (2, 0), (2, 3), (3, 4), (4, 6)) if topology == 2 else
                 ((0, 1), (1, 2), (1, 3), (1, 4), (1, 5), (5, 6)))
        count = max(b for _, b in edges) + 1
        points = points[:count]
        lines = "".join(f'<path class="constellation-line" d="M {points[a][0]:.1f} {points[a][1]:.1f} L {points[b][0]:.1f} {points[b][1]:.1f}"/>' for a, b in edges)
        nodes = "".join(f'<circle class="constellation-node" cx="{x:.1f}" cy="{y:.1f}" r="{max(radius, width * (.007 + entropy[offset + index] / 30000)):.1f}" fill="{stroke}" stroke="none"/>' for index, (x, y) in enumerate(points))
        groups.append(f'<g class="constellation constellation--{corner}">{lines}{nodes}</g>')
    return (f'<g class="direction-graphic direction-graphic--constellations" fill="none" '
            f'stroke="{stroke}" stroke-width="{max(2.0, width * .002):.1f}" stroke-linecap="round" '
            f'data-generator="constellations-v1" data-seed="{seed}">' + "".join(groups) + '</g>')


def direction_graphic(
    direction: str, *, width: int, height: int, colors: dict[str, str], enabled: bool,
    variant: str = "default", seed: int = 0, gradient_inks: list[str] | None = None,
    gradient_logo_status: str = "not_present",
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
    if direction == "editorial" and variant == "cover":
        return cover_graphic(width, height, colors, seed)
    if direction == "editorial" and variant == "cutouts":
        return cutouts_graphic(width, height, colors, seed)
    if direction == "editorial" and variant == "gradient":
        return gradient_graphic(width, height, colors, seed, ink_colours=gradient_inks,
                                logo_status=gradient_logo_status)
    if direction == "editorial":
        # The page itself is `colors["background"]`; pick whichever brand
        # color actually reads against it instead of assuming accent does.
        stroke_color = legible_color(colors["accent"], colors["primary"], colors["background"])
        if variant == "rhythm_lines":
            stroke_width = max(2.0, width * 0.0022)
            rules: list[str] = []
            for index in range(5):
                top_y = height * (-0.006 + index * 0.018)
                top_x = width * (0.70 + index * 0.026)
                bottom_y = height * (0.925 + index * 0.018)
                bottom_end = width * (0.24 - index * 0.026)
                rules.append(
                    f'<path class="rhythm-rule rhythm-rule--top" d="M {top_x:.1f} {top_y:.1f} H {width * 1.02:.1f}"/>'
                )
                rules.append(
                    f'<path class="rhythm-rule rhythm-rule--bottom" d="M {-width * 0.02:.1f} {bottom_y:.1f} H {bottom_end:.1f}"/>'
                )
            return (
                '<g class="direction-graphic direction-graphic--rhythm" fill="none" '
                f'stroke="{stroke_color}" stroke-width="{stroke_width:.1f}">{"".join(rules)}</g>'
            )
        paths: list[str] = []
        entropy = _graphic_entropy(seed, "contours") if seed else None
        for index in range(6):
            # These are the exact pre-1.3 Contours coordinates. Their natural
            # canvas crop is part of the original visual, not a mask.
            top_x = width * (0.89 + index * 0.026)
            top_y = -height * 0.07 + index * height * 0.018
            if entropy:
                top_x += width * ((entropy[index] / 255 - .5) * .018)
                top_y += height * ((entropy[index + 6] / 255 - .5) * .035)
            paths.append(
                f'<path class="contour-path contour-path--top" d="M {top_x:.1f} {top_y:.1f} '
                f'C {top_x - width * (0.12 + (entropy[index + 12] / 255 - .5) * .025 if entropy else .12):.1f} {top_y + height * 0.05:.1f}, '
                f'{top_x - width * 0.15:.1f} {top_y + height * 0.14:.1f}, '
                f'{top_x - width * 0.07:.1f} {top_y + height * 0.21:.1f} '
                f'S {top_x + width * 0.055:.1f} {top_y + height * 0.29:.1f}, '
                f'{top_x:.1f} {top_y + height * 0.39:.1f}"/>'
            )
            bottom_y = height * (0.67 + index * 0.019)
            if entropy:
                bottom_y += height * ((entropy[index + 18] / 255 - .5) * .035)
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
        if variant == "modules":
            accent = colors["accent"]
            modules = (
                f'<rect class="poster-module poster-module--top" x="{width * 0.82:.1f}" y="{-height * 0.015:.1f}" '
                f'width="{width * 0.055:.1f}" height="{height * 0.075:.1f}"/>'
                f'<rect class="poster-module poster-module--top" x="{width * 0.90:.1f}" y="{height * 0.055:.1f}" '
                f'width="{width * 0.055:.1f}" height="{height * 0.055:.1f}"/>'
                f'<rect class="poster-module poster-module--top" x="{width * 0.97:.1f}" y="{-height * 0.01:.1f}" '
                f'width="{width * 0.065:.1f}" height="{height * 0.075:.1f}"/>'
                f'<rect class="poster-module poster-module--top" x="{width * 0.90:.1f}" y="{height * 0.125:.1f}" '
                f'width="{width * 0.055:.1f}" height="{height * 0.055:.1f}"/>'
                f'<rect class="poster-module poster-module--bottom" x="{-width * 0.015:.1f}" y="{height * 0.86:.1f}" '
                f'width="{width * 0.075:.1f}" height="{height * 0.055:.1f}"/>'
                f'<rect class="poster-module poster-module--bottom" x="{width * 0.075:.1f}" y="{height * 0.80:.1f}" '
                f'width="{width * 0.055:.1f}" height="{height * 0.065:.1f}"/>'
                f'<rect class="poster-module poster-module--bottom" x="{width * 0.075:.1f}" y="{height * 0.875:.1f}" '
                f'width="{width * 0.055:.1f}" height="{height * 0.055:.1f}"/>'
                f'<rect class="poster-module poster-module--bottom" x="{width * 0.145:.1f}" y="{height * 0.94:.1f}" '
                f'width="{width * 0.06:.1f}" height="{height * 0.075:.1f}"/>'
            )
            return (
                '<g class="direction-graphic direction-graphic--modules" '
                f'fill="{accent}">{modules}</g>'
            )
        # Concentric rings radiating from two opposite corners, like an
        # echo/ripple. Stroke width tapers outward (never opacity) to read
        # as a fade while every ring stays a full-opacity brand color.
        ring_color = colors["accent"]
        corners = [(width, 0.0), (0.0, height)]
        ring_count = 4
        entropy = _graphic_entropy(seed, "echo") if seed else None
        base_radius = width * 0.05
        step = width * 0.07
        max_stroke = width * 0.016
        min_stroke = max(2.0, width * 0.003)
        rings: list[str] = []
        for cx, cy in corners:
            for i in range(ring_count):
                radius = base_radius + i * step
                if entropy:
                    radius *= 0.90 + entropy[(i + (0 if cx else 8)) % len(entropy)] / 255 * .20
                fade = i / (ring_count - 1)
                stroke = max_stroke + (min_stroke - max_stroke) * fade
                rings.append(
                    f'<circle class="echo-ring" cx="{cx:.1f}" cy="{cy:.1f}" r="{radius:.1f}" '
                    f'fill="none" stroke="{ring_color}" stroke-width="{stroke:.1f}"/>'
                )
        return '<g class="direction-graphic direction-graphic--echo">' + "".join(rings) + '</g>'
    if variant == "constellations":
        return constellations_graphic(width, height, colors, seed)
    # Contextual/Frame: dots sit over the accent field; "statement_emphasis"
    # already guarantees primary reads at >=4.5:1 against accent, so draw
    # them at full opacity rather than blending a third hue.
    if variant == "route_map":
        stroke_color = colors["primary"]
        stroke_width = max(2.0, width * 0.0022)
        radius = max(3.0, width * 0.0045)
        # Draw one route corner and rotate that exact geometry into the
        # opposite corner.  Keeping a single source shape avoids the visual
        # drift that used to make the lower-left route look unrelated to the
        # upper-right one, especially on square canvases.
        corner_paths = (
            f'<path class="route-line route-line--top" d="M {width * 0.79:.1f} {height * 0.03:.1f} '
            f'H {width * 0.94:.1f} V {height * 0.12:.1f} H {width * 1.02:.1f}"/>'
            f'<path class="route-line route-line--top" d="M {width * 0.87:.1f} {-height * 0.01:.1f} '
            f'V {height * 0.075:.1f} Q {width * 0.87:.1f} {height * 0.105:.1f} '
            f'{width * 0.90:.1f} {height * 0.105:.1f} H {width * 1.02:.1f}"/>'
        )
        corner_nodes = "".join(
            f'<circle class="route-node" cx="{x * width:.1f}" cy="{y * height:.1f}" r="{radius:.1f}"/>'
            for x, y in ((0.94, 0.03), (0.94, 0.12), (0.87, 0.075))
        )
        corner = f'{corner_paths}<g class="route-nodes" fill="{stroke_color}" stroke="none">{corner_nodes}</g>'
        opposite_corner_transform = f'rotate(180 {width / 2:.1f} {height / 2:.1f})'
        return (
            '<g class="direction-graphic direction-graphic--routes" fill="none" '
            f'stroke="{stroke_color}" stroke-width="{stroke_width:.1f}" stroke-linecap="round" '
            f'stroke-linejoin="round"><g class="route-corner route-corner--top">{corner}</g>'
            f'<g class="route-corner route-corner--bottom" transform="{opposite_corner_transform}">'
            f'{corner}</g></g>'
        )
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


def default_alt_text(text: str, attribution: str, source: dict[str, Any] | None = None) -> str:
    """The same accessible description render_svg has always embedded in
    <desc>, factored out so the editor and the production pack can propose
    it as a suggestion instead of only ever seeing it baked into an SVG.
    """
    description = f"{text} — {attribution}" if attribution else text
    source = source or {}
    source_description = source.get("title") or source.get("label") or source.get("locator")
    if source_description:
        separator = " " if re.search(r"[.!?…][\"'»”’)]*$", description.rstrip()) else ". "
        description = f"{description}{separator}Fonte: {source_description}"
    return description


def measured_text_width(text: str, font_size: float, *, letter_spacing_em: float = 0.0) -> float:
    """Rendered pixel width of ``text`` at ``font_size``, tracking included --
    the same estimate ``fitted_font_size`` and ``highlight_rects`` use, so a
    mark or rule anchored with this lines up with what actually gets drawn.
    """
    return visual_units(text) * font_size + letter_spacing_em * font_size * max(0, len(text) - 1)


def attribution_font_size(text: str, width: int, available_width: float) -> float:
    """Prefer a readable attribution size and fit long labels to their lane."""
    preferred = width * ATTRIBUTION_FONT_SIZE_RATIO
    if not text:
        return preferred
    unit_width = measured_text_width(text, 1.0, letter_spacing_em=ATTRIBUTION_TRACKING_EM)
    fitted = min(preferred, available_width / max(unit_width, 1e-6))
    # SVG serializes this value to one decimal. Floor to that precision so a
    # rounded-up tenth cannot put the final glyph fractionally outside the lane.
    return math.floor(fitted * 10) / 10


def last_text_line(lines: list[str]) -> str:
    return next((line for line in reversed(lines) if line), "")


def _pixel_box(box: dict[str, float], width: int, height: int) -> dict[str, float]:
    return {"x": box["x"] * width, "y": box["y"] * height,
            "width": box["width"] * width, "height": box["height"] * height}


def _ribbon_face_metrics(font: dict[str, Any], manifest_dir: Path) -> dict[str, dict[str, float] | None]:
    """Load each painted face, rather than measuring bold with regular ink."""
    faces: dict[str, dict[str, float] | None] = {}
    for key, field in (("regular", "regular_path"), ("bold", "bold_path"), ("italic", "italic_path")):
        candidates = [resolve_asset(font[field], manifest_dir)] if font.get(field) else []
        if key == "regular":
            candidates.extend(_system_font_candidates(font.get("family", "")))
        elif key == "bold":
            candidates.extend(_system_bold_font_candidates(font.get("family", "")))
        faces[key] = _resolve_char_widths(candidates)
    return faces


def _ribbon_rows(
    text: str, styles: list[dict[str, Any]], font_size: float, box: dict[str, float],
    faces: dict[str, dict[str, float] | None], hard_lines: list[str] | None = None,
    *, tracking: float = QUOTE_TRACKING_EM, uppercase: bool = False,
) -> list[dict[str, Any]]:
    """Word wrap the actual styled advances and assign variable baselines.

    A fragment owns its exact canonical offsets, measurement and size.
    Its highlight is generated from that fragment after the final wrapping.
    """
    chars: list[dict[str, Any]] = []
    for offset, char in enumerate(text):
        active = [style for style in styles if style["start"] <= offset < style["end"]]
        types = {style["type"] for style in active}
        scale = next((float(style["scale"]) for style in reversed(active) if style["type"] == "size"), 1.0)
        size = font_size * scale
        face = "bold" if "bold" in types else "italic" if "italic" in types else "regular"
        metrics = faces.get(face) or faces.get("regular")
        painted = char.upper() if uppercase else char
        advance = sum((metrics.get(glyph, metrics.get(" ", .28) if glyph.isspace() else .6)
                       if metrics else visual_units(glyph, bold="bold" in types)) * size for glyph in painted)
        chars.append({"char": painted, "offset": offset, "font_size": size,
                      "types": sorted(types), "advance": max(0.0, advance),
                      "tracking": tracking * size})

    def measured(start: int, end: int) -> float:
        return sum(item["advance"] for item in chars[start:end]) + sum(
            item["tracking"] for item in chars[start:max(start, end - 1)]
        )

    ranges: list[tuple[int, int]] = []
    breaks = list(re.finditer(r"\r\n|\r|\n", text))
    if breaks:
        # Canonical newlines are hard breaks, even when old saved lines no
        # longer match. Keep original offsets for every formatted fragment.
        cursor = 0
        for match in breaks:
            ranges.append((cursor, match.start()))
            cursor = match.end()
        ranges.append((cursor, len(text)))
    elif hard_lines and len(hard_lines) > 1:
        cursor = 0
        for line in hard_lines:
            if not line.strip():
                ranges.append((cursor, cursor))
                continue
            start = text.find(line.strip(), cursor)
            if start < 0:
                # Canonical text remains authoritative if stale line splits
                # arrive from a saved base after a new text was supplied.
                ranges = [(0, len(text))]
                break
            end = start + len(line.strip())
            ranges.append((start, end))
            cursor = end
        if normalize_spaces(" ".join(text[start:end] for start, end in ranges)) != normalize_spaces(text):
            # Stale or incomplete line lists must not silently discard words.
            ranges = [(0, len(text))]
    else:
        ranges = [(0, len(text))]
    wrapped: list[tuple[int, int]] = []
    for paragraph_start, paragraph_end in ranges:
        tokens = [(paragraph_start + match.start(), paragraph_start + match.end())
                  for match in re.finditer(r"\S+", text[paragraph_start:paragraph_end])]
        if not tokens:
            wrapped.append((paragraph_start, paragraph_start))
            continue
        start, end = tokens[0]
        for token_start, token_end in tokens[1:]:
            if measured(start, token_end) <= box["width"]:
                end = token_end
            else:
                wrapped.append((start, end))
                start, end = token_start, token_end
        wrapped.append((start, end))

    rows = []
    previous_size = 0.0
    baseline = box["y"]
    for row_index, (start, end) in enumerate(wrapped):
        items = chars[start:end]
        maximum = max((item["font_size"] for item in items), default=font_size)
        baseline += maximum * .82 if row_index == 0 else previous_size * .28 + maximum * .82 + font_size * .10
        fragments: list[dict[str, Any]] = []
        cursor_x = box["x"]
        for item in items:
            signature = (item["font_size"], tuple(item["types"]))
            if fragments and fragments[-1]["signature"] == signature:
                fragment = fragments[-1]
                fragment["text"] += item["char"]
                fragment["end"] = item["offset"] + 1
                fragment["width"] += item["advance"] + item["tracking"]
            else:
                fragments.append({"text": item["char"], "start": item["offset"],
                                  "end": item["offset"] + 1, "font_size": item["font_size"],
                                  "types": item["types"], "width": item["advance"] + item["tracking"],
                                  "signature": signature, "x": cursor_x, "y": baseline})
            cursor_x += item["advance"] + item["tracking"]
        for fragment in fragments:
            fragment["width"] -= tracking * fragment["font_size"]
            del fragment["signature"]
        rows.append({"text": text[start:end], "start": start, "end": end,
                     "x": box["x"], "y": baseline, "font_size": maximum,
                     "width": max(0.0, measured(start, end)), "fragments": fragments})
        previous_size = maximum
    return rows


def _rows_bounds(rows: list[dict[str, Any]], box: dict[str, float]) -> dict[str, float]:
    nonempty = [row for row in rows if row["text"]]
    if not nonempty:
        return {"x": box["x"], "y": box["y"], "width": 0.0, "height": 0.0}
    top = min(row["y"] - row["font_size"] * .82 for row in nonempty)
    bottom = max(row["y"] + row["font_size"] * .28 for row in nonempty)
    return {"x": box["x"], "y": top,
            "width": max(row["width"] for row in nonempty), "height": bottom - top}


def ribbon_layout(
    data: dict[str, Any], manifest_dir: Path, width: int | None = None,
    height: int | None = None, *, render_options: dict[str, Any] | None = None,
    font_size_override: float | None = None,
) -> dict[str, Any]:
    """Shared measurement used by preview, rendering and production QA.

    Explicit sizes are never shrunk. A failed fit produces actionable
    warnings alongside the requested drawing, so the editor can fix it.
    """
    width = width or data["canvas"]["width"]
    height = height or data["canvas"]["height"]
    options = {**(data.get("presentation") or {}), **(render_options or {})}
    normalized = normalize_grammar_presentation(options)
    composition = normalized["composition"]
    boxes = {key: _pixel_box(composition[key], width, height)
             for key in ("quote_box", "author_box", "logo_box")}
    faces = _ribbon_face_metrics(data["brand"]["font"], manifest_dir)
    activate_font_metrics(data["brand"]["font"], manifest_dir)
    content = data["content"]
    text = content["text"]
    styles = list(content.get("styles") or [])
    emphasis = content.get("emphasis", "")
    if emphasis and not styles:
        start = text.find(emphasis)
        if start >= 0:
            styles = [{"start": start, "end": start + len(emphasis), "type": "bold"}]
    hard_lines = content.get("lines")
    def rows_at(size: float) -> list[dict[str, Any]]:
        return _ribbon_rows(text, styles, size, boxes["quote_box"], faces, hard_lines)
    def contained(bounds: dict[str, float], box: dict[str, float]) -> bool:
        return (bounds["x"] >= box["x"] - .1 and bounds["y"] >= box["y"] - .1
                and bounds["x"] + bounds["width"] <= box["x"] + box["width"] + .1
                and bounds["y"] + bounds["height"] <= box["y"] + box["height"] + .1)
    def fits(rows: list[dict[str, Any]]) -> bool:
        bounds = _rows_bounds(rows, boxes["quote_box"])
        return contained(bounds, boxes["quote_box"])
    explicit = normalized.get("quote_font_size")
    if explicit is not None:
        font_size = explicit
        fit_mode = "ribbons_explicit"
    elif font_size_override is not None:
        font_size = float(font_size_override)
        fit_mode = "ribbons_shared_fit"
    else:
        low, high = 1.0, width * .22
        for _ in range(32):
            middle = (low + high) / 2
            if fits(rows_at(middle)):
                low = middle
            else:
                high = middle
        scale = max(.8, min(1.0, float(options.get("text_scale", 1.0))))
        font_size = math.floor(low * .995 * scale * 10) / 10
        fit_mode = "ribbons_styled_max_fit"
    rows = rows_at(font_size)
    quote_bounds = _rows_bounds(rows, boxes["quote_box"])
    attribution = content.get("attribution") or {}
    author = attribution.get("label", "") if attribution.get("role") != "none" else ""
    author_font_size = normalized.get("author_font_size", width * ATTRIBUTION_FONT_SIZE_RATIO)
    # Author has independent typography and can naturally occupy two lines.
    author_rows = _ribbon_rows(author, [], author_font_size, boxes["author_box"], faces,
                               author.splitlines(), tracking=0.0) if author else []
    author_bounds = _rows_bounds(author_rows, boxes["author_box"])
    warnings: list[dict[str, str]] = []
    colors = data["brand"]["colors"]
    ground, ink = colors[composition["background_role"]], colors[composition["text_role"]]
    marker = colors[composition["highlight_role"]]
    marker_ink = max(colors.values(), key=lambda color: contrast_ratio(color, marker))
    if contrast_ratio(ink, ground) < 4.5:
        add_error(warnings, "presentation.composition.text_role", "text_contrast",
                  "Il colore del testo non garantisce contrasto sul fondo scelto.")
    if any("highlight" in fragment["types"] for row in rows for fragment in row["fragments"]):
        if contrast_ratio(marker_ink, marker) < 4.5:
            add_error(warnings, "presentation.composition.highlight_role", "highlight_contrast",
                      "Nessun colore della palette rende leggibile il testo sull'highlight.")
    if any("accent" in fragment["types"] and "highlight" not in fragment["types"]
           for row in rows for fragment in row["fragments"]):
        if contrast_ratio(marker, ground) < 4.5:
            add_error(warnings, "content.styles", "accent_contrast",
                      "Il testo colorato non ha abbastanza contrasto sul fondo.")
    if any("outline" in fragment["types"] and "highlight" not in fragment["types"]
           for row in rows for fragment in row["fragments"]):
        if contrast_ratio(ink, ground) < 7:
            add_error(warnings, "content.styles", "outline_contrast",
                      "Il testo a contorno richiede maggiore contrasto sul fondo.")
    for name, rows_value, bounds, box in (
        ("quote", rows, quote_bounds, boxes["quote_box"]),
        ("author", author_rows, author_bounds, boxes["author_box"]),
    ):
        if not contained(bounds, box):
            add_error(warnings, f"presentation.{name}_font_size", f"{name}_overflow",
                      "Il testo non entra nell'area assegnata." if name == "quote"
                      else "L’attribuzione non entra nell’area assegnata.")
        if name == "quote" and any("outline" in fragment["types"] and fragment["font_size"] < width * .045
                                   for row in rows_value for fragment in row["fragments"]):
            add_error(warnings, "content.styles", "outline_too_small", "Il contorno selezionato è troppo piccolo per essere leggibile.")
    def overlaps(first: dict[str, float], second: dict[str, float]) -> bool:
        return (first["width"] > 0 and first["height"] > 0 and second["width"] > 0 and second["height"] > 0
                and min(first["x"] + first["width"], second["x"] + second["width"]) > max(first["x"], second["x"])
                and min(first["y"] + first["height"], second["y"] + second["height"]) > max(first["y"], second["y"]))
    if overlaps(quote_bounds, author_bounds):
        add_error(warnings, "presentation.composition.author_box", "author_overlaps_quote", "L'autore si sovrappone alla citazione.")
    if options.get("logo_mode", "auto") != "hidden" and data["brand"].get("logo"):
        if overlaps(quote_bounds, boxes["logo_box"]) or overlaps(author_bounds, boxes["logo_box"]):
            add_error(warnings, "presentation.composition.logo_box", "logo_overlaps_text", "Il logo si sovrappone al testo.")
    geometry_codes = {"quote_overflow", "author_overflow", "author_overlaps_quote", "logo_overlaps_text"}
    return {"lines": [row["text"] for row in rows], "font_size": font_size,
            "author_font_size": author_font_size, "rows": rows, "author_rows": author_rows,
            **boxes, "bounds": {"quote": quote_bounds, "author": author_bounds, "logo": boxes["logo_box"]},
            "warnings": warnings, "valid": not warnings,
            "geometry_valid": not any(warning["code"] in geometry_codes for warning in warnings), "fitting": fit_mode,
            "metric": "font_metrics_ttf" if faces.get("regular") else "deterministic_heuristic"}


def _ribbon_path(path: dict[str, Any], width: int, height: int) -> str:
    points = path["points"]
    pieces = [f'M {points[0][0] * width:.2f} {points[0][1] * height:.2f}']
    for index in range(1, len(points), 3):
        pieces.append("C " + " ".join(f"{point[0] * width:.2f} {point[1] * height:.2f}"
                                        for point in points[index:index + 3]))
    return " ".join(pieces)


def _split_ribbon_cubic(points: list[list[float]], t: float) -> tuple[list[list[float]], list[list[float]]]:
    """Exact de Casteljau subdivision, keeping editable curve coordinates."""
    def mix(first: list[float], last: list[float]) -> list[float]:
        return [first[axis] + (last[axis] - first[axis]) * t for axis in (0, 1)]
    a, b, c = (mix(points[index], points[index + 1]) for index in range(3))
    d, e = mix(a, b), mix(b, c)
    middle = mix(d, e)
    return [points[0], a, d, middle], [middle, e, c, points[3]]


def _ribbon_crossing_path(
    over: dict[str, Any], under: dict[str, Any], crossing: dict[str, Any], width: int, height: int,
) -> dict[str, Any] | None:
    """Cover one connected stroke intersection without clipping its middle.

    A fixed circle cuts shallow intersections into visible steps. Locate the
    contiguous part of the upper curve approaching the lower stroke instead,
    and redraw that exact Bézier portion through the lower stroke's mask.
    Separate intersections along the same upper path remain separate.
    """
    radius = (over["width_ratio"] + under["width_ratio"]) * width / 2 + 4
    step = max(3.0, radius / 4)

    def distance(point: tuple[float, float], start: tuple[float, float], end: tuple[float, float]) -> float:
        dx, dy = end[0] - start[0], end[1] - start[1]
        square = dx*dx + dy*dy
        t = max(0.0, min(1.0, ((point[0] - start[0])*dx + (point[1] - start[1])*dy) / square)) if square else 0
        return math.hypot(point[0] - start[0] - t*dx, point[1] - start[1] - t*dy)

    def flatten(path: dict[str, Any]) -> list[tuple[float, tuple[float, float]]]:
        points = [[point[0] * width, point[1] * height] for point in path["points"]]
        result = [(0.0, tuple(points[0]))]
        def visit(curve: list[list[float]], start: float, end: float, depth: int = 0) -> None:
            first, last = tuple(curve[0]), tuple(curve[3])
            flatness = max(distance(tuple(curve[1]), first, last), distance(tuple(curve[2]), first, last))
            if depth >= 12 or (flatness <= 1 and math.dist(first, last) <= step):
                result.append((end, last))
                return
            left, right = _split_ribbon_cubic(curve, .5)
            middle = (start + end) / 2
            visit(left, start, middle, depth + 1)
            visit(right, middle, end, depth + 1)
        for segment in range((len(points) - 1) // 3):
            visit(points[segment * 3:segment * 3 + 4], float(segment), float(segment + 1))
        return result

    upper, lower = flatten(over), flatten(under)
    # Index nearby line pieces so long arbitrary paths do not need a full
    # Cartesian scan on every preview. Flatness contributes <1px of error.
    cells: dict[tuple[int, int], list[tuple[tuple[float, float], tuple[float, float]]]] = {}
    for (_, first), (_, last) in zip(lower, lower[1:]):
        for cell_x in range(math.floor((min(first[0], last[0]) - radius) / radius),
                            math.floor((max(first[0], last[0]) + radius) / radius) + 1):
            for cell_y in range(math.floor((min(first[1], last[1]) - radius) / radius),
                                math.floor((max(first[1], last[1]) + radius) / radius) + 1):
                cells.setdefault((cell_x, cell_y), []).append((first, last))
    intervals: list[tuple[int, int]] = []
    start = None
    for index, (_, point) in enumerate(upper):
        nearby = cells.get((math.floor(point[0] / radius), math.floor(point[1] / radius)), [])
        active = any(distance(point, first, last) <= radius for first, last in nearby)
        if active and start is None:
            start = index
        if start is not None and (not active or index == len(upper) - 1):
            intervals.append((max(0, start - 1), index))
            start = None
    if not intervals:
        return None
    anchor = crossing["segment"] + crossing["t"]
    first, last = min(intervals, key=lambda pair: max(upper[pair[0]][0] - anchor, anchor - upper[pair[1]][0], 0))
    start_parameter, end_parameter = upper[first][0], upper[last][0]
    sliced: list[list[float]] = []
    for segment in range((len(over["points"]) - 1) // 3):
        low, high = max(0.0, start_parameter - segment), min(1.0, end_parameter - segment)
        if high <= low:
            continue
        curve = over["points"][segment * 3:segment * 3 + 4]
        if high < 1:
            curve, _ = _split_ribbon_cubic(curve, high)
        if low > 0:
            _, curve = _split_ribbon_cubic(curve, low / high)
        sliced.extend(curve if not sliced else curve[1:])
    return {**over, "points": sliced} if sliced else None


def _ribbon_text(
    rows: list[dict[str, Any]], colors: dict[str, str], composition: dict[str, Any],
    *, author: bool = False, tracking: float = QUOTE_TRACKING_EM,
) -> str:
    ink = colors[composition["text_role"]]
    highlight = colors[composition["highlight_role"]]
    highlight_ink = max(colors.values(), key=lambda color: contrast_ratio(color, highlight))
    marks, texts = [], []
    for row in rows:
        for fragment in row["fragments"]:
            types = set(fragment["types"])
            size, x, y, fragment_width = (fragment[key] for key in ("font_size", "x", "y", "width"))
            fill = highlight_ink if "highlight" in types else highlight if "accent" in types else ink
            if "highlight" in types:
                marks.append(f'<rect class="highlight-marker" x="{x - size * .025:.2f}" y="{y - size * .79:.2f}" '
                             f'width="{fragment_width + size * .05:.2f}" height="{size * .98:.2f}" rx="{size * .045:.2f}" fill="{highlight}"/>')
            attrs = ' font-weight="700"' if "bold" in types else ' font-weight="400"'
            attrs += ' font-style="italic"' if "italic" in types else ""
            if "underline" in types:
                attrs += ' text-decoration="underline"'
            if "outline" in types and "highlight" not in types:
                attrs += f' stroke="{fill}" stroke-width="{size * OUTLINE_STROKE_EM:.2f}" stroke-linejoin="round"'
                fill = "none"
            kind = "meta attribution source-field" if author else "quote"
            fragment_tracking = 0 if author else tracking
            texts.append(f'<text class="{kind}" x="{x:.2f}" y="{y:.2f}" font-size="{size:.2f}" '
                         f'fill="{fill}"{attrs} xml:space="preserve" style="letter-spacing:{fragment_tracking}em;white-space:pre" '
                         f'data-start="{fragment["start"]}" data-end="{fragment["end"]}" '
                         f'data-text-styles="{" ".join(sorted(types))}" '
                         f'data-measured-width="{fragment_width:.4f}">{html.escape(fragment["text"])}</text>')
    return "".join(marks + texts)


def render_ribbon_svg(
    data: dict[str, Any], manifest_dir: Path, *, render_options: dict[str, Any] | None = None,
    font_size_override: float | None = None,
) -> str:
    """Render chosen editable paths; the preview and export share this function."""
    width, height = data["canvas"]["width"], data["canvas"]["height"]
    options = {**(data.get("presentation") or {}), **(render_options or {})}
    composition = normalize_grammar_presentation(options)["composition"]
    layout = ribbon_layout(data, manifest_dir, render_options=render_options, font_size_override=font_size_override)
    colors, brand = data["brand"]["colors"], data["brand"]
    background = colors[composition["background_role"]]
    ink = colors[composition["text_role"]]
    family = card_font_stack(brand["font"]["family"])
    # Measurements use sfnt glyph advances, so do not let platform-specific
    # kerning/ligature substitutions move the highlight boundaries later.
    css = font_css(brand["font"], manifest_dir) + (
        f".quote,.meta{{font-family:{family};font-synthesis:weight;"
        "font-kerning:none;font-variant-ligatures:none;}"
    )
    protected = []
    # Protect ink that actually exists, rather than cutting entire unused
    # layout lanes out of the drawing. An absent author's declared area is
    # still reserved; when present, its protection grows with its real text.
    # Curves stay the user's chosen curves when typography is edited.
    for key in ("quote_box", "author_box", "logo_box"):
        if key == "logo_box" and options.get("logo_mode", "auto") == "hidden":
            continue
        if key == "quote_box":
            box = layout["bounds"]["quote"]
        elif key == "author_box" and layout["author_rows"]:
            box = layout["bounds"]["author"]
        elif key == "logo_box":
            asset = logo_data(brand, manifest_dir, light=relative_luminance(background) < .2)
            if not asset:
                continue
            lane = layout[key]
            logo_width = min(lane["width"], lane["height"] * asset[1])
            box = {**lane, "width": logo_width, "height": logo_width / asset[1]}
        else:
            box = layout[key]
        if not box["width"] or not box["height"]:
            continue
        pad = width * .012
        protected.append(f'<rect x="{box["x"] - pad:.2f}" y="{box["y"] - pad:.2f}" '
                         f'width="{box["width"] + 2*pad:.2f}" height="{box["height"] + 2*pad:.2f}" '
                         f'rx="{pad * 1.5:.2f}" fill="black"/>')
    definitions = [f'<mask id="ribbon-clearance" maskUnits="userSpaceOnUse" x="0" y="0" width="{width}" height="{height}">'
                   f'<rect width="{width}" height="{height}" fill="white"/>{"".join(protected)}</mask>']
    by_id = {path["id"]: path for path in composition["ribbons"]}
    def stroke(path: dict[str, Any], extra: str = "") -> str:
        return (f'<path class="ribbon" data-ribbon-id="{path["id"]}" d="{_ribbon_path(path, width, height)}" '
                f'fill="none" stroke="{colors[path["color_role"]]}" stroke-width="{path["width_ratio"] * width:.2f}" '
                f'stroke-linecap="round" stroke-linejoin="round"{extra}/>')
    drawings = [stroke(path) for path in composition["ribbons"]]
    for index, crossing in enumerate(composition["crossings"]):
        over, under = by_id[crossing["over"]], by_id[crossing["under"]]
        portion = _ribbon_crossing_path(over, under, crossing, width, height)
        if portion is None:
            continue
        mask_id = f"ribbon-crossing-{index}"
        definitions.append(
            f'<mask id="{mask_id}" maskUnits="userSpaceOnUse" x="0" y="0" width="{width}" height="{height}">'
            f'<path d="{_ribbon_path(under, width, height)}" fill="none" stroke="white" '
            f'stroke-width="{under["width_ratio"] * width:.2f}" stroke-linecap="round" stroke-linejoin="round"/></mask>'
        )
        drawings.append(stroke(portion, f' mask="url(#{mask_id})" data-over="{over["id"]}" data-under="{under["id"]}"'))
    graphic = "" if options.get("graphic_mode", "auto") == "hidden" else (
        f'<g class="ribbon-geometry" mask="url(#ribbon-clearance)">{"".join(drawings)}</g>'
    )
    box = layout["logo_box"]
    logo = ""
    if options.get("logo_mode", "auto") != "hidden":
        asset = logo_data(brand, manifest_dir, light=relative_luminance(background) < .2)
        if asset:
            logo_width = min(box["width"], box["height"] * asset[1])
            logo = logo_image(asset, x=box["x"], y=box["y"], width=logo_width)
    attribution = data["content"].get("attribution") or {}
    label = attribution.get("label", "") if attribution.get("role") != "none" else ""
    desc = data["content"].get("alt_text", "").strip() or default_alt_text(data["content"]["text"], label, data.get("source"))
    attrs = " ".join(f'data-{key.replace("_", "-")}="{html.escape(json.dumps(layout[key]), quote=True)}"'
                     for key in ("quote_box", "author_box", "logo_box"))
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
            f'role="img" aria-labelledby="title desc" data-visual-grammar="ribbons" '
            f'data-composition-id="{composition["id"]}" data-layout-valid="{str(layout["valid"]).lower()}" '
            f'data-geometry-valid="{str(layout["geometry_valid"]).lower()}" '
            f'data-layout-warnings="{html.escape(json.dumps(layout["warnings"]), quote=True)}" {attrs}>'
            f'<title id="title">{html.escape("Nastri — " + brand["name"])}</title><desc id="desc">{html.escape(desc)}</desc>'
            f'<style>{css}</style><defs>{"".join(definitions)}</defs>'
            f'<rect width="{width}" height="{height}" fill="{background}"/>{graphic}{logo}'
            f'{_ribbon_text(layout["rows"], colors, composition)}'
            f'{_ribbon_text(layout["author_rows"], colors, composition, author=True)}</svg>\n')


def _xerox_rows(
    text: str, styles: list[dict[str, Any]], font_size: float, box: dict[str, float],
    faces: dict[str, dict[str, float] | None], hard_lines: list[str] | None,
) -> list[dict[str, Any]]:
    # Preserve source text and its offsets. Uppercase is a painted treatment,
    # including expanding glyphs such as ß; editor selections keep their indexes.
    tokens = list(re.finditer(r"\S+", text))
    default_styles = ([{"start": tokens[-2].start(), "end": len(text), "type": "size", "scale": .55}]
                      if len(tokens) >= 5 else [])
    rows = _ribbon_rows(text, default_styles + styles, font_size, box, faces, hard_lines,
                        tracking=0, uppercase=True)
    baseline, previous_size = box["y"], 0.0
    for index, row in enumerate(rows):
        size = row["font_size"]
        baseline += size * .82 if index == 0 else previous_size * .18 + size * .65
        row["y"] = baseline
        for fragment in row["fragments"]:
            fragment["y"] = baseline
        previous_size = size
    return rows


def urban_layout(data: dict[str, Any], manifest_dir: Path, width: int | None = None,
                 height: int | None = None, *, render_options: dict[str, Any] | None = None,
                 font_size_override: float | None = None) -> dict[str, Any]:
    options = {**(data.get("presentation") or {}), **(render_options or {})}
    scene = normalize_grammar_presentation(options)["composition"]
    width, height = width or data["canvas"]["width"], height or data["canvas"]["height"]
    boxes = {key: _pixel_box(scene[key], width, height) for key in ("quote_box", "author_box", "logo_box")}
    faces = _ribbon_face_metrics(data["brand"]["font"], manifest_dir)
    activate_font_metrics(data["brand"]["font"], manifest_dir)
    text = data["content"]["text"]
    styles = list(data["content"].get("styles") or [])
    xerox = is_xerox(scene)
    row_builder = _xerox_rows if xerox else _ribbon_rows
    size = scene.get("quote_font_size", options.get("quote_font_size", font_size_override))
    if size is None:
        low, high = 1.0, width*(.1982 if xerox else .22)
        for _ in range(32):
            mid=(low+high)/2
            rows=row_builder(text,styles,mid,boxes["quote_box"],faces,data["content"].get("lines"))
            bounds=_rows_bounds(rows,boxes["quote_box"])
            if bounds["width"]<=boxes["quote_box"]["width"] and bounds["height"]<=boxes["quote_box"]["height"]: low=mid
            else: high=mid
        size=math.floor(low*.995*float(options.get("text_scale",1))*10)/10
    rows=row_builder(text,styles,float(size),boxes["quote_box"],faces,data["content"].get("lines"))
    attribution=data["content"].get("attribution") or {}; author=attribution.get("label","") if attribution.get("role")!="none" else ""
    author_size=options.get("author_font_size",width*ATTRIBUTION_FONT_SIZE_RATIO)
    author_rows=_ribbon_rows(author,[],float(author_size),boxes["author_box"],faces,author.splitlines(),tracking=0) if author else []
    bounds=_rows_bounds(rows,boxes["quote_box"]); warnings=[]
    if bounds["width"]>boxes["quote_box"]["width"] or bounds["height"]>boxes["quote_box"]["height"]:
        add_error(warnings,"presentation.quote_font_size","quote_overflow","Il testo non entra nell'area assegnata.")
    ground=(XEROX_COLORS["background"] if xerox and not scene.get("quote_backing_role") else
            data["brand"]["colors"][scene.get("quote_backing_role",scene["background_role"])])
    ink=data["brand"]["colors"][scene["text_role"]]
    if contrast_ratio(ink,ground)<4.5:
        add_error(warnings,"presentation.composition.text_role","text_contrast","Il colore del testo non garantisce contrasto sul fondo riservato alla citazione.")
    author_ground=(XEROX_COLORS["background"] if xerox and not scene.get("author_backing_role") else
                   data["brand"]["colors"][scene.get("author_backing_role",scene["background_role"])])
    if author and contrast_ratio(ink,author_ground)<4.5:
        add_error(warnings,"presentation.composition.text_role","author_contrast","Il colore del testo non garantisce contrasto sul fondo riservato all'attribuzione.")
    author_bounds=_rows_bounds(author_rows,boxes["author_box"])
    def overlaps(a: dict[str,float], b: dict[str,float]) -> bool:
        return bool(a["width"] and a["height"] and b["width"] and b["height"] and min(a["x"]+a["width"],b["x"]+b["width"])>max(a["x"],b["x"]) and min(a["y"]+a["height"],b["y"]+b["height"])>max(a["y"],b["y"]))
    if overlaps(bounds,author_bounds): add_error(warnings,"presentation.composition.author_box","author_overlaps_quote","L'attribuzione si sovrappone alla citazione.")
    if options.get("logo_mode","auto")!="hidden" and data["brand"].get("logo") and (overlaps(bounds,boxes["logo_box"]) or overlaps(author_bounds,boxes["logo_box"])):
        add_error(warnings,"presentation.composition.logo_box","logo_overlaps_text","Il logo si sovrappone al testo.")
    return {"rows":rows,"author_rows":author_rows,"font_size":float(size),"author_font_size":float(author_size),**boxes,
            "bounds":{"quote":bounds,"author":author_bounds,"logo":boxes["logo_box"]},
            "warnings":warnings,"valid":not warnings,"geometry_valid":not warnings,"fitting":"urban_fit","metric":"font_metrics_ttf" if faces.get("regular") else "deterministic_heuristic"}

def render_urban_svg(data: dict[str, Any], manifest_dir: Path, *, render_options: dict[str, Any] | None = None,
                     font_size_override: float | None = None) -> str:
    options={**(data.get("presentation") or {}),**(render_options or {})}
    scene=normalize_grammar_presentation(options)["composition"]
    layout=urban_layout(data,manifest_dir,render_options=render_options,font_size_override=font_size_override)
    width,height=data["canvas"]["width"],data["canvas"]["height"]; colors=data["brand"]["colors"]
    bg=(XEROX_COLORS["background"] if is_xerox(scene) else colors[scene["background_role"]])
    artwork = (f'<image class="urban-artwork" data-artwork-id="{scene["artwork_id"]}" '
               f'x="0" y="0" width="{width}" height="{height}" '
               f'preserveAspectRatio="xMidYMid slice" href="{artwork_data_uri(scene["artwork_id"])}"/>'
               if scene.get("artwork_id") else "")
    shapes=[]
    for b in scene["blocks"]:
        if b["shape"]=="rect":
            shapes.append(f'<rect data-block-id="{html.escape(str(b["id"]),quote=True)}" x="{b["x"]*width:.2f}" y="{b["y"]*height:.2f}" width="{b["width"]*width:.2f}" height="{b["height"]*height:.2f}" fill="{colors[b["color_role"]]}"/>')
        else:
            pts=" ".join(f'{x*width:.2f},{y*height:.2f}' for x,y in b["points"])
            shapes.append(f'<polygon data-block-id="{html.escape(str(b["id"]),quote=True)}" points="{pts}" fill="{colors[b["color_role"]]}"/>')
    for s in scene["strips"]:
        shapes.append(f'<line data-strip-id="{html.escape(str(s["id"]),quote=True)}" x1="{s["x1"]*width:.2f}" y1="{s["y1"]*height:.2f}" x2="{s["x2"]*width:.2f}" y2="{s["y2"]*height:.2f}" stroke="{colors[s["color_role"]]}" stroke-width="{s["width"]*width:.2f}"/>')
    # Reserve the explicitly selected backing role beneath each text lane.
    for lane, key in (("quote", "quote_box"), ("author", "author_box")):
        backing=scene.get(f"{lane}_backing_role")
        if backing:
            box=layout[key]
            shapes.append(f'<rect class="{lane}-backing" x="{box["x"]:.2f}" y="{box["y"]:.2f}" width="{box["width"]:.2f}" height="{box["height"]:.2f}" fill="{colors[backing]}"/>')
    texture=scene["texture"]; rng=random.Random(texture["seed"]); marks=[]
    for _ in range(texture["dots"]):
        x,y=rng.random()*width,rng.random()*height
        if not any(box["x"]-12<x<box["x"]+box["width"]+12 and box["y"]-12<y<box["y"]+box["height"]+12 for box in (layout["quote_box"],layout["author_box"])):
            marks.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rng.uniform(1,2.1):.1f}" fill="{colors[texture["color_role"]]}" opacity=".18"/>')
    for _ in range(texture["scratches"]):
        x,y=rng.random()*width,rng.random()*height; dx=rng.uniform(5,24); dy=rng.uniform(-12,12)
        if not any(max(x,x+dx)>=box["x"]-12 and min(x,x+dx)<=box["x"]+box["width"]+12 and max(y,y+dy)>=box["y"]-12 and min(y,y+dy)<=box["y"]+box["height"]+12 for box in (layout["quote_box"],layout["author_box"])):
            marks.append(f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x+dx:.1f}" y2="{y+dy:.1f}" stroke="{colors[texture["color_role"]]}" opacity=".2" stroke-width="1"/>')
    logo=""; asset=logo_data(data["brand"],manifest_dir,light=relative_luminance(bg)<.2)
    if asset and options.get("logo_mode","auto")!="hidden":
        box=layout["logo_box"]; lw=min(box["width"],box["height"]*asset[1]); logo=logo_image(asset,x=box["x"],y=box["y"],width=lw)
    attribution=data["content"].get("attribution") or {}; author=attribution.get("label","") if attribution.get("role")!="none" else ""
    desc=data["content"].get("alt_text","").strip() or default_alt_text(data["content"]["text"],author,data.get("source"))
    attrs=" ".join(f'data-{k.replace("_","-")}="{html.escape(json.dumps(layout[k]),quote=True)}"' for k in ("quote_box","author_box","logo_box"))
    css=font_css(data["brand"]["font"],manifest_dir)+f'.quote,.meta{{font-family:{card_font_stack(data["brand"]["font"]["family"])};font-synthesis:weight;font-kerning:none;font-variant-ligatures:none}}'
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'+f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc" data-visual-grammar="urban" data-composition-id="{scene["id"]}" data-layout-valid="{str(layout["valid"]).lower()}" data-geometry-valid="{str(layout["geometry_valid"]).lower()}" data-layout-warnings="{html.escape(json.dumps(layout["warnings"]),quote=True)}" {attrs}><title id="title">Urban — {html.escape(data["brand"]["name"])}</title><desc id="desc">{html.escape(desc)}</desc><style>{css}</style><rect width="100%" height="100%" fill="{bg}"/>{artwork}{''.join(shapes)}{''.join(marks)}{logo}{_ribbon_text(layout["rows"],colors,scene,tracking=0 if is_xerox(scene) else QUOTE_TRACKING_EM)}{_ribbon_text(layout["author_rows"],colors,scene,author=True)}</svg>\n')

def render_svg(
    data: dict[str, Any],
    manifest_dir: Path,
    direction: str,
    *,
    font_size_override: float | None = None,
    render_options: dict[str, Any] | None = None,
) -> str:
    grammar = {**(data.get("presentation") or {}), **(render_options or {})}.get("visual_grammar")
    if grammar == "urban":
        return render_urban_svg(data, manifest_dir, render_options=render_options, font_size_override=font_size_override)
    if grammar == "ribbons":
        return render_ribbon_svg(data, manifest_dir, render_options=render_options, font_size_override=font_size_override)
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
    # Optional editor scale is applied after the canonical max-fit calculation.
    # Keeping it as a render option preserves the compact visual-manifest 0.2
    # contract while allowing the MCP editor to expose the same control as the
    # local review editor.
    try:
        text_scale = float(options.get("text_scale", 1.0))
    except (TypeError, ValueError):
        text_scale = 1.0
    text_scale = max(0.8, min(1.0, text_scale))
    logo_mode = options.get("logo_mode", "auto")
    graphic_mode = options.get("graphic_mode", "auto")
    graphic_variant = options.get("graphic_variant", "default")
    gradient_inks: list[str] | None = None
    gradient_logo_status = "not_present"
    if (direction == "editorial" and graphic_variant == "gradient"
            and graphic_mode != "hidden"):
        gradient_inks, gradient_logo_status = gradient_ink_colours(
            brand, manifest_dir, logo_mode=logo_mode,
        )
    graphic = direction_graphic(
        direction, width=width, height=height, colors=colors, enabled=graphic_mode != "hidden",
        variant=graphic_variant if graphic_variant_allowed(direction, graphic_variant) else "default",
        seed=options.get("graphic_seed", 0), gradient_inks=gradient_inks,
        gradient_logo_status=gradient_logo_status,
    )
    vertical_position = options.get("vertical_position", "center")
    geometry = presentation_geometry(data, direction, width, height, vertical_position, render_options)
    safe = width * 0.085
    css = (
        font_css(brand["font"], manifest_dir)
        + f".quote{{font-family:{font_stack};font-weight:500;font-synthesis:weight;letter-spacing:-0.018em;}}"
        + f".meta{{font-family:{font_stack};font-weight:500;letter-spacing:0.08em;}}"
        + ".data{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-weight:600;letter-spacing:0.08em;}"
    )

    if direction == "editorial":
        cover = cover_layout(height) if cover_enabled(direction, options) else None
        background = colors["background"]
        quote_color = colors["primary"]
        quote_x = geometry["text_x"]
        font_size = font_size_override or fitted_font_size(
            lines, geometry["text_width"], geometry["fit_height"], float(max(width, height)),
            letter_spacing_em=geometry["tracking_em"],
        )
        if font_size_override is None:
            font_size *= text_scale
        line_height = font_size * geometry["line_ratio"]
        block_height = line_height * max(0, len(lines) - 1) + font_size
        start_y = geometry["start_y"]
        logo_asset = None if logo_mode == "hidden" else logo_data(brand, manifest_dir, light=False)
        cutouts = cutouts_layout(height) if cutouts_enabled(direction, options) else None
        logo = "" if logo_mode == "hidden" else logo_image(
            logo_asset,
            x=width * 0.07, y=cover["logo_y"] if cover else height * 0.21 if cutouts else height * 0.055,
            width=cover_logo_width(width, height, logo_asset[1]) if (cover or cutouts) and logo_asset else width * 0.21,
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
        attribution_y = cover["attribution_y"] if cover else height * 0.82 if cutouts else height * 0.915
        attribution_size = attribution_font_size(attribution, width, width * 0.82)
        attribution_x = width * 0.07 if cutouts else width * 0.91
        attribution_anchor = "start" if cutouts else "end"
        body = (
            f'<rect width="{width}" height="{height}" fill="{background}"/>'
            f'{graphic}{logo}{quote}'
            f'<text class="meta attribution source-field" x="{attribution_x:.1f}" y="{attribution_y:.1f}" '
            f'text-anchor="{attribution_anchor}" font-size="{attribution_size:.1f}" fill="{colors["text"]}">'
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
        if font_size_override is None:
            font_size *= text_scale
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
        statement_attribution_size = attribution_font_size(attribution, width, width * 0.89)
        body = (
            f'<rect width="{width}" height="{height}" fill="{background}"/>'
            f'{graphic}{logo}{quote}'
            f'<text class="meta attribution source-field" x="{width * 0.945:.1f}" y="{statement_attribution_y:.1f}" '
            f'text-anchor="end" font-size="{statement_attribution_size:.1f}" fill="{colors["background"]}">'
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
        if font_size_override is None:
            font_size *= text_scale
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
        field_attribution_size = attribution_font_size(attribution, width, geometry["text_width"])
        body = (
            f'<rect width="{width}" height="{height}" fill="{background}"/>'
            f'<rect class="field-sheet" x="{sheet_x:.1f}" y="{sheet_y:.1f}" '
            f'width="{sheet_width:.1f}" height="{sheet_height:.1f}" fill="{colors["background"]}"/>'
            f'{graphic}'
            f'{logo}{marks}'
            f'{quote}'
            f'<text class="meta attribution source-field" x="{content_right:.1f}" y="{field_attribution_y:.1f}" '
            f'text-anchor="end" font-size="{field_attribution_size:.1f}" fill="{colors["text"]}">'
            f'{html.escape(attribution)}</text>'
        )

    title = f"Quote card {direction} — {brand['name']}"
    alt_override = str(content.get("alt_text", "")).strip()
    description = alt_override or default_alt_text(content["text"], attribution, source)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">'
        f'<title id="title">{html.escape(title)}</title><desc id="desc">{html.escape(description)}</desc>'
        f'<style>{css}</style>{body}</svg>\n'
    )


def write_contact_sheet(paths: list[Path], output_path: Path, title: str, alt_text: str = "") -> None:
    cards = "".join(
        f'<figure><img src="{html.escape(path.name, quote=True)}" alt="{html.escape(alt_text or path.stem)}"><figcaption>{html.escape(path.stem)}</figcaption></figure>'
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
