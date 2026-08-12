#!/usr/bin/env python3
"""Atomically apply the permitted visual-review changes to a 0.4 manifest."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
import unicodedata
from pathlib import Path
from typing import Any


DIRECTIONS = {"editorial", "statement", "contextual"}
LOGO_MODES = {"auto", "hidden"}
GRAPHIC_MODES = {"auto", "hidden"}
OUTPUT_MODES = {"all", "4x5", "1x1", "9x16"}
VERTICAL_POSITIONS = {"upper", "center", "lower"}
TRANSFORMATIONS = {"VERBATIM", "EDITED", "PARAPHRASE", "AI_GENERATED"}
EVIDENCE_STATUSES = {"VERIFIED", "USER_SUPPLIED", "UNVERIFIED", "CONFLICT"}
ATTRIBUTION_ROLES = {"speaker", "author", "publisher", "none"}
STYLE_TYPES = {"bold", "italic", "underline", "highlight"}
CONTENT_KEYS = {"text", "transformation", "evidence_status", "attribution", "use_quotation_marks", "styles", "declared_by"}


class ReviewError(ValueError):
    """A review cannot be safely applied."""


def _normalise(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", value).split())


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReviewError(f"{label} non leggibile: {exc}") from exc
    if not isinstance(value, dict):
        raise ReviewError(f"{label} deve essere un oggetto JSON.")
    return value


def _atomic_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


class SessionLock:
    """An O_EXCL lock which safely clears a lock left by a dead process."""

    def __init__(self, session_dir: Path) -> None:
        self.path = session_dir / ".apply-card-review.lock"
        self.acquired = False

    @staticmethod
    def _owner_is_alive(lock_path: Path) -> bool:
        try:
            payload = json.loads(lock_path.read_text(encoding="utf-8"))
            pid = payload.get("pid")
            if not isinstance(pid, int) or pid <= 0:
                return False
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except (OSError, ValueError, json.JSONDecodeError):
            return False

    def __enter__(self) -> "SessionLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        for attempt in range(2):
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError:
                if attempt == 0 and not self._owner_is_alive(self.path):
                    try:
                        self.path.unlink()
                    except FileNotFoundError:
                        pass
                    continue
                raise ReviewError("Sessione occupata da un altro applicatore di review.")
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump({"pid": os.getpid(), "created_at": time.time()}, stream)
                stream.flush()
                os.fsync(stream.fileno())
            self.acquired = True
            return self
        raise ReviewError("Impossibile acquisire il lock della sessione.")

    def __exit__(self, *_: Any) -> None:
        if self.acquired:
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass


def _require_exact_path(state: dict[str, Any], key: str, actual: Path) -> None:
    stored = state.get(key)
    if not isinstance(stored, str) or Path(stored).resolve() != actual.resolve():
        raise ReviewError(f"session-state.{key} non corrisponde al percorso fornito.")


def _validate_state(state: dict[str, Any], manifest: Path, feedback: Path, data: dict[str, Any]) -> None:
    _require_exact_path(state, "manifest", manifest)
    _require_exact_path(state, "feedback_path", feedback)
    feedback_id = data.get("feedback_id")
    if not isinstance(feedback_id, str) or not feedback_id:
        raise ReviewError("feedback.feedback_id mancante.")
    if state.get("last_feedback_id") != feedback_id:
        raise ReviewError("feedback_id non coincide con session-state.last_feedback_id.")
    if state.get("applied_feedback_id") == feedback_id:
        raise ReviewError("Questo feedback è già stato applicato.")


def _validate_lines(lines: Any, text: str, path: str) -> list[str]:
    if not isinstance(lines, list) or not 1 <= len(lines) <= 6 or any(
        not isinstance(line, str) for line in lines
    ):
        raise ReviewError(f"{path}.lines deve contenere da 1 a 6 stringhe.")
    if not any(line.strip() for line in lines):
        raise ReviewError(f"{path}.lines deve contenere almeno una riga di testo.")
    if _normalise(" ".join(lines)) != _normalise(text):
        raise ReviewError(f"{path}.lines non ricostruisce esattamente content.text.")
    return lines


def _validate_patch(feedback: dict[str, Any], manifest: dict[str, Any]) -> None:
    allowed = {"feedback_id", "submitted_at", "base_revision", "action", "editorial_responsibility", "content", "direction", "emphasis", "presentation", "formats", "overall_note"}
    extra = set(feedback) - allowed
    if extra:
        raise ReviewError("Feedback contiene campi non applicabili: " + ", ".join(sorted(extra)))
    if feedback.get("action") not in {"feedback", "approve"}:
        raise ReviewError("feedback.action deve essere feedback o approve.")
    revision = manifest.get("revision")
    if not isinstance(revision, int) or isinstance(revision, bool):
        raise ReviewError("manifest.revision deve essere un intero.")
    if feedback.get("base_revision") != revision:
        raise ReviewError("feedback.base_revision non coincide con manifest.revision.")
    if manifest.get("schema_version") != "0.4":
        raise ReviewError("È supportato soltanto manifest schema_version 0.4.")

    content = manifest.get("content")
    if not isinstance(content, dict) or not isinstance(content.get("text"), str):
        raise ReviewError("manifest.content non valido.")
    content_patch = feedback.get("content", {})
    if not isinstance(content_patch, dict) or set(content_patch) - CONTENT_KEYS:
        raise ReviewError("feedback.content contiene campi non applicabili.")
    target_content = dict(content)
    target_content.update(content_patch)
    target_text = target_content.get("text")
    if not isinstance(target_text, str) or not target_text.strip() or len(target_text) > 600:
        raise ReviewError("content.text deve contenere da 1 a 600 caratteri.")
    text_changed = _normalise(target_text) != _normalise(content.get("text", ""))
    if target_content.get("transformation") not in TRANSFORMATIONS:
        raise ReviewError("content.transformation non ammessa.")
    if target_content.get("evidence_status") not in EVIDENCE_STATUSES:
        raise ReviewError("content.evidence_status non ammesso.")
    if not isinstance(target_content.get("use_quotation_marks"), bool):
        raise ReviewError("content.use_quotation_marks deve essere booleano.")
    attribution = target_content.get("attribution")
    if not isinstance(attribution, dict) or set(attribution) - {"label", "role", "authorship_approved"}:
        raise ReviewError("content.attribution non valida.")
    if attribution.get("role") not in ATTRIBUTION_ROLES:
        raise ReviewError("content.attribution.role non ammesso.")
    if attribution.get("role") != "none" and (not isinstance(attribution.get("label"), str) or not attribution["label"].strip()):
        raise ReviewError("content.attribution.label è obbligatorio per il ruolo scelto.")
    if target_content.get("declared_by", "user") != "user":
        raise ReviewError("content.declared_by deve essere user.")
    styles = target_content.get("styles")
    if styles is not None:
        if not isinstance(styles, list) or len(styles) > 64:
            raise ReviewError("content.styles deve essere una lista con al massimo 64 intervalli.")
        for index, style in enumerate(styles):
            if not isinstance(style, dict) or set(style) != {"start", "end", "type"}:
                raise ReviewError(f"content.styles[{index}] richiede start, end e type.")
            start, end, kind = style.get("start"), style.get("end"), style.get("type")
            if (
                not isinstance(start, int) or isinstance(start, bool)
                or not isinstance(end, int) or isinstance(end, bool)
                or not 0 <= start < end <= len(target_text)
            ):
                raise ReviewError(f"content.styles[{index}] non ricade nel testo corrente.")
            if kind not in STYLE_TYPES:
                raise ReviewError(f"content.styles[{index}].type non ammesso.")

    if "direction" in feedback and feedback["direction"] not in DIRECTIONS:
        raise ReviewError("direction non ammessa.")
    if "emphasis" in feedback:
        emphasis = feedback["emphasis"]
        if not isinstance(emphasis, str) or (emphasis and emphasis not in target_text):
            raise ReviewError("content.emphasis deve essere vuota o una sottostringa esatta del testo.")
    if "overall_note" in feedback and not isinstance(feedback["overall_note"], str):
        raise ReviewError("overall_note deve essere una stringa.")

    presentation = feedback.get("presentation", {})
    if not isinstance(presentation, dict) or set(presentation) - {"logo_mode", "show_quotation_marks", "graphic_mode", "output_mode"}:
        raise ReviewError("Sono consentite solo modifiche di presentazione previste.")
    if "logo_mode" in presentation and presentation["logo_mode"] not in LOGO_MODES:
        raise ReviewError("presentation.logo_mode non ammesso.")
    if "show_quotation_marks" in presentation:
        show = presentation["show_quotation_marks"]
        if not isinstance(show, bool):
            raise ReviewError("presentation.show_quotation_marks deve essere booleano.")
    if "graphic_mode" in presentation and presentation["graphic_mode"] not in GRAPHIC_MODES:
        raise ReviewError("presentation.graphic_mode non ammesso.")
    if "output_mode" in presentation and presentation["output_mode"] not in OUTPUT_MODES:
        raise ReviewError("presentation.output_mode non ammesso.")

    formats = feedback.get("formats", [])
    if not isinstance(formats, list):
        raise ReviewError("feedback.formats deve essere una lista.")
    existing = manifest.get("formats")
    if not isinstance(existing, list):
        raise ReviewError("manifest.formats deve essere una lista.")
    existing_ids: set[str] = set()
    for index, item in enumerate(existing):
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or item["id"] in existing_ids:
            raise ReviewError("manifest.formats deve contenere identificatori univoci.")
        existing_ids.add(item["id"])
    seen: set[Any] = set()
    # A review may touch one format only, but it must never carry forward an
    # already invalid line split in one of the other production formats.
    if not text_changed:
        for item in existing:
            _validate_lines(item.get("lines"), target_text, f"manifest.formats[{item['id']}]")
    elif {item.get("id") for item in formats if isinstance(item, dict)} != existing_ids:
        raise ReviewError("Una modifica al testo deve aggiornare gli a capo di tutti i formati.")
    for item in formats:
        if not isinstance(item, dict) or set(item) - {"id", "lines", "text_scale", "vertical_position"}:
            raise ReviewError("Ogni feedback.formats può contenere solo id, lines, text_scale e vertical_position.")
        ident = item.get("id")
        if not isinstance(ident, str) or ident not in existing_ids or ident in seen:
            raise ReviewError("Il feedback fa riferimento a un formato inesistente o duplicato.")
        seen.add(ident)
        if not (set(item) - {"id"}):
            raise ReviewError("Ogni formato deve includere almeno una modifica.")
        if "lines" in item:
            _validate_lines(item["lines"], target_text, f"formats[{ident}]")
        elif text_changed:
            raise ReviewError("Una modifica al testo richiede lines per ogni formato.")
        if "text_scale" in item:
            scale = item["text_scale"]
            if not isinstance(scale, (int, float)) or isinstance(scale, bool) or not 0.80 <= scale <= 1.08:
                raise ReviewError("text_scale deve essere fra 0.80 e 1.00; i valori legacy fino a 1.08 vengono limitati al massimo sicuro.")
        if "vertical_position" in item and item["vertical_position"] not in VERTICAL_POSITIONS:
            raise ReviewError("vertical_position non ammessa.")


def _apply_patch(manifest: dict[str, Any], feedback: dict[str, Any]) -> bool:
    changed = False
    content_patch = feedback.get("content", {})
    if content_patch:
        target = manifest.setdefault("content", {})
        for key in CONTENT_KEYS:
            if key in content_patch and target.get(key) != content_patch[key]:
                target[key] = content_patch[key]
                changed = True
    for key in ("direction",):
        if key in feedback and manifest.get(key) != feedback[key]:
            manifest[key] = feedback[key]
            changed = True
    emphasis_patch = {"emphasis": feedback["emphasis"]} if "emphasis" in feedback else {}
    for section, patch, keys in (
        ("content", emphasis_patch, ("emphasis",)),
        ("presentation", feedback.get("presentation", {}), ("logo_mode", "show_quotation_marks", "graphic_mode", "output_mode")),
    ):
        if patch:
            target = manifest.setdefault(section, {})
            for key in keys:
                if key in patch and target.get(key) != patch[key]:
                    target[key] = patch[key]
                    changed = True
    by_id = {item["id"]: item for item in manifest["formats"]}
    for patch in feedback.get("formats", []):
        target = by_id[patch["id"]]
        for key in ("lines", "text_scale", "vertical_position"):
            if key in patch and target.get(key) != patch[key]:
                target[key] = patch[key]
                changed = True
    if manifest.get("state") == "candidato_selezionato":
        manifest["state"] = "contenuto_approvato"
        changed = True
    return changed


def apply_review(manifest_path: Path, feedback_path: Path, session_dir: Path) -> dict[str, Any]:
    manifest_path, feedback_path, session_dir = manifest_path.resolve(), feedback_path.resolve(), session_dir.resolve()
    state_path = session_dir / "session-state.json"
    with SessionLock(session_dir):
        manifest = _load_json(manifest_path, "Manifest")
        feedback = _load_json(feedback_path, "Feedback")
        state = _load_json(state_path, "session-state")
        _validate_state(state, manifest_path, feedback_path, feedback)
        _validate_patch(feedback, manifest)
        before = json.loads(json.dumps(manifest))
        changed = _apply_patch(manifest, feedback)
        revision = manifest["revision"]
        if changed:
            backup = session_dir / f"{manifest_path.stem}-r{revision}.backup.json"
            _atomic_write(backup, before)
            manifest["revision"] = revision + 1
            _atomic_write(manifest_path, manifest)
            revision = manifest["revision"]
        state["applied_feedback_id"] = feedback["feedback_id"]
        state["manifest_revision"] = revision
        _atomic_write(state_path, state)
        warnings = [] if changed else ["Nessuna modifica visuale da applicare."]
        return {
            "changed": changed,
            "revision": revision,
            "approval_requested": feedback["action"] == "approve",
            "content_confirmed": manifest.get("state") == "contenuto_approvato",
            "editorial_responsibility": "user",
            "overall_note": feedback.get("overall_note", ""),
            "warnings": warnings,
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("feedback", type=Path)
    parser.add_argument("--session-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = apply_review(args.manifest, args.feedback, args.session_dir)
    except ReviewError as exc:
        result = {"changed": False, "approval_requested": False, "warnings": [str(exc)]}
        print(json.dumps(result, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
