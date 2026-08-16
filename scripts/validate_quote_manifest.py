#!/usr/bin/env python3
"""Validate a Quote Card Builder 0.1 manifest using only the standard library."""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from pathlib import Path
from typing import Any


TRANSFORMATIONS = {"VERBATIM", "EDITED", "PARAPHRASE", "AI_GENERATED"}
EVIDENCE_STATUSES = {"VERIFIED", "USER_SUPPLIED", "UNVERIFIED", "CONFLICT"}
ATTRIBUTION_ROLES = {"speaker", "author", "publisher", "none"}
SOURCE_KINDS = {"phrase", "text", "url", "document", "idea"}
STATES = {
    "bozza",
    "candidati_pronti",
    "contenuto_approvato",
}


def normalize_verbatim(value: str) -> str:
    """Allow Unicode and whitespace normalization, but no punctuation or case edits."""
    return " ".join(unicodedata.normalize("NFC", value).split())


def add_error(errors: list[dict[str, str]], path: str, code: str, message: str) -> None:
    errors.append({"path": path, "code": code, "message": message})


def require_dict(value: Any, path: str, errors: list[dict[str, str]]) -> dict[str, Any]:
    if not isinstance(value, dict):
        add_error(errors, path, "type", "Deve essere un oggetto.")
        return {}
    return value


def require_nonempty_string(
    obj: dict[str, Any], key: str, path: str, errors: list[dict[str, str]]
) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        add_error(errors, f"{path}.{key}", "required", "Deve essere una stringa non vuota.")
        return ""
    return value


def validate_manifest(data: Any) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    root = require_dict(data, "$", errors)
    if not root:
        return errors

    if root.get("schema_version") != "0.1":
        add_error(errors, "schema_version", "unsupported", "La versione supportata è 0.1.")

    state = root.get("state")
    if state not in STATES:
        add_error(errors, "state", "enum", "Stato non ammesso.")

    source = require_dict(root.get("source"), "source", errors)
    require_nonempty_string(source, "id", "source", errors)
    source_kind = source.get("kind")
    if source_kind not in SOURCE_KINDS:
        add_error(errors, "source.kind", "enum", "Tipo di fonte non ammesso.")
    source_text = source.get("text")
    if not isinstance(source_text, str):
        add_error(errors, "source.text", "type", "Deve essere una stringa, anche quando è vuota.")
        source_text = ""

    candidates = root.get("candidates")
    if not isinstance(candidates, list) or not 1 <= len(candidates) <= 5:
        add_error(errors, "candidates", "count", "Inserire da 1 a 5 candidati.")
        candidates = []

    candidate_ids: set[str] = set()

    for index, candidate_value in enumerate(candidates):
        path = f"candidates[{index}]"
        candidate = require_dict(candidate_value, path, errors)
        candidate_id = require_nonempty_string(candidate, "id", path, errors)
        candidate_text = require_nonempty_string(candidate, "text", path, errors)
        if candidate_id in candidate_ids:
            add_error(errors, f"{path}.id", "duplicate", "L'identificatore del candidato deve essere unico.")
        candidate_ids.add(candidate_id)

        transformation = candidate.get("transformation")
        if transformation not in TRANSFORMATIONS:
            add_error(errors, f"{path}.transformation", "enum", "Trasformazione non ammessa.")

        evidence_status = candidate.get("evidence_status")
        if evidence_status not in EVIDENCE_STATUSES:
            add_error(errors, f"{path}.evidence_status", "enum", "Stato della prova non ammesso.")

        evidence = candidate.get("evidence")
        if not isinstance(evidence, list):
            add_error(errors, f"{path}.evidence", "type", "Deve essere una lista.")
            evidence = []

        valid_excerpts: list[str] = []
        for span_index, span_value in enumerate(evidence):
            span_path = f"{path}.evidence[{span_index}]"
            span = require_dict(span_value, span_path, errors)
            start = span.get("start")
            end = span.get("end")
            excerpt = span.get("excerpt")
            if not isinstance(start, int) or isinstance(start, bool) or start < 0:
                add_error(errors, f"{span_path}.start", "range", "Deve essere un intero non negativo.")
                continue
            if not isinstance(end, int) or isinstance(end, bool) or end < start:
                add_error(errors, f"{span_path}.end", "range", "Deve essere un intero non minore di start.")
                continue
            if not isinstance(excerpt, str):
                add_error(errors, f"{span_path}.excerpt", "type", "Deve essere una stringa.")
                continue
            if end > len(source_text) or source_text[start:end] != excerpt:
                add_error(
                    errors,
                    span_path,
                    "span_mismatch",
                    "Gli offset non ricostruiscono esattamente l'estratto sorgente.",
                )
                continue
            valid_excerpts.append(excerpt)

        attribution = require_dict(candidate.get("attribution"), f"{path}.attribution", errors)
        role = attribution.get("role")
        if role not in ATTRIBUTION_ROLES:
            add_error(errors, f"{path}.attribution.role", "enum", "Ruolo di attribuzione non ammesso.")
        label = attribution.get("label", "")
        if role != "none" and (not isinstance(label, str) or not label.strip()):
            add_error(errors, f"{path}.attribution.label", "required", "Il ruolo richiede un'etichetta visibile.")
        ranking = require_dict(candidate.get("ranking"), f"{path}.ranking", errors)
        score = ranking.get("score")
        if not isinstance(score, int) or isinstance(score, bool) or not 0 <= score <= 100:
            add_error(errors, f"{path}.ranking.score", "range", "Il punteggio deve essere un intero fra 0 e 100.")
        require_nonempty_string(ranking, "reason", f"{path}.ranking", errors)

    selection_value = root.get("selection")
    selection_required = state in STATES - {"bozza", "candidati_pronti"}
    if selection_required and not isinstance(selection_value, dict):
        add_error(errors, "selection", "required", "Lo stato richiede una selezione.")
    if isinstance(selection_value, dict):
        selection = selection_value
        selected_id = require_nonempty_string(selection, "candidate_id", "selection", errors)
        if selected_id and selected_id not in candidate_ids:
            add_error(errors, "selection.candidate_id", "unknown", "Il candidato selezionato non esiste.")
        require_nonempty_string(selection, "reason", "selection", errors)
        approved = selection.get("content_approved")
        if not isinstance(approved, bool):
            add_error(errors, "selection.content_approved", "type", "Deve essere true o false.")
        if state not in {"bozza", "candidati_pronti"} and approved is not True:
            add_error(errors, "selection.content_approved", "state", "Lo stato richiede approvazione editoriale esplicita.")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args(argv)

    try:
        data = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        result = {
            "valid": False,
            "errors": [{"path": "$", "code": "read", "message": str(exc)}],
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    errors = validate_manifest(data)
    print(json.dumps({"valid": not errors, "errors": errors}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
