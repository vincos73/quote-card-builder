#!/usr/bin/env python3
"""Render deterministic 4:5 quote-card proofs from a visual manifest 0.2."""

from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import math
import os
import re
import shutil
import subprocess
import sys
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


DIRECTIONS = ("editorial", "statement", "contextual")
TRANSFORMATIONS = {"VERBATIM", "EDITED", "PARAPHRASE", "AI_GENERATED"}
EVIDENCE_STATUSES = {"VERIFIED", "USER_SUPPLIED", "UNVERIFIED", "CONFLICT"}
EVIDENCE_LABELS = {
    "VERIFIED": "ESTRATTO VERIFICATO",
    "USER_SUPPLIED": "FONTE FORNITA",
    "UNVERIFIED": "DA VERIFICARE",
    "CONFLICT": "PROVA IN CONFLITTO",
}
ATTRIBUTION_ROLES = {"speaker", "author", "publisher", "none"}
STYLE_TYPES = {"bold", "italic", "underline", "highlight"}
HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")
UNSAFE_SVG = re.compile(r"<(?:script|foreignObject)\b|\bon\w+\s*=", re.IGNORECASE)


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
            add_error(errors, f"{item_path}.type", "enum", "Usare bold, italic, underline o highlight.")


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
        or not 1 <= len(lines) <= 6
        or any(not isinstance(line, str) for line in lines if isinstance(lines, list))
        or (isinstance(lines, list) and not any(line.strip() for line in lines if isinstance(line, str)))
    ):
        add_error(errors, "content.lines", "lines", "Inserire da 1 a 6 righe, con almeno una riga di testo.")
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

    use_quotes = content.get("use_quotation_marks")
    if not isinstance(use_quotes, bool):
        add_error(errors, "content.use_quotation_marks", "type", "Deve essere true o false.")

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


def visual_units(value: str) -> float:
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
    return units


def fitted_font_size(lines: list[str], available_width: float, available_height: float, maximum: float) -> float:
    max_units = max(visual_units(line) for line in lines)
    width_size = available_width / max(max_units, 1)
    height_size = available_height / (len(lines) * 1.18)
    return max(48, min(maximum, width_size, height_size))


def statement_visual_lines(lines: list[str], width: int, height: int) -> list[str]:
    """Add poster-style soft wraps without removing any user-authored hard break."""
    target_units = 11.5 if width / height >= 0.75 else 9.5
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
                if current and visual_units(candidate) > limit:
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
        if styles and any(
            style["type"] in {"bold", "highlight"}
            and style["end"] > line_start
            and style["start"] < line_end
            for style in styles
        ):
            strong.add(index)
        elif emphasis_start >= 0 and emphasis_end > line_start and emphasis_start < line_end:
            strong.add(index)
        cursor = line_end
        has_text = True
    if not strong:
        strong.add(max(index for index, line in enumerate(lines) if line))
    return strong


def statement_fitted_font_size(
    lines: list[str], strong_rows: set[int], width: int, height: int
) -> float:
    safe = width * 0.055
    available_width = width - 2 * safe
    available_height = height * 0.55
    strong_multiplier = 1.12
    width_limits = [
        available_width / max(visual_units(line) * (strong_multiplier if index in strong_rows else 1.0), 1)
        for index, line in enumerate(lines)
        if line
    ]
    vertical_multipliers = [
        1.4 if not line else strong_multiplier if index in strong_rows else 1.0
        for index, line in enumerate(lines)
    ]
    vertical_units = sum(vertical_multipliers[:-1]) * 0.98 + vertical_multipliers[-1]
    height_limit = available_height / max(vertical_units, 1)
    return max(48, min(width * 0.074, height_limit, *width_limits))


def statement_block_height(font_size: float, lines: list[str], strong_rows: set[int]) -> float:
    multipliers = [1.4 if not line else 1.12 if index in strong_rows else 1.0 for index, line in enumerate(lines)]
    if not multipliers:
        return 0.0
    return sum(font_size * multiplier * 0.98 for multiplier in multipliers[:-1]) + font_size * multipliers[-1]


