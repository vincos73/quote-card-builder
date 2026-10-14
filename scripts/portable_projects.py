"""Conversions for the portable personal-base and card-project wire formats."""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import portable_brand

BASE_SCHEMA = "qcb-personal-base"
PROJECT_SCHEMA = "qcb-card-project"


def _design(manifest: dict[str, Any], base_dir: Path, format_id: str | None = None) -> dict[str, Any]:
    presentation = manifest["presentation"]
    fmt = next((item for item in manifest["formats"] if item["id"] == format_id), None)
    fmt = fmt or next((item for item in manifest["formats"] if item["id"] == "4x5"), manifest["formats"][0])
    kit = portable_brand.kit_from_brand(manifest["brand"], base_dir)
    result = {"format": fmt["id"], "direction": manifest["direction"],
              "graphic_mode": presentation.get("graphic_mode", "auto"),
              "graphic_variant": presentation.get("graphic_variant", "default"),
              "graphic_seed": presentation.get("graphic_seed", 0), "text_scale": fmt["text_scale"],
              "vertical_position": fmt["vertical_position"], "profile_mode": "custom",
              "palette": {"name": kit["name"], "colors": copy.deepcopy(manifest["brand"]["colors"])},
              "brand_kit": kit, "visual_grammar": presentation.get("visual_grammar"),
              "composition": copy.deepcopy(presentation.get("composition")),
              "logo_mode": presentation.get("logo_mode", "auto"),
              "quote_font_size": presentation.get("quote_font_size"),
              "author_font_size": presentation.get("author_font_size")}
    return {key: value for key, value in result.items() if value is not None}


def export_base(name: str, manifest: dict[str, Any], base_dir: Path, format_id: str | None = None) -> dict[str, Any]:
    return {"schema": BASE_SCHEMA, "schemaVersion": 2, "name": name,
            "design": _design(manifest, base_dir, format_id)}


def export_project(name: str, manifest: dict[str, Any], base_dir: Path, format_id: str | None = None) -> dict[str, Any]:
    design = _design(manifest, base_dir, format_id)
    content = manifest["content"]
    fmt = next(item for item in manifest["formats"] if item["id"] == design["format"])
    project_text, project_styles = _project_text_and_styles(content["text"], fmt["lines"], content.get("styles", []))
    draft = {**design, "text": project_text, "lines": copy.deepcopy(fmt["lines"]),
             "attribution": content.get("attribution", {}).get("label", ""),
             "styles": project_styles,
             "transformation": content.get("transformation"),
             "evidence_status": content.get("evidence_status"),
             "alt_text": content.get("alt_text", ""),
             "composition_candidates": copy.deepcopy(manifest.get("composition_candidates", [])),
             "proposal_source": manifest.get("proposal_source")}
    result = {"schema": PROJECT_SCHEMA, "schemaVersion": 1, "name": name, "draft": draft}
    if isinstance(manifest.get("source"), dict):
        result["editorial"] = {"source": copy.deepcopy(manifest["source"])}
    return result


