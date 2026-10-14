#!/usr/bin/env python3
"""MCP-facing quote-card adapter built on the canonical renderer."""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Mapping

import render_quote_card as renderer
import inspect_render as inspector
from grammar_sessions import proposal_metadata
from visual_grammars import demo_compositions, normalize_composition, normalize_grammar_presentation, variation_compositions


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
    "9x16": {"id": "9x16", "width": 1440, "height": 2560},
}
DEFAULT_FORMAT = "4x5"
MAX_TEXT_LENGTH = 600
MAX_ATTRIBUTION_LENGTH = 160
MAX_STYLES = 64
VALID_TRANSFORMATIONS = {"VERBATIM", "EDITED", "PARAPHRASE", "AI_GENERATED"}
VALID_EVIDENCE_STATUSES = {"VERIFIED", "USER_SUPPLIED", "UNVERIFIED", "CONFLICT"}
VALID_DIRECTIONS = {"editorial", "statement", "contextual"}
VALID_STYLE_TYPES = {"bold", "italic", "underline", "highlight", "accent", "outline", "size"}
GRAMMAR_FIELDS = ("visual_grammar", "composition", "quote_font_size", "author_font_size")
MANIFEST_VISUAL_CODES = {"contrast", "gradient_contrast"}
TECHNICAL_RENDER_CODES = {"svg_invalid", "ribbon_geometry_missing"}
VALID_GRAPHIC_MODES = {"auto", "hidden"}
GRAPHIC_VARIANTS = renderer.GRAPHIC_VARIANTS
VALID_VERTICAL_POSITIONS = {"upper", "center", "lower"}
PALETTE_COLOR_KEYS = ("primary", "accent", "background", "text")
HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")


def _issue(path: str, code: str, message: str) -> dict[str, str]:
    return {"path": path, "code": code, "message": message}


def _text(value: Any, path: str, maximum: int, *, required: bool = False, trim: bool = True) -> tuple[str, list[dict[str, str]]]:
    if not isinstance(value, str):
        return "", [_issue(path, "type", "Must be a string.")]
    value = value.strip() if trim else value
    if required and not value.strip():
        return "", [_issue(path, "required", "Must be a non-empty string.")]
    if len(value) > maximum:
        return value, [_issue(path, "length", f"Must not exceed {maximum} characters.")]
    return value, []


def _lines(value: Any, text: str) -> tuple[list[str], list[dict[str, str]]]:
    if value is None:
        value = text.splitlines() if "\n" in text or "\r" in text else [text]
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
        expected = {"start", "end", "type", "scale"} if isinstance(item, dict) and item.get("type") == "size" else {"start", "end", "type"}
        if not isinstance(item, dict) or set(item) != expected:
            errors.append(_issue(path, "shape", "Every range requires start, end, and type; size also requires scale."))
            continue
        start, end, kind = item["start"], item["end"], item["type"]
        if not isinstance(start, int) or isinstance(start, bool) or not isinstance(end, int) or isinstance(end, bool):
            errors.append(_issue(path, "offset", "Start and end must be integers."))
            continue
        if not 0 <= start < end <= len(text):
            errors.append(_issue(path, "range", "The range must fall within the current text."))
        if not isinstance(kind, str) or kind not in VALID_STYLE_TYPES:
            errors.append(_issue(f"{path}.type", "enum", "Unsupported style type."))
        result = {"start": start, "end": end, "type": kind}
        if kind == "size":
            scale = item["scale"]
            if isinstance(scale, bool) or not isinstance(scale, (int, float)) or not math.isfinite(scale) or not .5 <= scale <= 2.5:
                errors.append(_issue(f"{path}.scale", "range", "Use a scale between 0.5 and 2.5."))
            result["scale"] = scale
        normalized.append(result)
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
            mapped.append({**style, "start": start, "end": end})
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


