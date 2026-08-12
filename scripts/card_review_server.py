#!/usr/bin/env python3
"""Local-only visual review server for Quote Card manifest 0.4."""

from __future__ import annotations

import argparse
import copy
import inspect
import json
import math
import os
import secrets
import sys
import threading
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
import render_quote_card as proof
import render_quote_card_pack as pack
import apply_card_review as review_applier

MAX_BODY_BYTES = 250_000
MAX_TEXT_LENGTH = 600
MAX_LINES = 6
MAX_FORMATS = 3
FORMAT_IDS = {"4x5", "1x1", "9x16"}
DIRECTIONS = {"editorial", "statement", "contextual"}
POSITIONS = {"upper", "center", "lower"}
LOGO_MODES = {"auto", "hidden"}
GRAPHIC_MODES = {"auto", "hidden"}
OUTPUT_MODES = {"all", "4x5", "1x1", "9x16"}
SESSION_STATES = {"candidato_selezionato", "contenuto_approvato"}
MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".ttf": "font/ttf",
    ".svg": "image/svg+xml",
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
    if "styles" in content:
        style_errors: list[dict[str, str]] = []
        proof.validate_text_styles(content["styles"], content.get("text", ""), style_errors)
        errors.extend(item["message"] for item in style_errors)
    if not isinstance(content.get("use_quotation_marks"), bool): error(errors, "content.use_quotation_marks deve essere booleano")
    attribution = content.get("attribution")
    if not isinstance(attribution, dict) or attribution.get("role") not in proof.ATTRIBUTION_ROLES: error(errors, "content.attribution deve essere valido")
    elif attribution.get("role") != "none" and (not isinstance(attribution.get("label"), str) or not attribution["label"].strip()): error(errors, "content.attribution.label è obbligatorio per il ruolo scelto")
    if data.get("direction") not in DIRECTIONS: error(errors, "direction non valida")
    presentation = data.get("presentation")
    if (
        not isinstance(presentation, dict)
        or presentation.get("logo_mode") not in LOGO_MODES
        or presentation.get("graphic_mode", "auto") not in GRAPHIC_MODES
        or presentation.get("output_mode", "all") not in OUTPUT_MODES
        or not isinstance(presentation.get("show_quotation_marks"), bool)
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

    regular = available("regular_path")
    bold = available("bold_path")
    italic = available("italic_path")
    return {
        "family": font.get("family", "Font del brand"),
        "embedded": regular,
        "styles": {
            "bold": {"available": regular or bold, "exact": bold},
            "italic": {"available": italic, "exact": italic},
            "underline": {"available": True, "exact": True},
            "highlight": {"available": True, "exact": True},
        },
    }


def session_model(manifest: dict[str, Any], manifest_dir: Path | None = None) -> dict[str, Any]:
    """Return the selected candidate plus the values reviewable in the editor."""
    model = {key: copy.deepcopy(manifest[key]) for key in ("schema_version", "state", "revision", "content", "direction", "presentation", "formats", "brand", "source", "output")}
    model["font_capabilities"] = font_capabilities(manifest, manifest_dir or Path.cwd())
    return model


def validate_draft(payload: Any, manifest: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict): raise ValueError("Il draft deve essere un oggetto JSON")
    allowed = {"base_revision", "text", "transformation", "evidence_status", "attribution", "use_quotation_marks", "direction", "emphasis", "styles", "presentation", "formats", "action", "overall_note"}
    if set(payload) - allowed: raise ValueError("Il draft contiene campi non modificabili")
    if payload.get("base_revision") != manifest["revision"]: raise RuntimeError("La revisione di base non coincide con il manifest")
    candidate = copy.deepcopy(manifest)
    requested_text = normalized_text(payload.get("text", candidate["content"].get("text")))
    if not requested_text or len(requested_text) > MAX_TEXT_LENGTH:
        raise ValueError(f"text deve contenere da 1 a {MAX_TEXT_LENGTH} caratteri")
    candidate["content"].update({
        "text": requested_text,
        "transformation": payload.get("transformation", candidate["content"].get("transformation")),
        "evidence_status": payload.get("evidence_status", candidate["content"].get("evidence_status")),
        "attribution": copy.deepcopy(payload.get("attribution", candidate["content"].get("attribution"))),
        "use_quotation_marks": payload.get("use_quotation_marks", candidate["content"].get("use_quotation_marks")),
        "declared_by": "user",
    })
    for key in ("direction", "emphasis", "styles", "presentation", "formats"):
        if key in payload:
            if key == "emphasis": candidate["content"]["emphasis"] = payload[key]
            elif key == "styles": candidate["content"]["styles"] = copy.deepcopy(payload[key])
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
        adapted["content"]["use_quotation_marks"] = manifest["presentation"]["show_quotation_marks"]
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
    font_value = font.get("medium_path") or font.get("regular_path")
    if font_value:
        try:
            from PIL import ImageFont

            face = ImageFont.truetype(str(proof.resolve_asset(font_value, manifest_dir)), max(1, round(font_size)))
            return max(float(face.getlength(line)) for line in lines), font_size * line_ratio * len(lines), "pillow_real_metrics"
        except (ImportError, OSError, ValueError):
            pass
    return max(proof.visual_units(line) for line in lines) * font_size, font_size * line_ratio * len(lines), "deterministic_heuristic"


def preview_quality(manifest: dict[str, Any], previews: list[dict[str, Any]], manifest_dir: Path) -> dict[str, Any]:
    """Run renderer-aware checks used by the live quality gate."""
    warnings: list[dict[str, str]] = []
    checks = ["structure", "contrast", "fitting", "safe_area", "svg", "assets"]
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
        adapted["content"]["use_quotation_marks"] = manifest["presentation"]["show_quotation_marks"]
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

    return {"passed": not warnings, "checks": checks, "warnings": warnings}


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


def create_server(manifest_path: Path, session_dir: Path, port: int = 0) -> tuple[ThreadingHTTPServer, str]:
    manifest_path, session_dir = manifest_path.resolve(), session_dir.resolve()
    manifest = read_json(manifest_path)
    errors = validate_manifest(manifest)
    if errors: raise ValueError("; ".join(errors))
    session_dir.mkdir(parents=True, exist_ok=True)
    state_path, feedback_path = session_dir / "session-state.json", session_dir / "feedback.json"
    state = read_json(state_path) if state_path.exists() else {}
    if state.get("manifest") not in (None, str(manifest_path)): raise ValueError("La sessione è associata a un manifest diverso")
    token = state.get("token") if isinstance(state.get("token"), str) else secrets.token_urlsafe(24)
    state.update({"manifest": str(manifest_path), "feedback_path": str(feedback_path), "token": token, "manifest_revision": manifest["revision"], "server_started_at": now_iso(), "last_feedback_id": state.get("last_feedback_id"), "applied_feedback_id": state.get("applied_feedback_id")})
    atomic_write_json(state_path, state)
    assets = SCRIPT_DIR.parent / "assets" / "card-editor"
    lock = threading.Lock()

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
            if parsed.path == "/":
                index = assets / "index.html"
                if index.is_file(): self.send_value(HTTPStatus.OK, index.read_bytes(), MIME_TYPES[".html"]); return
                self.send_json(HTTPStatus.NOT_FOUND, {"error": "Interfaccia card-editor mancante"}); return
            if parsed.path == "/api/session": self.send_json(HTTPStatus.OK, session_model(read_json(manifest_path), manifest_path.parent)); return
            if parsed.path == "/api/status":
                current = read_json(state_path); latest = read_json(manifest_path); self.send_json(HTTPStatus.OK, {"revision": latest["revision"], "last_feedback_id": current.get("last_feedback_id"), "applied_feedback_id": current.get("applied_feedback_id"), "feedback_pending": bool(current.get("last_feedback_id") and current.get("last_feedback_id") != current.get("applied_feedback_id"))}); return
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "Risorsa non trovata"})
        def do_POST(self) -> None:  # noqa: N802
            parsed, query = urlparse(self.path), parse_qs(urlparse(self.path).query)
            if not self.local_host() or not self.authorized(query): self.send_json(HTTPStatus.FORBIDDEN, {"error": "Sessione non autorizzata"}); return
            if parsed.path not in {"/api/preview", "/api/submit"}: self.send_json(HTTPStatus.NOT_FOUND, {"error": "Risorsa non trovata"}); return
            try:
                payload, current = self.request_json(), read_json(manifest_path)
                if parsed.path == "/api/preview":
                    draft = validate_draft(payload, current)
                    previews = render_preview(draft, manifest_path.parent)
                    qa = preview_quality(draft, previews, manifest_path.parent)
                    self.send_json(HTTPStatus.OK, {"revision": current["revision"], "previews": previews, "qa": qa, "warnings": qa["warnings"], "editorial_responsibility": "user", "declaration": {"transformation": draft["content"]["transformation"], "evidence_status": draft["content"]["evidence_status"], "attribution": draft["content"]["attribution"], "use_quotation_marks": draft["content"]["use_quotation_marks"]}}); return
                with lock:
                    draft = validate_draft(payload, current)
                    action = payload.get("action")
                    if action not in {"feedback", "approve"}: raise ValueError("action deve essere feedback oppure approve")
                    if action == "approve": ensure_approvable(draft, manifest_path.parent)
                    feedback = {"feedback_id": f"feedback-{secrets.token_hex(8)}", "submitted_at": now_iso(), "action": action, "base_revision": current["revision"], "editorial_responsibility": "user", "content": {"text": draft["content"]["text"], "transformation": draft["content"]["transformation"], "evidence_status": draft["content"]["evidence_status"], "attribution": draft["content"]["attribution"], "use_quotation_marks": draft["content"]["use_quotation_marks"], "styles": draft["content"].get("styles", []), "declared_by": "user"}, "direction": draft["direction"], "emphasis": draft["content"]["emphasis"], "presentation": draft["presentation"], "formats": [{"id": item["id"], "lines": item["lines"], "text_scale": item["text_scale"], "vertical_position": item["vertical_position"]} for item in draft["formats"]], "overall_note": payload.get("overall_note", "")}
                    application = record_and_apply_feedback(manifest_path, session_dir, feedback)
                event = {"event": "feedback", "feedback_id": feedback["feedback_id"], "action": action, "path": str(feedback_path), "applied": True, "revision": application["revision"]}
                print(json.dumps(event, ensure_ascii=False), flush=True)
                self.send_json(HTTPStatus.OK, {**feedback, "applied": True, "application": application})
            except RuntimeError as exc: self.send_json(HTTPStatus.CONFLICT, {"error": str(exc)})
            except (ValueError, UnicodeDecodeError, json.JSONDecodeError, TypeError, review_applier.ReviewError) as exc: self.send_json(HTTPStatus.UNPROCESSABLE_ENTITY, {"error": str(exc)})
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    return server, token


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("manifest", type=Path); parser.add_argument("--session-dir", type=Path, required=True); parser.add_argument("--port", type=int, default=0); args = parser.parse_args(argv)
    try: server, token = create_server(args.manifest, args.session_dir, args.port)
    except (OSError, ValueError, json.JSONDecodeError) as exc: print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr); return 2
    url = f"http://127.0.0.1:{server.server_address[1]}/?token={token}"
    print(json.dumps({"status": "ready", "url": url, "session_dir": str(args.session_dir.resolve()), "manifest": str(args.manifest.resolve())}, ensure_ascii=False), flush=True)
    try: server.serve_forever(poll_interval=.25)
    except KeyboardInterrupt: pass
    finally: server.server_close()
    return 0


if __name__ == "__main__": raise SystemExit(main())
