#!/usr/bin/env python3
"""MCP-facing quote-card adapter built on the canonical renderer."""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

import render_quote_card as renderer


NEUTRAL_PROFILE = {
    "name": "Neutral profile",
    "colors": {
        "primary": "#072743",
        "accent": "#E3F4FF",
        "background": "#FEFDFB",
        "text": "#323232",
    },
    "font": {"family": "Arial"},
}
FORMATS = {
    "4x5": {"id": "4x5", "width": 1440, "height": 1800},
    "1x1": {"id": "1x1", "width": 1440, "height": 1440},
}
DEFAULT_FORMAT = "4x5"
MAX_TEXT_LENGTH = 600
MAX_ATTRIBUTION_LENGTH = 160
MAX_STYLES = 64
VALID_TRANSFORMATIONS = {"VERBATIM", "EDITED", "PARAPHRASE", "AI_GENERATED"}
VALID_EVIDENCE_STATUSES = {"VERIFIED", "USER_SUPPLIED", "UNVERIFIED", "CONFLICT"}
VALID_DIRECTIONS = {"editorial", "statement", "contextual"}
VALID_STYLE_TYPES = {"bold", "italic", "underline", "highlight", "accent", "outline"}
VALID_GRAPHIC_MODES = {"auto", "hidden"}
GRAPHIC_VARIANTS = {
    "editorial": {"default", "rhythm_lines"},
    "statement": {"default", "modules"},
    "contextual": {"default", "route_map"},
}
VALID_VERTICAL_POSITIONS = {"upper", "center", "lower"}
PALETTE_COLOR_KEYS = ("primary", "accent", "background", "text")
HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")


def _issue(path: str, code: str, message: str) -> dict[str, str]:
    return {"path": path, "code": code, "message": message}


def _text(value: Any, path: str, maximum: int, *, required: bool = False) -> tuple[str, list[dict[str, str]]]:
    if not isinstance(value, str):
        return "", [_issue(path, "type", "Must be a string.")]
    value = value.strip()
    if required and not value:
        return "", [_issue(path, "required", "Must be a non-empty string.")]
    if len(value) > maximum:
        return value, [_issue(path, "length", f"Must not exceed {maximum} characters.")]
    return value, []


def _lines(value: Any, text: str) -> tuple[list[str], list[dict[str, str]]]:
    if value is None:
        return [text], []
    if not isinstance(value, list) or not value:
        return [], [_issue("lines", "count", "Provide at least one line.")]
    if any(not isinstance(line, str) for line in value):
        return [], [_issue("lines", "type", "Every line must be a string.")]
    # Preserve authored hard rows (including blank spacer rows), but make the
    # text inside each row use the renderer's canonical whitespace contract.
    # Inline style offsets are defined against that same canonical text.
    lines = [renderer.normalize_spaces(line) for line in value]
    if renderer.normalize_spaces(" ".join(lines)) != renderer.normalize_spaces(text):
        return lines, [_issue("lines", "text_changed", "The line breaks do not reconstruct the text exactly.")]
    if not any(lines):
        return lines, [_issue("lines", "empty", "Provide at least one non-empty line.")]
    return lines, []


def _styles(value: Any, text: str) -> tuple[list[dict[str, Any]] | None, list[dict[str, str]]]:
    if value is None:
        return None, []
    if not isinstance(value, list) or len(value) > MAX_STYLES:
        return [], [_issue("styles", "count", f"Use a list with at most {MAX_STYLES} ranges.")]
    errors: list[dict[str, str]] = []
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        path = f"styles[{index}]"
        if not isinstance(item, dict) or set(item) != {"start", "end", "type"}:
            errors.append(_issue(path, "shape", "Every range requires start, end, and type."))
            continue
        start, end, kind = item["start"], item["end"], item["type"]
        if not isinstance(start, int) or isinstance(start, bool) or not isinstance(end, int) or isinstance(end, bool):
            errors.append(_issue(path, "offset", "Start and end must be integers."))
            continue
        if not 0 <= start < end <= len(text):
            errors.append(_issue(path, "range", "The range must fall within the current text."))
        if kind not in VALID_STYLE_TYPES:
            errors.append(_issue(f"{path}.type", "enum", "Unsupported style type."))
        normalized.append({"start": start, "end": end, "type": kind})
    return normalized, errors


