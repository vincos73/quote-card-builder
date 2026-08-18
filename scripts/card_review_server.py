#!/usr/bin/env python3
"""Local-only visual review server for Quote Card manifest 0.4."""

from __future__ import annotations

import argparse
import copy
import inspect
import json
import math
import os
import re
import secrets
import subprocess
import sys
import threading
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, unquote, urlparse

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
import render_quote_card as proof
import render_quote_card_pack as pack
import inspect_render as inspector
import apply_card_review as review_applier

MAX_BODY_BYTES = 250_000
MAX_TEXT_LENGTH = 600
ALT_TEXT_MAX_LENGTH = proof.ALT_TEXT_MAX_LENGTH
MAX_LINES = 40  # defensive ceiling only; real limit is available space, see render_quote_card.MAX_LINES
MAX_FORMATS = 3
FORMAT_IDS = {"4x5", "1x1", "9x16"}
DIRECTIONS = {"editorial", "statement", "contextual"}
POSITIONS = {"upper", "center", "lower"}
LOGO_MODES = {"auto", "hidden"}
GRAPHIC_MODES = {"auto", "hidden"}
OUTPUT_MODES = {"all", "4x5", "1x1", "9x16"}
SESSION_STATES = {"candidato_selezionato", "contenuto_approvato"}
CHATBOT_TIMEOUT_SECONDS = 300
CODEX_CLI_DEFAULT = Path("/Applications/ChatGPT.app/Contents/Resources/codex")
MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".ttf": "font/ttf",
    ".svg": "image/svg+xml",
}
GENERATED_MIME_TYPES = {
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".html": "text/html; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".zip": "application/zip",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Il manifest deve essere un oggetto JSON")
    return value


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(6)}.tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def chatbot_cli_path() -> Path | None:
    """Resolve the local Codex CLI used by the explicit chatbot handoff."""
    configured = os.environ.get("QUOTE_CARD_CODEX_BIN", "").strip()
    candidate = Path(configured) if configured else CODEX_CLI_DEFAULT
    return candidate.resolve() if candidate.is_file() else None


def chatbot_prompt(
    production_manifest: Path,
    output_dir: Path,
    node: Path | None,
    node_modules: Path | None,
) -> str:
    """Build a fixed, path-scoped prompt; browser content is never executable."""
    command = [
        sys.executable,
        str(SCRIPT_DIR / "render_quote_card_pack.py"),
        str(production_manifest),
        "--output-dir",
        str(output_dir),
        "--png",
        "required",
        "--svg",
        "discard",
    ]
    if node and node_modules:
        command.extend(["--node", str(node), "--node-modules", str(node_modules)])
    return (
        "Sei il chatbot di produzione di Quote Card Builder. "
        "Devi creare l'artefatto PNG della card approvata, senza modificare codice o manifest. "
        "Leggi il production manifest indicato e lancia esattamente il renderer locale con il comando seguente. "
        "Non chiedere conferme e non fare altre modifiche. Verifica alla fine che ogni formato richiesto abbia un file PNG.\n\n"
        f"Manifest: {production_manifest}\n"
        f"Output: {output_dir}\n"
        f"Comando: {' '.join(command)}\n"
    )


def approval_feedback(draft: dict[str, Any], base_revision: int, overall_note: str = "") -> dict[str, Any]:
    """The commit every generate request performs: freeze the current draft
    as an approved batch, built in one place so the feedback shape and
    apply_card_review's CONTENT_KEYS whitelist cannot silently drift apart.
    """
    return {
        "feedback_id": f"feedback-{secrets.token_hex(8)}", "submitted_at": now_iso(), "action": "approve",
        "base_revision": base_revision, "editorial_responsibility": "user",
        "content": {
            "text": draft["content"]["text"], "transformation": draft["content"]["transformation"],
            "evidence_status": draft["content"]["evidence_status"], "attribution": draft["content"]["attribution"],
            "alt_text": draft["content"].get("alt_text", ""), "styles": draft["content"].get("styles", []),
            "styles_customized": draft["content"].get("styles_customized", False), "declared_by": "user",
        },
        "direction": draft["direction"], "emphasis": draft["content"]["emphasis"], "presentation": draft["presentation"],
        "formats": [{"id": item["id"], "lines": item["lines"], "text_scale": item["text_scale"], "vertical_position": item["vertical_position"]} for item in draft["formats"]],
        "overall_note": overall_note,
    }


def record_and_apply_feedback(
    manifest_path: Path, session_dir: Path, feedback: dict[str, Any]
) -> dict[str, Any]:
    """Persist one validated batch and apply it before returning to the editor."""
    state_path = session_dir / "session-state.json"
    feedback_path = session_dir / "feedback.json"
    state_now = read_json(state_path)
    if state_now.get("last_feedback_id") != state_now.get("applied_feedback_id") and state_now.get("last_feedback_id"):
        raise RuntimeError("Il feedback precedente attende ancora di essere applicato")
    atomic_write_json(feedback_path, feedback)
    state_now.update({
        "manifest_revision": feedback["base_revision"],
        "last_feedback_id": feedback["feedback_id"],
    })
    atomic_write_json(state_path, state_now)
    return review_applier.apply_review(manifest_path, feedback_path, session_dir)


