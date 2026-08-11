#!/usr/bin/env python3
"""Finalize a production pack after visual inspection of every rendered format."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_output(base: Path, value: str) -> Path:
    candidate = (base / value).resolve()
    try:
        candidate.relative_to(base.resolve())
    except ValueError as exc:
        raise ValueError(f"Percorso esterno al pacchetto: {value}") from exc
    return candidate


def verify_artifact(base: Path, record: Any, label: str, errors: list[str]) -> None:
    if record is None:
        return
    if not isinstance(record, dict) or not isinstance(record.get("path"), str) or not isinstance(record.get("sha256"), str):
        errors.append(f"Record non valido: {label}")
        return
    try:
        path = resolve_output(base, record["path"])
    except ValueError as exc:
        errors.append(str(exc))
        return
    if not path.is_file():
        errors.append(f"File mancante: {record['path']}")
    elif sha256_file(path) != record["sha256"]:
        errors.append(f"Hash non valido: {record['path']}")


def finalize(data: Any, qa_path: Path, reviewer: str) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return None, ["Il report QA deve essere un oggetto."]
    if data.get("schema_version") != "0.3":
        errors.append("Il report non usa lo schema 0.3.")
    if data.get("status") != "automatic_checks_passed" or data.get("state") != "qa":
        errors.append("Il report non è pronto per l'ispezione finale.")
    formats = data.get("formats")
    if not isinstance(formats, list) or not formats:
        errors.append("Il report non contiene formati.")
        formats = []
    inspected: list[str] = []
    for index, item in enumerate(formats):
        if not isinstance(item, dict) or not isinstance(item.get("format"), str):
            errors.append(f"Formato non valido all'indice {index}.")
            continue
        inspected.append(item["format"])
        verify_artifact(qa_path.parent, item.get("svg"), f"formats[{index}].svg", errors)
        verify_artifact(qa_path.parent, item.get("png"), f"formats[{index}].png", errors)
    verify_artifact(qa_path.parent, data.get("contact_sheet"), "contact_sheet", errors)
    if errors:
        return None, errors

    finalized = dict(data)
    finalized["status"] = "passed"
    finalized["state"] = "consegnato"
    checks = dict(finalized.get("checks") or {})
    checks["visual_inspection_required"] = False
    checks["visual_inspection_passed"] = True
    finalized["checks"] = checks
    finalized["visual_review"] = {
        "reviewer": reviewer,
        "inspected_formats": inspected,
        "completed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    return finalized, []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("qa_report", type=Path)
    parser.add_argument("--all-formats", action="store_true", help="Conferma che ogni formato è stato ispezionato.")
    parser.add_argument("--reviewer", required=True)
    args = parser.parse_args(argv)
    if not args.all_formats:
        print(json.dumps({"valid": False, "errors": ["Usare --all-formats soltanto dopo aver ispezionato ogni output."]}, ensure_ascii=False, indent=2))
        return 1
    try:
        qa_path = args.qa_report.resolve()
        data = json.loads(qa_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"valid": False, "errors": [str(exc)]}, ensure_ascii=False, indent=2))
        return 1
    finalized, errors = finalize(data, qa_path, args.reviewer.strip())
    if errors or finalized is None or not args.reviewer.strip():
        if not args.reviewer.strip():
            errors.append("Il reviewer non può essere vuoto.")
        print(json.dumps({"valid": False, "errors": errors}, ensure_ascii=False, indent=2))
        return 1
    qa_path.write_text(json.dumps(finalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"valid": True, "state": "consegnato", "qa_report": str(qa_path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