def emphasized_lines(lines: list[str], emphasis: str, emphasis_color: str) -> list[str]:
    """Render one exact emphasis phrase, including when it crosses line breaks."""
    joined = " ".join(lines)
    start = joined.find(emphasis) if emphasis else -1
    if start < 0:
        return [html.escape(line) for line in lines]
    end = start + len(emphasis)
    rendered: list[str] = []
    cursor = 0
    for line in lines:
        line_start, line_end = cursor, cursor + len(line)
        overlap_start, overlap_end = max(start, line_start), min(end, line_end)
        if overlap_start < overlap_end:
            local_start, local_end = overlap_start - line_start, overlap_end - line_start
            rendered.append(
                f"{html.escape(line[:local_start])}"
                f"<tspan font-weight=\"700\" fill=\"{emphasis_color}\">"
                f"{html.escape(line[local_start:local_end])}</tspan>"
                f"{html.escape(line[local_end:])}"
            )
        else:
            rendered.append(html.escape(line))
        cursor = line_end + 1
    return rendered


def styled_lines(lines: list[str], styles: list[dict[str, Any]], highlight_color: str) -> list[str]:
    """Render user-owned inline styles against text offsets, preserving spacer rows."""
    rendered: list[str] = []
    cursor = 0
    has_text = False
    for line in lines:
        if not line:
            rendered.append("")
            continue
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
            value = html.escape(line[local_start:local_end])
            if not active:
                fragments.append(value)
                continue
            attributes: list[str] = []
            if "bold" in active:
                attributes.append('font-weight="700"')
            if "italic" in active:
                attributes.append('font-style="italic"')
            if "underline" in active:
                attributes.append('style="text-decoration:underline;text-decoration-thickness:.07em;text-underline-offset:.12em"')
            if "highlight" in active:
                attributes.extend(
                    (
                        'paint-order="stroke fill"',
                        f'stroke="{highlight_color}"',
                        'stroke-width=".24em"',
                        'stroke-linecap="round"',
                        'stroke-linejoin="round"',
                    )
                )
            fragments.append(f"<tspan {' '.join(attributes)}>{value}</tspan>")
        rendered.append("".join(fragments))
        cursor = line_end
        has_text = True
    return rendered


def text_block(
    lines: list[str], *, x: float, y: float, font_size: float, line_height: float,
    color: str, emphasis: str, emphasis_color: str, styles: list[dict[str, Any]] | None = None,
    highlight_color: str | None = None, anchor: str = "start"
) -> str:
    rendered = []
    formatted = (
        emphasized_lines(lines, emphasis, emphasis_color)
        if styles is None
        else styled_lines(lines, styles, highlight_color or emphasis_color)
    )
    for index, content in enumerate(formatted):
        line_y = y + index * line_height
        rendered.append(f'<tspan x="{x:.1f}" y="{line_y:.1f}">{content}</tspan>')
    return (
        f'<text class="quote" x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
        f'font-size="{font_size:.1f}" fill="{color}">{"".join(rendered)}</text>'
    )


def statement_text_block(
    lines: list[str], *, x: float, y: float, font_size: float, color: str,
    emphasis: str, emphasis_color: str, strong_rows: set[int],
    styles: list[dict[str, Any]] | None = None, highlight_color: str | None = None,
) -> str:
    formatted = (
        emphasized_lines(lines, emphasis, emphasis_color)
        if styles is None
        else styled_lines(lines, styles, highlight_color or emphasis_color)
    )
    rows: list[str] = []
    cursor_y = y
    for index, content in enumerate(formatted):
        multiplier = 1.4 if not lines[index] else 1.12 if index in strong_rows else 1.0
        size = font_size * multiplier
        fill = emphasis_color if index in strong_rows else color
        weight = ' font-weight="700"' if index in strong_rows else ""
        rows.append(
            f'<tspan x="{x:.1f}" y="{cursor_y:.1f}" font-size="{size:.1f}" fill="{fill}"{weight}>{content}</tspan>'
        )
        cursor_y += size * 0.98
    return (
        f'<text class="quote" data-layout="statement-poster" x="{x:.1f}" y="{y:.1f}" '
        f'style="font-weight:700;letter-spacing:-0.032em" fill="{color}">{"".join(rows)}</text>'
    )