def error(errors: list[str], message: str) -> None:
    errors.append(message)


def normalized_text(value: Any) -> str:
    return " ".join(value.split()) if isinstance(value, str) else ""


def valid_lines(lines: Any, text: str, errors: list[str], field: str) -> list[str]:
    if not isinstance(lines, list) or not (1 <= len(lines) <= MAX_LINES) or not all(isinstance(v, str) for v in lines):
        error(errors, f"{field} deve contenere da 1 a {MAX_LINES} righe")
        return []
    if not any(line.strip() for line in lines):
        error(errors, f"{field} deve contenere almeno una riga di testo")
        return []
    normalized = " ".join(" ".join(lines).split())
    if normalized != " ".join(text.split()):
        error(errors, f"{field} deve ricostruire content.text senza modifiche")
    return lines


def validate_manifest(data: Any) -> list[str]:
    """Validate the immutable editorial and visual seed of a 0.4 manifest."""
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["Il manifest deve essere un oggetto"]
    if data.get("schema_version") != "0.4": error(errors, "schema_version deve essere 0.4")
    if data.get("state") not in SESSION_STATES: error(errors, "state deve essere candidato_selezionato o contenuto_approvato")
    if not isinstance(data.get("revision"), int) or isinstance(data.get("revision"), bool) or data["revision"] < 1: error(errors, "revision deve essere un intero >= 1")
    content = data.get("content")
    if not isinstance(content, dict):
        return errors + ["content deve essere un oggetto"]
    for key in ("text", "transformation", "evidence_status"):
        if not isinstance(content.get(key), str) or not content[key].strip(): error(errors, f"content.{key} è obbligatorio")
    if isinstance(content.get("text"), str) and len(content["text"]) > MAX_TEXT_LENGTH: error(errors, f"content.text supera {MAX_TEXT_LENGTH} caratteri")
    if content.get("transformation") not in proof.TRANSFORMATIONS: error(errors, "content.transformation non valida")
    if content.get("evidence_status") not in proof.EVIDENCE_STATUSES: error(errors, "content.evidence_status non valido")
    emphasis = content.get("emphasis", "")
    if not isinstance(emphasis, str) or (emphasis and emphasis not in content.get("text", "")): error(errors, "content.emphasis deve essere vuota o comparire nel testo")
    if "alt_text" in content:
        alt_text = content.get("alt_text")
        if not isinstance(alt_text, str): error(errors, "content.alt_text deve essere una stringa")
        elif len(alt_text) > ALT_TEXT_MAX_LENGTH: error(errors, f"content.alt_text non può superare {ALT_TEXT_MAX_LENGTH} caratteri")
    if "styles" in content:
        style_errors: list[dict[str, str]] = []
        proof.validate_text_styles(content["styles"], content.get("text", ""), style_errors)
        errors.extend(item["message"] for item in style_errors)
    attribution = content.get("attribution")
    if not isinstance(attribution, dict) or attribution.get("role") not in proof.ATTRIBUTION_ROLES: error(errors, "content.attribution deve essere valido")
    elif attribution.get("role") != "none" and (not isinstance(attribution.get("label"), str) or not attribution["label"].strip()): error(errors, "content.attribution.label è obbligatorio per il ruolo scelto")
    if data.get("direction") not in DIRECTIONS: error(errors, "direction non valida")
    presentation = data.get("presentation")
    if (
        not isinstance(presentation, dict)
        or presentation.get("logo_mode") not in LOGO_MODES
        or presentation.get("graphic_mode", "auto") not in GRAPHIC_MODES
        or not proof.graphic_variant_allowed(
            data.get("direction"), presentation.get("graphic_variant", "default")
        )
        or presentation.get("output_mode", "all") not in OUTPUT_MODES
    ): error(errors, "presentation non valida")
    formats = data.get("formats")
    if not isinstance(formats, list) or not (1 <= len(formats) <= MAX_FORMATS): return errors + ["formats deve contenere da 1 a 3 formati"]
    seen: set[str] = set()
    text = content.get("text", "") if isinstance(content.get("text"), str) else ""
    for index, item in enumerate(formats):
        field = f"formats[{index}]"
        if not isinstance(item, dict): error(errors, f"{field} deve essere un oggetto"); continue
        if item.get("id") not in FORMAT_IDS or item.get("id") in seen: error(errors, f"{field}.id non valido o duplicato")
        seen.add(item.get("id"))
        for size in ("width", "height"):
            if not isinstance(item.get(size), int) or isinstance(item.get(size), bool) or item[size] < 1: error(errors, f"{field}.{size} deve essere un intero positivo")
        expected_ratio = pack.FORMAT_RATIOS.get(item.get("id"))
        if expected_ratio and isinstance(item.get("width"), int) and isinstance(item.get("height"), int) and not math.isclose(item["width"] / item["height"], expected_ratio, rel_tol=.001): error(errors, f"{field} non rispetta il rapporto {item.get('id')}")
        valid_lines(item.get("lines"), text, errors, f"{field}.lines")
        scale = item.get("text_scale")
        if not isinstance(scale, (int, float)) or isinstance(scale, bool) or not .80 <= scale <= 1.08: error(errors, f"{field}.text_scale deve essere tra 0.80 e 1.00; i valori legacy fino a 1.08 vengono limitati al massimo sicuro")
        if item.get("vertical_position") not in POSITIONS: error(errors, f"{field}.vertical_position non valida")
    for key in ("brand", "source", "output"):
        if not isinstance(data.get(key), dict): error(errors, f"{key} deve essere un oggetto")
    return errors