def _grammar(payload: Mapping[str, Any], text: str, seed: int) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, str]]]:
    """Accept authored scenes, while identifying deterministic demonstrations."""
    value = payload.get("presentation")
    if value is not None and not isinstance(value, Mapping):
        return {}, {}, [_issue("presentation", "type", "Presentation must be an object.")]
    presentation = {key: value[key] for key in GRAMMAR_FIELDS if value and key in value and value[key] is not None}
    for key in GRAMMAR_FIELDS:
        if key in payload:
            presentation.pop(key, None)
            if payload[key] is not None:
                presentation[key] = payload[key]
    try:
        proposals = proposal_metadata({key: payload[key] for key in ("composition_candidates", "proposal_source")
                                       if key in payload and payload[key] is not None})
        candidates = proposals.get("composition_candidates", [])
        reuse = payload.get("reuse_composition")
        if reuse is not None:
            reuse = normalize_composition(reuse)
        if presentation.get("visual_grammar") == "ribbons":
            if "composition" not in presentation:
                if not candidates:
                    candidates = (variation_compositions(reuse, text, seed) if reuse is not None
                                  else demo_compositions(text, seed))
                    proposals = {"composition_candidates": candidates, "proposal_source": "demo"}
                presentation["composition"] = copy.deepcopy(candidates[0])
            if proposals.get("proposal_source") is None:
                proposals["proposal_source"] = "model"
        elif candidates or reuse is not None:
            raise ValueError("Compositions require visual_grammar='ribbons'.")
        return normalize_grammar_presentation(presentation), proposals, []
    except (TypeError, ValueError) as error:
        return {}, {}, [_issue("presentation", "grammar", str(error))]


def build_manifest(payload: Mapping[str, Any], manifest_dir: Path | None = None) -> tuple[dict[str, Any] | None, list[dict[str, str]]]:
    """Turn the small MCP input into the renderer's visual manifest contract."""
    if not isinstance(payload, Mapping):
        return None, [_issue("$", "type", "Input must be a JSON object.")]

    text, errors = _text(payload.get("text"), "text", MAX_TEXT_LENGTH, required=True, trim=False)
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
    graphic_seed = payload.get("graphic_seed", 0)
    if not renderer.graphic_seed_allowed(graphic_seed):
        errors.append(_issue("graphic_seed", "range", "Use an integer between 0 and 999999."))
    vertical_position = payload.get("vertical_position", "center")
    if vertical_position not in VALID_VERTICAL_POSITIONS:
        errors.append(_issue("vertical_position", "enum", "Use upper, center, or lower."))
    text_scale = payload.get("text_scale", 1.0)
    if isinstance(text_scale, bool) or not isinstance(text_scale, (int, float)) or not 0.8 <= text_scale <= 1.0:
        errors.append(_issue("text_scale", "range", "Scale must be between 0.80 and 1.00."))
    format_id = payload.get("format", DEFAULT_FORMAT)
    if format_id not in FORMATS:
        errors.append(_issue("format", "enum", "Use the 4x5, 1x1, or 9x16 format."))

    grammar, proposals, grammar_errors = _grammar(payload, text, graphic_seed if renderer.graphic_seed_allowed(graphic_seed) else 0)
    errors.extend(grammar_errors)
    if any(style.get("type") == "size" for style in styles or []) and grammar.get("visual_grammar") != "ribbons":
        errors.append(_issue("styles", "grammar", "Local size ranges require the ribbons visual grammar."))

    brand, palette_errors = _palette(payload.get("palette"))
    errors.extend(palette_errors)
    if grammar.get("visual_grammar") == "ribbons":
        # Native geometry measures the same portable font that the SVG draws.
        # Legacy styles retain their existing Arial default.
        font_dir = Path(__file__).resolve().parent.parent / "assets" / "card-editor" / "fonts"
        brand["font"] = {"family": "Barlow", "regular_path": str(font_dir / "Barlow-Regular.ttf"),
                         "bold_path": str(font_dir / "Barlow-Bold.ttf")}

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
        "presentation": {
            "logo_mode": "hidden",
            "graphic_mode": graphic_mode,
            "graphic_variant": graphic_variant,
            "graphic_seed": graphic_seed,
            **grammar,
        },
        **proposals,
        "brand": brand,
        "source": {"title": "MCP input", "locator": "mcp://quote-card-builder/preview"},
        "output": {"basename": "quote-card-preview"},
    }
    return manifest, []


