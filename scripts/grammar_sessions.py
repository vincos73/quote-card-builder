"""Shared session data for model-authored visual grammar proposals."""

from __future__ import annotations

import copy
from typing import Any

from visual_grammars import normalize_composition


def complete_ribbon_formats(formats: list[dict[str, Any]], text: str) -> list[dict[str, Any]]:
    """Add missing social canvases without replacing the user's edited format."""
    by_id = {item["id"]: copy.deepcopy(item) for item in formats}
    base = by_id.get("4x5") or next(iter(by_id.values()), {})
    width = base.get("width", 1440)
    ratios = {"4x5": 5 / 4, "1x1": 1, "9x16": 16 / 9}
    for format_id, ratio in ratios.items():
        if format_id not in by_id:
            by_id[format_id] = {"id": format_id, "width": width, "height": round(width * ratio),
                                "lines": copy.deepcopy(base.get("lines", [text])),
                                "text_scale": 1.0, "vertical_position": "center"}
    return [by_id[format_id] for format_id in ratios]


def normalize_candidates(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not 1 <= len(value) <= 3:
        raise ValueError("composition_candidates: inserire da una a tre composizioni.")
    result = [normalize_composition(item) for item in value]
    if len({item["id"] for item in result}) != len(result):
        raise ValueError("composition_candidates: gli identificatori devono essere distinti.")
    return result


def proposal_metadata(data: dict[str, Any]) -> dict[str, Any]:
    """Validate proposal metadata without turning it into a reusable style."""
    result: dict[str, Any] = {}
    if "composition_candidates" in data:
        # A faithfully reopened card needs no gallery. The editor represents
        # that absence as [], whereas authored proposal batches stay strict.
        result["composition_candidates"] = ([] if data["composition_candidates"] == []
                                             else normalize_candidates(data["composition_candidates"]))
    if "proposal_source" in data:
        if data["proposal_source"] not in {"model", "demo"}:
            raise ValueError("proposal_source: usare model o demo.")
        result["proposal_source"] = data["proposal_source"]
    return copy.deepcopy(result)


def reset_content_for_reuse(candidate: dict[str, Any], text: str, attribution: str | None = None) -> None:
    """A new quote never inherits offsets or editorial evidence of the old one."""
    normalized = " ".join(text.split()) if isinstance(text, str) else ""
    if not normalized or len(normalized) > 600:
        raise ValueError("La nuova citazione deve contenere da 1 a 600 caratteri.")
    content = candidate["content"]
    changed = normalized != " ".join(content.get("text", "").split())
    if changed:
        content.update(text=normalized, lines=[normalized], styles=[], styles_customized=True,
                       emphasis="", alt_text="", transformation="EDITED", evidence_status="UNVERIFIED")
        candidate["source"] = {"title": "Nuovo testo fornito dall’utente", "locator": "user-supplied"}
        for item in candidate.get("formats", []):
            item["lines"] = [normalized]
        # Absolute sizes were interventions on the old content. The saved
        # composition/scale still defines the new quote's initial hierarchy.
        candidate.get("presentation", {}).pop("quote_font_size", None)
    if attribution is not None:
        if not isinstance(attribution, str) or len(attribution) > 160:
            raise ValueError("L’autore deve contenere al massimo 160 caratteri.")
        content["attribution"] = {"label": attribution.strip(), "role": "author" if attribution.strip() else "none"}
    elif changed:
        content["attribution"] = {"label": "", "role": "none"}