def font_capabilities(manifest: dict[str, Any], manifest_dir: Path) -> dict[str, Any]:
    """Describe which inline treatments can be rendered predictably."""
    font = (manifest.get("brand") or {}).get("font") or {}

    def available(key: str) -> bool:
        value = font.get(key)
        return bool(
            isinstance(value, str)
            and value.strip()
            and proof.resolve_asset(value, manifest_dir).is_file()
        )

    system_font = str(font.get("family", "")).strip().casefold() == "arial"
    regular = available("regular_path")
    bold = available("bold_path")
    italic = available("italic_path")
    return {
        "family": font.get("family", "Font del brand"),
        "embedded": regular,
        "styles": {
            "bold": {"available": system_font or regular or bold, "exact": system_font or bold},
            "italic": {"available": system_font or italic, "exact": system_font or italic},
            "underline": {"available": True, "exact": True},
            "highlight": {"available": True, "exact": True},
            "accent": {"available": True, "exact": True},
            # Outline strokes the glyph outlines the regular face already
            # provides, so it needs no extra font file of its own.
            "outline": {"available": True, "exact": True},
        },
    }


THREAD_ID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def return_url_for_thread(thread_id: str | None) -> str | None:
    """Build a native Codex task link without accepting arbitrary URLs."""
    if thread_id is None:
        return None
    normalized = thread_id.strip()
    if not THREAD_ID_PATTERN.fullmatch(normalized):
        raise ValueError("return-thread-id non valido")
    return f"codex://threads/{normalized}"


def session_model(
    manifest: dict[str, Any], manifest_dir: Path | None = None,
    return_url: str | None = None,
) -> dict[str, Any]:
    """Return the selected candidate plus the values reviewable in the editor."""
    model = {key: copy.deepcopy(manifest[key]) for key in ("schema_version", "state", "revision", "content", "direction", "presentation", "formats", "brand", "source", "output")}
    model["font_capabilities"] = font_capabilities(manifest, manifest_dir or Path.cwd())
    model["return_url"] = return_url
    return model


def validate_draft(payload: Any, manifest: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict): raise ValueError("Il draft deve essere un oggetto JSON")
    allowed = {"base_revision", "text", "transformation", "evidence_status", "attribution", "direction", "emphasis", "styles", "styles_customized", "presentation", "formats", "action", "overall_note", "alt_text"}
    if set(payload) - allowed: raise ValueError("Il draft contiene campi non modificabili")
    if payload.get("base_revision") != manifest["revision"]: raise RuntimeError("La revisione di base non coincide con il manifest")
    candidate = copy.deepcopy(manifest)
    requested_text = normalized_text(payload.get("text", candidate["content"].get("text")))
    if not requested_text or len(requested_text) > MAX_TEXT_LENGTH:
        raise ValueError(f"text deve contenere da 1 a {MAX_TEXT_LENGTH} caratteri")
    alt_text = payload.get("alt_text", candidate["content"].get("alt_text", ""))
    if not isinstance(alt_text, str) or len(alt_text) > ALT_TEXT_MAX_LENGTH:
        raise ValueError(f"alt_text deve essere una stringa di al più {ALT_TEXT_MAX_LENGTH} caratteri")
    candidate["content"].update({
        "text": requested_text,
        "transformation": payload.get("transformation", candidate["content"].get("transformation")),
        "evidence_status": payload.get("evidence_status", candidate["content"].get("evidence_status")),
        "attribution": copy.deepcopy(payload.get("attribution", candidate["content"].get("attribution"))),
        "alt_text": alt_text.strip(),
        "declared_by": "user",
    })
    for key in ("direction", "emphasis", "styles", "styles_customized", "presentation", "formats"):
        if key in payload:
            if key == "emphasis": candidate["content"]["emphasis"] = payload[key]
            elif key == "styles": candidate["content"]["styles"] = copy.deepcopy(payload[key])
            elif key == "styles_customized": candidate["content"]["styles_customized"] = bool(payload[key])
            elif key == "presentation":
                candidate[key] = copy.deepcopy(payload[key])
            else: candidate[key] = payload[key]
    errors = validate_manifest(candidate)
    if errors: raise ValueError("; ".join(errors))
    return candidate