def _scene_preview(manifest: dict[str, Any], base_dir: Path, options: dict[str, Any]) -> dict[str, Any]:
    """Render exact proof bytes; visual assessment is always advisory."""
    layout = (renderer.ribbon_layout(manifest, base_dir, render_options=options)
              if manifest["presentation"].get("visual_grammar") == "ribbons" else None)
    svg = renderer.render_svg(manifest, base_dir, manifest["direction"], render_options=options)
    findings = inspector.inspect_render(svg, manifest["direction"], manifest["canvas"]["width"],
                                        manifest["canvas"]["height"], vertical_position=options["vertical_position"],
                                        ribbon_layout=layout)
    errors = [_issue("render", item["code"], item["message"]) for item in findings
              if item["code"] in TECHNICAL_RENDER_CODES]
    warnings = (layout or {}).get("warnings", []) + [item for item in findings if item["code"] not in TECHNICAL_RENDER_CODES]
    return {"svg": svg, "svg_sha256": hashlib.sha256(svg.encode("utf-8")).hexdigest(),
            "ribbon_layout": layout, "warnings": warnings, "errors": errors}


def _advisories(items: list[dict[str, Any]]) -> list[dict[str, str]]:
    result = []
    seen = set()
    for item in items:
        key = (item["code"], item["message"])
        if key not in seen:
            result.append({"path": item.get("path", "render"), "code": item["code"],
                           "message": item["message"], "severity": "advisory"})
            seen.add(key)
    return result


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
    validation_manifest = copy.deepcopy(manifest)
    # The proof validator historically accepts 4:5 and square. Validate the
    # same data against a supported reference canvas, then render the exact
    # selected story dimensions; no schema or quality error is discarded.
    if selected_format["id"] == "9x16":
        validation_manifest["canvas"]["height"] = 1800
    validation = renderer.validate_visual_manifest(validation_manifest, base_dir)
    validation_errors = [item for item in validation if item["code"] not in MANIFEST_VISUAL_CODES]
    quality_warnings = [item for item in validation if item["code"] in MANIFEST_VISUAL_CODES]
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
            "warnings": _advisories(quality_warnings),
            "errors": validation_errors,
            "editorial_responsibility": "caller",
        }

    options = {"vertical_position": vertical_position, "text_scale": float(text_scale)}
    scene = _scene_preview(manifest, base_dir, options)
    svg = scene["svg"]
    composition_previews = []
    for composition in manifest.get("composition_candidates", []):
        candidate = copy.deepcopy(manifest)
        candidate["presentation"]["composition"] = composition
        preview = (scene if composition == manifest["presentation"].get("composition")
                   else _scene_preview(candidate, base_dir, options))
        composition_previews.append({"id": composition["id"], "name": composition.get("name", composition["id"]),
                                     "svg": preview["svg"], "svg_sha256": preview["svg_sha256"],
                                     "ribbon_layout": preview["ribbon_layout"],
                                     "warnings": _advisories(preview["warnings"])})
    alt_text = manifest["content"].get("alt_text") or renderer.default_alt_text(
        manifest["content"]["text"], manifest["content"]["attribution"].get("label", ""), manifest.get("source")
    )
    digest = scene["svg_sha256"]
    return {
        "valid": not scene["errors"],
        "rendered": not scene["errors"],
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
        "warnings": _advisories(quality_warnings + scene["warnings"]),
        "errors": scene["errors"],
        **{key: copy.deepcopy(manifest["presentation"].get(key)) for key in GRAMMAR_FIELDS},
        "composition_candidates": copy.deepcopy(manifest.get("composition_candidates", [])),
        "proposal_source": manifest.get("proposal_source"),
        "ribbon_layout": scene["ribbon_layout"],
        "composition_previews": composition_previews,
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