def _canonical_text_and_styles(
    text: str, styles: list[dict[str, Any]] | None
) -> tuple[str, list[dict[str, Any]] | None]:
    """Map editor offsets onto the renderer's whitespace-normalized text.

    The iframe keeps newlines so the user can author hard rows. The renderer
    intentionally addresses styles on the canonical text, where every run of
    spaces/newlines is one separator. Without this small translation, every
    blank row shifts all later formatting ranges.
    """

    canonical_text = renderer.normalize_spaces(text)
    if styles is None:
        return canonical_text, None

    # Map every raw code-point boundary to the corresponding boundary in the
    # collapsed text. A whitespace run between two words contributes exactly
    # one canonical space; leading/trailing whitespace contributes none.
    boundaries = [0] * (len(text) + 1)
    canonical_offset = 0
    index = 0
    while index < len(text):
        boundaries[index] = canonical_offset
        if text[index].isspace():
            run_end = index + 1
            while run_end < len(text) and text[run_end].isspace():
                run_end += 1
            if canonical_offset and run_end < len(text):
                canonical_offset += 1
            for boundary in range(index + 1, run_end + 1):
                boundaries[boundary] = canonical_offset
            index = run_end
            continue
        canonical_offset += 1
        index += 1
        boundaries[index] = canonical_offset

    canonical_limit = len(canonical_text)
    mapped: list[dict[str, Any]] = []
    for style in styles:
        raw_start = style["start"]
        raw_end = style["end"]
        while raw_start < raw_end and text[raw_start].isspace():
            raw_start += 1
        while raw_end > raw_start and text[raw_end - 1].isspace():
            raw_end -= 1
        if raw_start >= raw_end:
            continue
        start = min(boundaries[raw_start], canonical_limit)
        end = min(boundaries[raw_end], canonical_limit)
        if start < end:
            mapped.append({"start": start, "end": end, "type": style["type"]})
    return canonical_text, mapped


def _palette(value: Any) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """Resolve an explicitly chosen palette without adding renderer logic."""
    if value is None:
        return copy.deepcopy(NEUTRAL_PROFILE), []
    if not isinstance(value, Mapping):
        return copy.deepcopy(NEUTRAL_PROFILE), [_issue("palette", "type", "The palette must be a JSON object.")]

    name = value.get("name", "Custom palette")
    errors: list[dict[str, str]] = []
    if not isinstance(name, str):
        errors.append(_issue("palette.name", "type", "The palette name must be a string."))
        name = "Custom palette"
    else:
        name = name.strip()
        if not name:
            errors.append(_issue("palette.name", "required", "Provide a palette name."))
        elif len(name) > 80:
            errors.append(_issue("palette.name", "length", "The palette name must not exceed 80 characters."))

    colors = value.get("colors")
    if not isinstance(colors, Mapping):
        errors.append(_issue("palette.colors", "type", "The palette requires primary, accent, background, and text colors."))
        colors = {}
    normalized_colors: dict[str, str] = {}
    for key in PALETTE_COLOR_KEYS:
        color = colors.get(key)
        if not isinstance(color, str) or not HEX_COLOR.fullmatch(color):
            errors.append(_issue(f"palette.colors.{key}", "color", "Use a hexadecimal #RRGGBB color."))
        else:
            normalized_colors[key] = color.upper()

    brand = copy.deepcopy(NEUTRAL_PROFILE)
    brand["name"] = name or "Custom palette"
    brand["colors"] = normalized_colors or copy.deepcopy(NEUTRAL_PROFILE["colors"])
    return brand, errors