def render_preview(manifest: dict[str, Any], manifest_dir: Path) -> list[dict[str, Any]]:
    rendered: list[dict[str, Any]] = []
    supports_options = "render_options" in inspect.signature(proof.render_svg).parameters
    for item in manifest["formats"]:
        adapted = pack.proof_manifest_for_format(manifest, item)
        adapted["canvas"] = {"width": item["width"], "height": item["height"]}
        adapted["direction"] = manifest["direction"]
        adapted["content"]["emphasis"] = manifest["content"]["emphasis"]
        if manifest["presentation"]["logo_mode"] == "hidden": adapted["brand"] = copy.deepcopy(adapted["brand"]); adapted["brand"].pop("logo", None)
        size, fit_mode, requested_size, auto_fitted, maximum_size = pack.resolve_font_size(
            item["lines"], adapted, manifest_dir, manifest["direction"],
            item["width"], item["height"], item["text_scale"], item["vertical_position"],
        )
        kwargs: dict[str, Any] = {"font_size_override": size}
        if supports_options:
            kwargs["render_options"] = {"vertical_position": item["vertical_position"], **manifest["presentation"]}
        svg = proof.render_svg(adapted, manifest_dir, manifest["direction"], **kwargs)
        rendered.append({
            "format": item["id"], "width": item["width"], "height": item["height"],
            "font_size": size, "requested_font_size": requested_size,
            "maximum_font_size": maximum_size, "text_scale": min(float(item["text_scale"]), 1.0),
            "auto_fitted": auto_fitted, "fitting": fit_mode, "svg": svg,
        })
    return rendered


def _measured_text_box(lines: list[str], font_size: float, manifest: dict[str, Any], manifest_dir: Path, line_ratio: float) -> tuple[float, float, str]:
    font = manifest["brand"]["font"]
    proof.activate_font_metrics(font, manifest_dir)
    font_value = font.get("medium_path") or font.get("regular_path")
    if font_value:
        try:
            from PIL import ImageFont

            face = ImageFont.truetype(str(proof.resolve_asset(font_value, manifest_dir)), max(1, round(font_size)))
            return max(float(face.getlength(line)) for line in lines), font_size * line_ratio * len(lines), "pillow_real_metrics"
        except (ImportError, OSError, ValueError):
            pass
    metric = "font_metrics_ttf" if proof.font_metrics_active() else "deterministic_heuristic"
    return max(proof.visual_units(line) for line in lines) * font_size, font_size * line_ratio * len(lines), metric


def preview_quality(manifest: dict[str, Any], previews: list[dict[str, Any]], manifest_dir: Path) -> dict[str, Any]:
    """Run renderer-aware checks used by the live quality gate."""
    warnings: list[dict[str, str]] = []
    checks = ["structure", "contrast", "fitting", "safe_area", "svg", "render", "assets"]
    seen: set[tuple[str, str, str]] = set()

    def add(code: str, message: str, format_id: str = "all") -> None:
        key = (code, message, format_id)
        if key not in seen:
            seen.add(key)
            warnings.append({"code": code, "format": format_id, "message": message})

    by_id = {item["id"]: item for item in manifest["formats"]}
    for preview in previews:
        format_id = preview["format"]
        item = by_id[format_id]
        adapted = pack.proof_manifest_for_format(manifest, item)
        adapted["canvas"] = {"width": item["width"], "height": item["height"]}
        adapted["direction"] = manifest["direction"]
        adapted["content"]["emphasis"] = manifest["content"]["emphasis"]
        if manifest["presentation"]["logo_mode"] == "hidden":
            adapted["brand"] = copy.deepcopy(adapted["brand"])
            adapted["brand"].pop("logo", None)
        for issue in proof.validate_visual_manifest(adapted, manifest_dir):
            # The proof validator is intentionally 4:5-only; format ratios are
            # validated separately by the 0.4 contract before this QA pass.
            if issue.get("path") == "canvas" and issue.get("code") == "ratio":
                continue
            add(f"visual_{issue['code']}", f"{format_id}: {issue['message']}", format_id)

        measurement = pack.layout_measurement(
            item["lines"], float(preview["font_size"]), adapted, manifest_dir,
            manifest["direction"], item["width"], item["height"], item["vertical_position"],
        )
        preview["measurement"] = measurement["metric"]
        if not measurement["width_fits"]:
            add("text_fit", f"{format_id}: il testo supera l'area tipografica disponibile; riduci la scala o rivedi gli a capo.", format_id)
        if not measurement["vertical_fits"]:
            add("safe_area", f"{format_id}: il blocco di testo invade l'area riservata a logo o attribuzione.", format_id)

        try:
            width, height = item["width"], item["height"]
            root = ET.fromstring(preview["svg"])
            if root.tag.rsplit("}", 1)[-1] != "svg" or root.get("viewBox") != f"0 0 {width} {height}":
                add("svg_geometry", f"{format_id}: geometria SVG non coerente con il formato.", format_id)
        except ET.ParseError:
            add("svg_invalid", f"{format_id}: l'anteprima SVG non è ben formata.", format_id)

        # Every check above validates a *prediction* about the render. This
        # one reads the render itself, so a defect has to survive both the
        # estimate and the drawing to reach the user -- the gap that let a
        # Poster overflow ship while this gate reported success.
        for finding in inspector.inspect_render(
            preview["svg"], manifest["direction"], item["width"], item["height"],
            vertical_position=item["vertical_position"],
        ):
            add(finding["code"], f"{format_id}: {finding['message']}", format_id)

    return {"passed": not warnings, "checks": checks, "warnings": warnings}