def import_design(value: Any, asset_dir: Path, current: dict[str, Any], *, project: bool) -> dict[str, Any]:
    """Map a portable object onto the active native manifest's stable fields."""
    if not isinstance(value, dict): raise ValueError("Portable file must be an object")
    if project:
        if value.get("schema") != PROJECT_SCHEMA or value.get("schemaVersion") != 1 or not isinstance(value.get("draft"), dict):
            raise ValueError("Unsupported card project schema")
        fields = value["draft"]
    else:
        if value.get("schema") != BASE_SCHEMA or value.get("schemaVersion") != 2 or not isinstance(value.get("design"), dict):
            raise ValueError("Unsupported personal base schema")
        fields = value["design"]
    raw_kit = fields.get("brand_kit")
    if raw_kit is not None:
        kit = portable_brand.normalize_brand_kit(raw_kit)
        if isinstance(fields.get("palette"), dict) and isinstance(fields["palette"].get("colors"), dict):
            kit["colors"] = copy.deepcopy(fields["palette"]["colors"])
        brand = portable_brand.brand_from_kit(kit, asset_dir)
    else:
        palette = fields.get("palette")
        colors = palette.get("colors") if isinstance(palette, dict) else None
        if not isinstance(colors, dict):
            colors = copy.deepcopy(current["brand"]["colors"])
        name = palette.get("name") if isinstance(palette, dict) else None
        brand = {"name": name or value.get("name") or "Imported brand", "colors": copy.deepcopy(colors)}
        if fields.get("visual_grammar") not in {"ribbons", "urban"}:
            brand["font"] = {"family": "Arial"}
    if fields.get("visual_grammar") in {"ribbons", "urban"} and not brand.get("font", {}).get("regular_path"):
        font_dir = Path(__file__).resolve().parent.parent / "assets" / "card-editor" / "fonts"
        brand["font"] = {"family": "Barlow", "regular_path": str(font_dir / "Barlow-Regular.ttf"),
                         "bold_path": str(font_dir / "Barlow-Bold.ttf")}
    result = copy.deepcopy(current)
    result["brand"] = brand
    result["direction"] = fields.get("direction", result["direction"])
    fmt_id = fields.get("format", "4x5")
    formats = result["formats"]
    chosen = next((item for item in formats if item["id"] == fmt_id), formats[0])
    chosen["text_scale"] = fields.get("text_scale", chosen["text_scale"])
    chosen["vertical_position"] = fields.get("vertical_position", chosen["vertical_position"])
    presentation = result["presentation"]
    presentation["graphic_mode"] = fields.get("graphic_mode", "auto")
    presentation["logo_mode"] = fields.get("logo_mode", "auto")
    presentation["graphic_variant"] = fields.get("graphic_variant", "default")
    presentation["graphic_seed"] = fields.get("graphic_seed", 0)
    if fields.get("visual_grammar") in {"ribbons", "urban"}:
        presentation["visual_grammar"] = fields["visual_grammar"]
    else:
        presentation.pop("visual_grammar", None)
    for key in ("composition", "quote_font_size", "author_font_size"):
        if key in fields: presentation[key] = copy.deepcopy(fields[key])
        else: presentation.pop(key, None)
    if project:
        content = result["content"]
        raw_text = fields.get("text", content["text"])
        content["text"], mapped_styles = _canonicalize_text_and_styles(raw_text, fields.get("styles", []))
        content["attribution"] = {**content.get("attribution", {}), "label": fields.get("attribution", "")}
        content.update(styles=mapped_styles, emphasis="", styles_customized=True)
        for key in ("transformation", "evidence_status", "alt_text"):
            if key in fields: content[key] = copy.deepcopy(fields[key])
        chosen["lines"] = copy.deepcopy(fields.get("lines", [content["text"]]))
        if "composition_candidates" in fields: result["composition_candidates"] = copy.deepcopy(fields["composition_candidates"])
        if "proposal_source" in fields: result["proposal_source"] = fields["proposal_source"]
        editorial = value.get("editorial")
        source = editorial.get("source") if isinstance(editorial, dict) else None
        result["source"] = copy.deepcopy(source) if isinstance(source, dict) else {"title": "Portable project", "locator": "user-supplied"}
    return result


def _project_text_and_styles(text: str, lines: list[str], styles: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    """Expand canonical content offsets into the portable editor's raw rows.

    MCP project files address styles in editor text, where blank rows and
    Unicode code points count. Local manifests address the normalized text.
    """
    raw = "\n".join(lines)
    canonical = " ".join(raw.split())
    source = " ".join(text.split())
    if canonical != source:
        return text, copy.deepcopy(styles)
    offsets: dict[int, int] = {}
    canonical_index = 0
    index = 0
    while index < len(raw):
        if raw[index].isspace():
            end = index + 1
            while end < len(raw) and raw[end].isspace():
                end += 1
            if canonical_index and end < len(raw):
                offsets[canonical_index] = index
                canonical_index += 1
                offsets[canonical_index] = end
            index = end
        else:
            offsets[canonical_index] = index
            canonical_index += 1
            index += 1
            offsets[canonical_index] = index
    mapped = []
    for item in styles:
        start, end = item["start"], item["end"]
        if start in offsets and end in offsets and offsets[start] < offsets[end]:
            mapped.append({**item, "start": offsets[start], "end": offsets[end]})
    return raw, mapped


def _canonicalize_text_and_styles(raw: Any, styles: Any) -> tuple[str, list[dict[str, Any]]]:
    """Map web editor code-point offsets onto normalized local text offsets."""
    if not isinstance(raw, str):
        return "", copy.deepcopy(styles) if isinstance(styles, list) else []
    canonical = " ".join(raw.split())
    if not isinstance(styles, list):
        return canonical, []
    boundaries = [0] * (len(raw) + 1)
    offset = 0
    index = 0
    while index < len(raw):
        boundaries[index] = offset
        if raw[index].isspace():
            end = index + 1
            while end < len(raw) and raw[end].isspace():
                end += 1
            if offset and end < len(raw):
                offset += 1
            for boundary in range(index + 1, end + 1):
                boundaries[boundary] = offset
            index = end
        else:
            offset += 1
            index += 1
            boundaries[index] = offset
    result = []
    for item in styles:
        if not isinstance(item, dict):
            result.append(copy.deepcopy(item))
            continue
        start, end = item.get("start"), item.get("end")
        if (type(start) is not int or type(end) is not int or start < 0 or start >= end or end > len(raw)):
            result.append(copy.deepcopy(item))
            continue
        while start < end and raw[start].isspace():
            start += 1
        while end > start and raw[end - 1].isspace():
            end -= 1
        mapped_start, mapped_end = boundaries[start], boundaries[end]
        if mapped_start < mapped_end:
            result.append({**copy.deepcopy(item), "start": mapped_start, "end": mapped_end})
    return canonical, result