def build_manifest(payload: Mapping[str, Any], manifest_dir: Path | None = None) -> tuple[dict[str, Any] | None, list[dict[str, str]]]:
    """Turn the small MCP input into the renderer's visual manifest contract."""
    if not isinstance(payload, Mapping):
        return None, [_issue("$", "type", "Input must be a JSON object.")]

    text, errors = _text(payload.get("text"), "text", MAX_TEXT_LENGTH, required=True)
    attribution, attribution_errors = _text(payload.get("attribution", ""), "attribution", MAX_ATTRIBUTION_LENGTH)
    errors.extend(attribution_errors)
    lines, line_errors = _lines(payload.get("lines"), text)
    errors.extend(line_errors)
    emphasis, emphasis_errors = _text(payload.get("emphasis", ""), "emphasis", MAX_TEXT_LENGTH)
    errors.extend(emphasis_errors)
    alt_text, alt_errors = _text(payload.get("alt_text", ""), "alt_text", renderer.ALT_TEXT_MAX_LENGTH)
    errors.extend(alt_errors)
    styles, style_errors = _styles(payload.get("styles"), text)
    errors.extend(style_errors)

    transformation = payload.get("transformation", "VERBATIM")
    if transformation not in VALID_TRANSFORMATIONS:
        errors.append(_issue("transformation", "enum", "Unsupported transformation."))
    evidence_status = payload.get("evidence_status", "USER_SUPPLIED")
    if evidence_status not in VALID_EVIDENCE_STATUSES:
        errors.append(_issue("evidence_status", "enum", "Unsupported evidence status."))
    direction = payload.get("direction", "editorial")
    if direction not in VALID_DIRECTIONS:
        errors.append(_issue("direction", "enum", "Unsupported direction."))
    graphic_mode = payload.get("graphic_mode", "auto")
    if graphic_mode not in VALID_GRAPHIC_MODES:
        errors.append(_issue("graphic_mode", "enum", "Use auto or hidden."))
    graphic_variant = payload.get("graphic_variant", "default")
    if graphic_variant not in GRAPHIC_VARIANTS.get(direction, set()):
        errors.append(_issue("graphic_variant", "enum", "The motif does not belong to the selected direction."))
    vertical_position = payload.get("vertical_position", "center")
    if vertical_position not in VALID_VERTICAL_POSITIONS:
        errors.append(_issue("vertical_position", "enum", "Use upper, center, or lower."))
    text_scale = payload.get("text_scale", 1.0)
    if isinstance(text_scale, bool) or not isinstance(text_scale, (int, float)) or not 0.8 <= text_scale <= 1.0:
        errors.append(_issue("text_scale", "range", "Scale must be between 0.80 and 1.00."))
    format_id = payload.get("format", DEFAULT_FORMAT)
    if format_id not in FORMATS:
        errors.append(_issue("format", "enum", "Use the 4x5 or 1x1 format."))

    brand, palette_errors = _palette(payload.get("palette"))
    errors.extend(palette_errors)

    if errors:
        return None, errors

    canonical_text, canonical_styles = _canonical_text_and_styles(text, styles)
    content: dict[str, Any] = {
        "text": canonical_text,
        "lines": lines,
        "transformation": transformation,
        "evidence_status": evidence_status,
        "emphasis": emphasis,
        "attribution": {"label": attribution, "role": "author" if attribution else "none"},
        "alt_text": alt_text,
        # The MCP editor starts visually neutral: only explicit style ranges
        # may accent words. Keep the intent explicit even though Manifesto is
        # now neutral in the canonical renderer as well.
        "styles_customized": True,
    }
    if canonical_styles is not None:
        content["styles"] = canonical_styles
    manifest = {
        "schema_version": "0.2",
        # The renderer's visual contract requires this state. The MCP tool
        # reports editorial responsibility separately and never claims source
        # verification merely because the contract is technically valid.
        "state": "contenuto_approvato",
        "content": content,
        "canvas": {"width": FORMATS[format_id]["width"], "height": FORMATS[format_id]["height"]},
        "direction": direction,
        "presentation": {"logo_mode": "hidden", "graphic_mode": graphic_mode, "graphic_variant": graphic_variant},
        "brand": brand,
        "source": {"title": "MCP input", "locator": "mcp://quote-card-builder/preview"},
        "output": {"basename": "quote-card-preview"},
    }
    return manifest, []