def quote_marks(use_quotes: bool, *, color: str, open_x: float, open_y: float, close_x: float, close_y: float) -> str:
    if not use_quotes:
        return ""
    return (
        f'<text class="marks" x="{open_x:.1f}" y="{open_y:.1f}" fill="{color}">“</text>'
        f'<text class="marks" x="{close_x:.1f}" y="{close_y:.1f}" fill="{color}">”</text>'
    )


def direction_graphic(
    direction: str, *, width: int, height: int, colors: dict[str, str], enabled: bool
) -> str:
    """Render the fixed evergreen motif paired with a visual direction."""
    if not enabled:
        return ""
    if direction == "editorial":
        top_paths: list[str] = []
        bottom_paths: list[str] = []
        for index in range(7):
            x = width * (0.625 + index * 0.058)
            top_paths.append(
                f'<path class="contour contour--top" d="M {x:.1f} {-height * 0.03:.1f} '
                f'C {x - width * 0.025:.1f} {height * 0.07:.1f}, {x + width * 0.095:.1f} {height * 0.095:.1f}, {x + width * 0.055:.1f} {height * 0.18:.1f} '
                f'C {x + width * 0.015:.1f} {height * 0.265:.1f}, {x + width * 0.105:.1f} {height * 0.335:.1f}, {x + width * 0.18:.1f} {height * 0.455:.1f}"/>'
            )
            y = height * (0.67 + index * 0.032)
            bottom_paths.append(
                f'<path class="contour contour--bottom" d="M {-width * 0.035:.1f} {y:.1f} '
                f'C {width * 0.075:.1f} {y - height * 0.01:.1f}, {width * 0.045:.1f} {y + height * 0.075:.1f}, {width * 0.155:.1f} {y + height * 0.085:.1f} '
                f'C {width * 0.27:.1f} {y + height * 0.095:.1f}, {width * 0.30:.1f} {y + height * 0.165:.1f}, {width * 0.43:.1f} {y + height * 0.19:.1f} '
                f'C {width * 0.54:.1f} {y + height * 0.215:.1f}, {width * 0.61:.1f} {y + height * 0.255:.1f}, {width * 0.69:.1f} {y + height * 0.30:.1f}"/>'
            )
        return (
            '<g class="direction-graphic direction-graphic--contours" fill="none" '
            f'stroke="{colors["accent"]}" stroke-width="{width * 0.003:.1f}" opacity="0.82">'
            f'{"".join(top_paths)}{"".join(bottom_paths)}</g>'
        )
    if direction == "statement":
        return (
            '<g class="direction-graphic direction-graphic--modules" fill="none" '
            f'stroke="{colors["accent"]}" stroke-width="{width * 0.105:.1f}" opacity="0.96">'
            f'<path class="module module--top" d="M {width * 0.75:.1f} {-height * 0.05:.1f} '
            f'V {height * 0.20:.1f} Q {width * 0.75:.1f} {height * 0.285:.1f} {width * 0.84:.1f} {height * 0.285:.1f} H {width * 1.06:.1f}"/>'
            f'<path class="module module--bottom" d="M {-width * 0.06:.1f} {height * 0.75:.1f} '
            f'H {width * 0.31:.1f} Q {width * 0.445:.1f} {height * 0.75:.1f} {width * 0.445:.1f} {height * 0.875:.1f} V {height * 1.06:.1f}"/>'
            '</g>'
        )
    dots: list[str] = []
    for row in range(6):
        for column in range(6):
            dots.append(
                f'<circle class="field-dot field-dot--top" cx="{width * (0.69 + column * 0.058):.1f}" '
                f'cy="{height * (0.02 + row * 0.032):.1f}" r="{max(2.0, width * 0.003):.1f}"/>'
            )
            dots.append(
                f'<circle class="field-dot field-dot--bottom" cx="{width * (0.04 + column * 0.058):.1f}" '
                f'cy="{height * (0.80 + row * 0.032):.1f}" r="{max(2.0, width * 0.003):.1f}"/>'
            )
    return (
        '<g class="direction-graphic direction-graphic--field" '
        f'fill="{colors["primary"]}" opacity="0.9">{"".join(dots)}</g>'
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
    family = html.escape(brand["font"]["family"], quote=True)
    lines = content["lines"]
    emphasis = content.get("emphasis", "")
    styles = content.get("styles")
    attribution = content["attribution"].get("label", "")
    use_quotes = content["use_quotation_marks"]
    options = {**(data.get("presentation") or {}), **(render_options or {})}
    logo_mode = options.get("logo_mode", "auto")
    graphic_mode = options.get("graphic_mode", "auto")
    graphic = direction_graphic(
        direction, width=width, height=height, colors=colors, enabled=graphic_mode != "hidden"
    )
    show_quotes = bool(options.get("show_quotation_marks", use_quotes)) and use_quotes
    vertical_position = options.get("vertical_position", "center")
    vertical_offset = {"upper": -0.075, "center": 0.0, "lower": 0.075}.get(vertical_position, 0.0) * height
    safe = width * 0.085
    css = (
        font_css(brand["font"], manifest_dir)
        + f".quote{{font-family:'{family}',sans-serif;font-weight:500;font-synthesis:weight;letter-spacing:-0.018em;}}"
        + f".meta{{font-family:'{family}',sans-serif;font-weight:500;letter-spacing:0.08em;}}"
        + f".marks{{font-family:'{family}',sans-serif;font-weight:700;font-size:{width * 0.17:.1f}px;}}"
    )

    if direction == "editorial":
        background = colors["background"]
        quote_color = colors["primary"]
        font_size = font_size_override or fitted_font_size(
            lines, width - 2 * safe, height * 0.40, width * 0.066
        )
        line_height = font_size * 1.13
        block_height = line_height * len(lines)
        start_y = height * 0.40 - block_height * 0.08 + vertical_offset
        logo = "" if logo_mode == "hidden" else logo_image(
            logo_data(brand, manifest_dir, light=False), x=safe, y=safe, width=width * 0.23
        )
        quote = text_block(
            lines, x=safe, y=start_y, font_size=font_size, line_height=line_height,
            color=quote_color, emphasis=emphasis, emphasis_color=quote_color,
            styles=styles, highlight_color=colors["accent"]
        )
        marks = quote_marks(
            show_quotes, color=colors["accent"], open_x=safe - width * 0.02, open_y=start_y - width * 0.11,
            close_x=width * 0.66, close_y=start_y + block_height + width * 0.06
        )
        body = (
            f'<rect width="{width}" height="{height}" fill="{background}"/>'
            f'{graphic}{logo}{marks}{quote}'
            f'<text class="meta" x="{width - safe}" y="{height - safe}" text-anchor="end" font-size="{width * 0.028:.1f}" fill="{colors["text"]}">{html.escape(attribution)}</text>'
        )
    elif direction == "statement":
        background = colors["primary"]
        quote_color = colors["background"]
        statement_safe = width * 0.055
        poster_lines = statement_visual_lines(lines, width, height)
        strong_rows = statement_strong_rows(poster_lines, styles, emphasis)
        font_size = font_size_override or statement_fitted_font_size(
            poster_lines, strong_rows, width, height
        )
        start_y = height * 0.265 + vertical_offset
        has_light_logo = bool((brand.get("logo") or {}).get("light_path"))
        logo = "" if logo_mode == "hidden" else logo_image(
            logo_data(brand, manifest_dir, light=True),
            x=statement_safe,
            y=safe,
            width=width * 0.23,
            filter_value="" if has_light_logo else "brightness(0) invert(1)",
        )
        quote = statement_text_block(
            poster_lines, x=statement_safe, y=start_y, font_size=font_size,
            color=quote_color, emphasis=emphasis, emphasis_color=colors["accent"],
            strong_rows=strong_rows, styles=styles, highlight_color=colors["accent"]
        )
        body = (
            f'<rect width="{width}" height="{height}" fill="{background}"/>'
            f'{graphic}{logo}{quote}'
            f'<text class="meta" x="{width - statement_safe}" y="{height - safe}" text-anchor="end" font-size="{width * 0.028:.1f}" fill="{colors["background"]}">{html.escape(attribution)}</text>'
        )
    else:
        background = colors["accent"]
        panel_x = safe
        panel_y = height * 0.085
        panel_width = width - 2 * safe
        panel_height = height * 0.83
        inner = width * 0.06
        quote_indent = width * 0.075
        font_size = font_size_override or fitted_font_size(
            lines, panel_width - 2 * inner - quote_indent, panel_height * 0.30, width * 0.058
        )
        line_height = font_size * 1.14
        block_height = line_height * len(lines)
        start_y = panel_y + panel_height * 0.50 + vertical_offset
        logo = "" if logo_mode == "hidden" else logo_image(
            logo_data(brand, manifest_dir, light=False),
            x=panel_x + inner,
            y=panel_y + height * 0.045,
            width=width * 0.25,
        )
        quote = text_block(
            lines, x=panel_x + inner + quote_indent, y=start_y, font_size=font_size, line_height=line_height,
            color=colors["primary"], emphasis=emphasis, emphasis_color=colors["primary"],
            styles=styles, highlight_color=colors["accent"]
        )
        source = data.get("source") or {}
        source_title = source.get("title", "")
        source_label = source.get("label") or source_title
        evidence_label = EVIDENCE_LABELS.get(content.get("evidence_status"), "STATO NON INDICATO")
        locator_label = source.get("evidence_locator") or source_label
        source_y = panel_y + panel_height * 0.205
        rule_y = source_y + height * 0.018
        evidence_y = panel_y + panel_height * 0.275
        locator_y = panel_y + panel_height * 0.32
        bar_y = start_y - font_size * 0.82
        bar_height = block_height - line_height + font_size * 1.10
        body = (
            f'<rect width="{width}" height="{height}" fill="{background}"/>'
            f'{graphic}'
            f'<rect class="source-panel" x="{panel_x}" y="{panel_y}" width="{panel_width}" height="{panel_height}" fill="{colors["background"]}"/>'
            f'{logo}'
            f'<text class="meta source-label" x="{panel_x + inner}" y="{source_y:.1f}" font-size="{width * 0.022:.1f}" fill="{colors["primary"]}">{html.escape(source_label.upper())}</text>'
            f'<line class="source-rule" x1="{panel_x + inner}" y1="{rule_y:.1f}" x2="{panel_x + inner + width * 0.075:.1f}" y2="{rule_y:.1f}" stroke="{colors["primary"]}" stroke-width="{width * 0.003:.1f}"/>'
            f'<text class="meta evidence-label" x="{panel_x + inner}" y="{evidence_y:.1f}" font-size="{width * 0.019:.1f}" fill="{colors["text"]}">{evidence_label}</text>'
            f'<text class="meta evidence-locator" x="{panel_x + inner}" y="{locator_y:.1f}" font-size="{width * 0.017:.1f}" fill="{colors["text"]}">{html.escape(locator_label)}</text>'
            f'<rect class="source-bar" x="{panel_x + inner}" y="{bar_y:.1f}" width="{width * 0.009:.1f}" height="{bar_height:.1f}" fill="{colors["primary"]}"/>'
            f'{quote}'
            f'<text class="meta attribution" x="{panel_x + panel_width - inner}" y="{panel_y + panel_height - height * 0.05:.1f}" text-anchor="end" font-size="{width * 0.024:.1f}" fill="{colors["text"]}">{html.escape(attribution)}</text>'
        )

    title = f"Quote card {direction} — {brand['name']}"
    description = f"{content['text']} — {attribution}" if attribution else content["text"]
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


def convert_with_sharp(svg_path: Path, png_path: Path, node: Path, node_modules: Path, width: int, height: int) -> None:
    helper = Path(__file__).with_name("svg_to_png.cjs")
    env = os.environ.copy()
    env["NODE_PATH"] = str(node_modules)
    subprocess.run(
        [str(node), str(helper), str(svg_path), str(png_path), str(width), str(height)],
        check=True,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


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
            converted = False
            if args.node and args.node_modules and args.node.is_file() and args.node_modules.is_dir():
                try:
                    convert_with_sharp(
                        svg_path,
                        png_path,
                        args.node.resolve(),
                        args.node_modules.resolve(),
                        data["canvas"]["width"],
                        data["canvas"]["height"],
                    )
                    converted = True
                except (OSError, subprocess.CalledProcessError):
                    converted = False
            if converted:
                png_paths.append(png_path)
            elif args.png == "required":
                print(json.dumps({"valid": False, "errors": [{"path": "output", "code": "png_unavailable", "message": "Conversione PNG non disponibile."}]}, ensure_ascii=False, indent=2))
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