# Ceiling for the contrast score: WCAG AAA (7:1) is already the codebase's
# own strictest bar (render_quote_card_pack's outline check uses it), so
# reaching it earns full marks rather than inventing a new reference point.
CONTRAST_SCORE_CEILING = 7.0


def preview_score(manifest: dict[str, Any], previews: list[dict[str, Any]], qa: dict[str, Any]) -> dict[str, Any]:
    """A read-out for the ledger, not a new gate: every input here already
    feeds an existing pass/fail check. Scoring only turns those checks into
    a number the user can see move, rather than inventing new criteria.
    """
    colors = manifest["brand"]["colors"]
    ratios = [
        proof.contrast_ratio(colors["primary"], colors["background"]),
        proof.contrast_ratio(colors["background"], colors["primary"]),
        proof.contrast_ratio(colors["accent"], colors["primary"]),
    ]
    contrast_score = round(min(100.0, min(ratios) / CONTRAST_SCORE_CEILING * 100))

    # auto_fitted means the format's chosen scale/position asked for more
    # room than the safe area has and was silently capped -- the one signal
    # here that is unambiguously a defect, not a legitimate design choice.
    capped_formats = sum(1 for item in previews if item.get("auto_fitted"))
    fit_score = max(0, 100 - 25 * capped_formats)

    structure_penalty = 20 * len({(item["code"], item["format"]) for item in qa.get("warnings", [])})
    structure_score = max(0, 100 - structure_penalty)

    overall = round((contrast_score + fit_score + structure_score) / 3)
    return {
        "overall": overall,
        "categories": {"contrast": contrast_score, "fit": fit_score, "structure": structure_score},
    }


def ensure_approvable(manifest: dict[str, Any], manifest_dir: Path) -> dict[str, Any]:
    qa = preview_quality(manifest, render_preview(manifest, manifest_dir), manifest_dir)
    if not qa["passed"]:
        messages = "; ".join(warning["message"] for warning in qa["warnings"])
        raise ValueError(f"La prova non supera il quality gate: {messages}")
    return qa


def asset_path(root: Path, url_path: str) -> Path | None:
    relative = url_path.lstrip("/")
    if relative.startswith("assets/"): relative = relative.removeprefix("assets/")
    if not relative or Path(relative).suffix not in MIME_TYPES: return None
    candidate = (root / relative).resolve()
    return candidate if candidate.is_file() and candidate.is_relative_to(root.resolve()) else None


def generated_asset_path(root: Path, url_path: str) -> Path | None:
    relative = Path(unquote(url_path.removeprefix("/api/output/").lstrip("/")))
    if relative.is_absolute() or relative.suffix.lower() not in GENERATED_MIME_TYPES:
        return None
    candidate = (root / relative).resolve()
    return candidate if candidate.is_file() and candidate.is_relative_to(root.resolve()) else None