def preview_quote_card(payload: Mapping[str, Any], manifest_dir: Path | None = None) -> dict[str, Any]:
    """Validate and render one explicit-profile quote card with the real engine."""
    base_dir = (manifest_dir or Path(__file__).resolve().parent).resolve()
    format_id = payload.get("format", DEFAULT_FORMAT) if isinstance(payload, Mapping) else DEFAULT_FORMAT
    selected_format = FORMATS.get(format_id, FORMATS[DEFAULT_FORMAT])
    manifest, input_errors = build_manifest(payload, base_dir)
    vertical_position = payload.get("vertical_position", "center") if isinstance(payload, Mapping) else "center"
    text_scale = payload.get("text_scale", 1.0) if isinstance(payload, Mapping) else 1.0
    if input_errors:
        return {
            "valid": False,
            "rendered": False,
            "profile": NEUTRAL_PROFILE["name"],
            "palette": copy.deepcopy(NEUTRAL_PROFILE["colors"]),
            "direction": payload.get("direction", "editorial") if isinstance(payload, Mapping) else "editorial",
            "graphic_mode": payload.get("graphic_mode", "auto") if isinstance(payload, Mapping) else "auto",
            "graphic_variant": payload.get("graphic_variant", "default") if isinstance(payload, Mapping) else "default",
            "text_scale": payload.get("text_scale", 1.0) if isinstance(payload, Mapping) else 1.0,
            "vertical_position": payload.get("vertical_position", "center") if isinstance(payload, Mapping) else "center",
            "format": selected_format["id"],
            "width": selected_format["width"],
            "height": selected_format["height"],
            "svg": None,
            "svg_data_uri": None,
            "alt_text": "",
            "warnings": [],
            "errors": input_errors,
            "editorial_responsibility": "caller",
        }

    assert manifest is not None
    validation_errors = renderer.validate_visual_manifest(manifest, base_dir)
    if validation_errors:
        return {
            "valid": False,
            "rendered": False,
            "profile": manifest["brand"]["name"],
            "palette": copy.deepcopy(manifest["brand"]["colors"]),
            "direction": manifest["direction"],
            "graphic_mode": manifest["presentation"]["graphic_mode"],
            "graphic_variant": manifest["presentation"]["graphic_variant"],
            "text_scale": float(payload.get("text_scale", 1.0)),
            "vertical_position": payload.get("vertical_position", "center"),
            "format": selected_format["id"],
            "width": selected_format["width"],
            "height": selected_format["height"],
            "svg": None,
            "svg_data_uri": None,
            "alt_text": manifest["content"].get("alt_text", ""),
            "warnings": [],
            "errors": validation_errors,
            "editorial_responsibility": "caller",
        }

    svg = renderer.render_svg(
        manifest,
        base_dir,
        manifest["direction"],
        render_options={
            "vertical_position": vertical_position,
            "text_scale": float(text_scale),
        },
    )
    alt_text = manifest["content"].get("alt_text") or renderer.default_alt_text(
        manifest["content"]["text"], manifest["content"]["attribution"].get("label", ""), manifest.get("source")
    )
    digest = hashlib.sha256(svg.encode("utf-8")).hexdigest()
    return {
        "valid": True,
        "rendered": True,
        "profile": manifest["brand"]["name"],
        "palette": copy.deepcopy(manifest["brand"]["colors"]),
        "direction": manifest["direction"],
        "graphic_mode": manifest["presentation"]["graphic_mode"],
        "graphic_variant": manifest["presentation"]["graphic_variant"],
        "text_scale": float(payload.get("text_scale", 1.0)),
        "vertical_position": payload.get("vertical_position", "center"),
        "format": selected_format["id"],
        "width": selected_format["width"],
        "height": selected_format["height"],
        "svg": svg,
        "svg_data_uri": "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii"),
        "svg_sha256": digest,
        "alt_text": alt_text,
        "warnings": [],
        "errors": [],
        "editorial_responsibility": "caller",
        "declaration": {
            "transformation": manifest["content"]["transformation"],
            "evidence_status": manifest["content"]["evidence_status"],
            "attribution": manifest["content"]["attribution"],
        },
    }


def json_result(payload: Mapping[str, Any]) -> str:
    """Stable JSON representation useful for local smoke tests and debugging."""
    return json.dumps(preview_quote_card(payload), ensure_ascii=False, sort_keys=True)