def production_formats(manifest: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    formats = copy.deepcopy(manifest["formats"])
    available = {item["id"] for item in formats}
    mode = (manifest.get("presentation") or {}).get("output_mode")
    if mode not in OUTPUT_MODES:
        mode = "all" if available == FORMAT_IDS else formats[0]["id"]
    selected = formats if mode == "all" else [item for item in formats if item["id"] == mode]
    if not selected:
        raise ValueError(f"Il formato {mode} non è disponibile nella sessione")
    return mode, selected


def generate_production_pack(
    manifest: dict[str, Any], manifest_path: Path, session_dir: Path,
    node: Path | None, node_modules: Path | None,
) -> dict[str, Any]:
    """Freeze the approved draft and render the selected production outputs."""
    production_dir = session_dir / "production"
    output_dir = production_dir / "output"
    mode, formats = production_formats(manifest)
    previews = {item["format"]: item for item in render_preview(manifest, manifest_path.parent)}
    proof_format = formats[0]["id"]
    proof = previews.get(proof_format)
    if not proof:
        raise ValueError("La prova approvata non è disponibile")

    basename = (manifest.get("output") or {}).get("basename", "quote-card")
    proof_path = production_dir / f"{basename}-{manifest['direction']}-{proof_format}-approved-proof.svg"
    proof_path.parent.mkdir(parents=True, exist_ok=True)
    proof_path.write_text(proof["svg"], encoding="utf-8")

    presentation = copy.deepcopy(manifest.get("presentation") or {})
    presentation["output_mode"] = mode
    production_manifest = {
        "schema_version": "0.3",
        "state": "prova_visuale_approvata",
        "approval": {
            "direction": manifest["direction"],
            "proof_path": proof_path.name,
            "content_sha256": pack.sha256_text(manifest["content"]["text"]),
            "approved_by": "user",
            "approved_at": now_iso(),
        },
        "content": copy.deepcopy(manifest["content"]),
        "formats": formats,
        "presentation": presentation,
        "brand": copy.deepcopy(manifest["brand"]),
        "source": copy.deepcopy(manifest["source"]),
        "output": copy.deepcopy(manifest.get("output") or {"basename": basename}),
    }
    production_manifest_path = production_dir / "production-manifest.json"
    atomic_write_json(production_manifest_path, production_manifest)
    errors = pack.validate_production_manifest(production_manifest, production_dir)
    if errors:
        messages = "; ".join(error["message"] for error in errors)
        raise ValueError(f"Manifest di produzione non valido: {messages}")

    png_required = bool(node and node_modules and node.is_file() and node_modules.is_dir())
    result = pack.render_pack(
        production_manifest, production_manifest_path, output_dir,
        "required" if png_required else "auto", node, node_modules, "auto",
    )
    outputs: list[dict[str, str]] = []
    if len(result["formats"]) > 1:
        # "Tutti" means every produced format bundled as one thing to save,
        # not three separate PNGs the user has to click through and rename
        # by hand -- the single-format case below is unaffected.
        zip_path = (production_dir / f"{basename}-{manifest['direction']}.zip").resolve()
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for item in result["formats"]:
                artifact = item.get("png") or item.get("svg")
                if artifact:
                    archive.write(output_dir / artifact["path"], arcname=artifact["path"])
            contact_sheet = Path(result["contact_sheet"])
            archive.write(contact_sheet, arcname=contact_sheet.name)
        outputs.append({
            "format": "zip",
            "kind": "zip",
            "filename": zip_path.name,
            "relative_path": zip_path.relative_to(production_dir.resolve()).as_posix(),
            "absolute_path": str(zip_path),
        })
    else:
        for item in result["formats"]:
            artifact = item.get("png") or item.get("svg")
            if not artifact:
                continue
            path = (output_dir / artifact["path"]).resolve()
            relative = path.relative_to(production_dir.resolve()).as_posix()
            outputs.append({
                "format": item["format"],
                "kind": "png" if item.get("png") else "svg",
                "filename": path.name,
                "relative_path": relative,
                "absolute_path": str(path),
            })
    return {
        **result,
        "outputs": outputs,
        "production_manifest": str(production_manifest_path),
        "production_root": str(production_dir),
    }


def output_payload(outputs: Any, token: str, production_root: Path | None = None) -> list[dict[str, Any]]:
    """Attach authenticated download URLs to persisted generation outputs."""
    result: list[dict[str, Any]] = []
    if not isinstance(outputs, list):
        return result
    for item in outputs:
        if not isinstance(item, dict) or not isinstance(item.get("relative_path"), str):
            continue
        encoded = quote(item["relative_path"], safe="/")
        enriched = {**item, "url": f"/api/output/{encoded}?token={quote(token, safe='')}"}
        if production_root is not None and not isinstance(enriched.get("absolute_path"), str):
            candidate = (production_root / item["relative_path"]).resolve()
            try:
                candidate.relative_to(production_root.resolve())
            except ValueError:
                pass
            else:
                enriched["absolute_path"] = str(candidate)
        result.append(enriched)
    return result


def create_server(
    manifest_path: Path, session_dir: Path, port: int = 0,
    node: Path | None = None, node_modules: Path | None = None,
    return_thread_id: str | None = None,
) -> tuple[ThreadingHTTPServer, str]:
    manifest_path, session_dir = manifest_path.resolve(), session_dir.resolve()
    manifest = read_json(manifest_path)
    errors = validate_manifest(manifest)
    if errors: raise ValueError("; ".join(errors))
    return_url = return_url_for_thread(return_thread_id)
    session_dir.mkdir(parents=True, exist_ok=True)
    state_path, feedback_path = session_dir / "session-state.json", session_dir / "feedback.json"
    state = read_json(state_path) if state_path.exists() else {}
    if state.get("manifest") not in (None, str(manifest_path)): raise ValueError("La sessione è associata a un manifest diverso")
    token = state.get("token") if isinstance(state.get("token"), str) else secrets.token_urlsafe(24)
    state.update({"manifest": str(manifest_path), "feedback_path": str(feedback_path), "token": token, "manifest_revision": manifest["revision"], "server_started_at": now_iso(), "last_feedback_id": state.get("last_feedback_id"), "applied_feedback_id": state.get("applied_feedback_id")})
    atomic_write_json(state_path, state)
    assets = SCRIPT_DIR.parent / "assets" / "card-editor"
    production_dir = session_dir / "production"
    node = node.resolve() if node else None
    node_modules = node_modules.resolve() if node_modules else None
    lock = threading.Lock()
    chatbot_lock = threading.Lock()

    def update_chatbot_state(status: dict[str, Any]) -> None:
        with chatbot_lock:
            current = read_json(state_path)
            current["chatbot_generation"] = status
            atomic_write_json(state_path, current)

    def launch_chatbot_generation(generation: dict[str, Any]) -> dict[str, Any]:
        """Hand the approved production manifest to a local Codex chatbot."""
        with chatbot_lock:
            existing = read_json(state_path).get("chatbot_generation")
            if isinstance(existing, dict) and existing.get("status") == "running":
                return existing
        cli = chatbot_cli_path()
        production_manifest = Path(generation["production_manifest"]).resolve()
        production_root = Path(generation["production_root"]).resolve()
        output_dir = production_root / "output"
        request_id = f"chatbot-{secrets.token_hex(8)}"
        request_path = session_dir / f"{request_id}.json"
        log_path = session_dir / f"{request_id}.log"
        if cli is None:
            return {
                "request_id": request_id,
                "status": "unavailable",
                "message": "Codex CLI non disponibile: gli output locali restano validi.",
            }
        request = {
            "request_id": request_id,
            "created_at": now_iso(),
            "manifest": str(production_manifest),
            "output_dir": str(output_dir),
            "outputs": generation.get("outputs", []),
            "status": "queued",
        }
        atomic_write_json(request_path, request)
        command = [
            str(cli), "exec", "--ephemeral", "--skip-git-repo-check",
            "--sandbox", "workspace-write", "--color", "never",
            "-C", str(SCRIPT_DIR.parent),
            chatbot_prompt(production_manifest, output_dir, node, node_modules),
        ]
        try:
            log_handle = log_path.open("w", encoding="utf-8")
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        except OSError as exc:
            return {
                "request_id": request_id,
                "status": "failed",
                "message": f"Avvio chatbot non riuscito: {exc}",
            }
        status = {
            "request_id": request_id,
            "status": "running",
            "started_at": now_iso(),
            "pid": process.pid,
            "request_path": str(request_path),
            "log_path": str(log_path),
        }
        update_chatbot_state(status)

        def monitor() -> None:
            try:
                return_code = process.wait(timeout=CHATBOT_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                return_code = -15
            finally:
                log_handle.close()
            # A "Tutti" generation delivers one zip, not a PNG per format --
            # the chatbot re-renders the individual PNGs it was pointed at
            # regardless, so existence is what settles readiness here.
            files_ready = all(
                (production_root / item["relative_path"]).is_file()
                for item in generation.get("outputs", [])
            )
            completed = return_code == 0 and files_ready
            update_chatbot_state({
                **status,
                "status": "completed" if completed else "failed",
                "finished_at": now_iso(),
                "return_code": return_code,
                "outputs_ready": files_ready,
                "message": "PNG creati dal chatbot." if completed else "Il chatbot non ha completato tutti i PNG; verifica il log.",
            })

        threading.Thread(target=monitor, name=f"quote-card-chatbot-{request_id}", daemon=True).start()
        return status

    class Handler(BaseHTTPRequestHandler):
        server_version = "QuoteVisualReview/0.4"
        def log_message(self, *_args: object) -> None: return
        def local_host(self) -> bool:
            host = self.headers.get("Host", "").rsplit(":", 1)[0].strip("[]")
            return host in {"127.0.0.1", "localhost", "::1"}
        def authorized(self, query: dict[str, list[str]]) -> bool:
            return secrets.compare_digest(query.get("token", [""])[0], token)
        def send_value(self, status: int, body: bytes, content_type: str) -> None:
            # Preview SVGs are generated locally from a validated manifest and
            # carry embedded @font-face rules. Inline scripts remain forbidden.
            self.send_response(status); self.send_header("Content-Type", content_type); self.send_header("Content-Length", str(len(body))); self.send_header("Cache-Control", "no-store"); self.send_header("X-Content-Type-Options", "nosniff"); self.send_header("X-Frame-Options", "DENY"); self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; font-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"); self.end_headers(); self.wfile.write(body)
        def send_json(self, status: int, value: dict[str, Any]) -> None: self.send_value(status, json.dumps(value, ensure_ascii=False).encode(), "application/json; charset=utf-8")
        def request_json(self) -> Any:
            if self.headers.get("Content-Type", "").split(";", 1)[0] != "application/json": raise ValueError("Content-Type deve essere application/json")
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= MAX_BODY_BYTES: raise ValueError("Corpo JSON non valido o troppo grande")
            return json.loads(self.rfile.read(length).decode("utf-8"))
        def do_GET(self) -> None:  # noqa: N802
            parsed, query = urlparse(self.path), parse_qs(urlparse(self.path).query)
            if not self.local_host(): self.send_json(HTTPStatus.FORBIDDEN, {"error": "Host non consentito"}); return
            static = asset_path(assets, parsed.path)
            if static: self.send_value(HTTPStatus.OK, static.read_bytes(), MIME_TYPES[static.suffix]); return
            if not self.authorized(query): self.send_json(HTTPStatus.FORBIDDEN, {"error": "Sessione non autorizzata"}); return
            if parsed.path.startswith("/api/output/"):
                generated = generated_asset_path(production_dir, parsed.path)
                if generated:
                    self.send_value(HTTPStatus.OK, generated.read_bytes(), GENERATED_MIME_TYPES[generated.suffix.lower()]); return
                self.send_json(HTTPStatus.NOT_FOUND, {"error": "Output non trovato"}); return
            if parsed.path == "/":
                index = assets / "index.html"
                if index.is_file(): self.send_value(HTTPStatus.OK, index.read_bytes(), MIME_TYPES[".html"]); return
                self.send_json(HTTPStatus.NOT_FOUND, {"error": "Interfaccia card-editor mancante"}); return
            if parsed.path == "/api/session": self.send_json(HTTPStatus.OK, session_model(read_json(manifest_path), manifest_path.parent, return_url)); return
            if parsed.path == "/api/status":
                current = read_json(state_path); latest = read_json(manifest_path)
                last_generation = copy.deepcopy(current.get("last_generation"))
                if isinstance(last_generation, dict):
                    last_generation["outputs"] = output_payload(last_generation.get("outputs"), token, production_dir)
                self.send_json(HTTPStatus.OK, {"revision": latest["revision"], "last_feedback_id": current.get("last_feedback_id"), "applied_feedback_id": current.get("applied_feedback_id"), "feedback_pending": bool(current.get("last_feedback_id") and current.get("last_feedback_id") != current.get("applied_feedback_id")), "chatbot_generation": current.get("chatbot_generation"), "last_generation": last_generation}); return
            if parsed.path == "/api/agent-status":
                current = read_json(state_path).get("chatbot_generation")
                if not isinstance(current, dict) or current.get("request_id") != query.get("request_id", [""])[0]:
                    self.send_json(HTTPStatus.NOT_FOUND, {"error": "Richiesta chatbot non trovata"}); return
                self.send_json(HTTPStatus.OK, current); return
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "Risorsa non trovata"})
        def do_POST(self) -> None:  # noqa: N802
            parsed, query = urlparse(self.path), parse_qs(urlparse(self.path).query)
            if not self.local_host() or not self.authorized(query): self.send_json(HTTPStatus.FORBIDDEN, {"error": "Sessione non autorizzata"}); return
            if parsed.path not in {"/api/preview", "/api/generate"}: self.send_json(HTTPStatus.NOT_FOUND, {"error": "Risorsa non trovata"}); return
            try:
                payload, current = self.request_json(), read_json(manifest_path)
                if parsed.path == "/api/preview":
                    draft = validate_draft(payload, current)
                    previews = render_preview(draft, manifest_path.parent)
                    qa = preview_quality(draft, previews, manifest_path.parent)
                    alt_suggestion = proof.default_alt_text(draft["content"]["text"], draft["content"]["attribution"].get("label", ""), draft.get("source"))
                    self.send_json(HTTPStatus.OK, {"revision": current["revision"], "previews": previews, "qa": qa, "warnings": qa["warnings"], "score": preview_score(draft, previews, qa), "editorial_responsibility": "user", "declaration": {"transformation": draft["content"]["transformation"], "evidence_status": draft["content"]["evidence_status"], "attribution": draft["content"]["attribution"], "alt_text_suggestion": alt_suggestion}}); return
                with lock:
                    draft = validate_draft(payload, current)
                    ensure_approvable(draft, manifest_path.parent)
                    feedback = approval_feedback(draft, current["revision"], payload.get("overall_note", ""))
                    application = record_and_apply_feedback(manifest_path, session_dir, feedback)
                    latest = read_json(manifest_path)
                    generation = generate_production_pack(latest, manifest_path, session_dir, node, node_modules)
                    current_state = read_json(state_path)
                    current_state["last_generation"] = {
                        "generated_at": now_iso(),
                        "revision": application["revision"],
                        "qa_report": generation["qa_report"],
                        "outputs": generation["outputs"],
                    }
                    atomic_write_json(state_path, current_state)
                    chatbot = launch_chatbot_generation(generation)
                generated_outputs = output_payload(generation["outputs"], token, production_dir)
                event = {"event": "generation", "feedback_id": feedback["feedback_id"], "action": "generate", "path": str(feedback_path), "applied": True, "revision": application["revision"], "outputs": generated_outputs}
                print(json.dumps(event, ensure_ascii=False), flush=True)
                self.send_json(HTTPStatus.OK, {"applied": True, "application": application, "generation": {**generation, "outputs": generated_outputs}, "chatbot": chatbot})
            except RuntimeError as exc: self.send_json(HTTPStatus.CONFLICT, {"error": str(exc)})
            except (ValueError, UnicodeDecodeError, json.JSONDecodeError, TypeError, review_applier.ReviewError) as exc: self.send_json(HTTPStatus.UNPROCESSABLE_ENTITY, {"error": str(exc)})
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    return server, token


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--session-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--node", type=Path)
    parser.add_argument("--node-modules", type=Path)
    parser.add_argument("--return-thread-id", help="Task Codex a cui tornare dopo la generazione")
    args = parser.parse_args(argv)
    try: server, token = create_server(args.manifest, args.session_dir, args.port, args.node, args.node_modules, args.return_thread_id)
    except (OSError, ValueError, json.JSONDecodeError) as exc: print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr); return 2
    url = f"http://127.0.0.1:{server.server_address[1]}/?token={token}"
    print(json.dumps({"status": "ready", "url": url, "session_dir": str(args.session_dir.resolve()), "manifest": str(args.manifest.resolve())}, ensure_ascii=False), flush=True)
    try: server.serve_forever(poll_interval=.25)
    except KeyboardInterrupt: pass
    finally: server.server_close()
    return 0


if __name__ == "__main__": raise SystemExit(main())
