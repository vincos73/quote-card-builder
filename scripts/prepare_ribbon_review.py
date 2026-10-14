#!/usr/bin/env python3
"""Prepare three model-authored ribbon scenes for the local review editor."""

from __future__ import annotations

import argparse
import copy
from pathlib import Path

import brand_profiles
from card_review_server import atomic_write_json, read_json, validate_manifest
from grammar_sessions import complete_ribbon_formats, normalize_candidates


def prepare(base: dict, proposals: list, base_dir: Path) -> dict:
    scenes = normalize_candidates(proposals)
    if len(scenes) != 3:
        raise ValueError("La prima esplorazione richiede tre composizioni distinte.")
    result = copy.deepcopy(base)
    result["brand"] = brand_profiles.resolve_brand_assets(result["brand"], base_dir)
    missing = brand_profiles.asset_status(result["brand"])["missing"]
    if missing:
        raise ValueError("Asset non disponibili: " + ", ".join(missing))
    result.update(state="candidato_selezionato", composition_candidates=scenes, proposal_source="model")
    result.setdefault("presentation", {}).update(visual_grammar="ribbons", composition=scenes[0], output_mode="4x5")
    result["formats"] = complete_ribbon_formats(result.get("formats", []), result["content"]["text"])
    for item in result["formats"]:
        item["lines"] = [result["content"]["text"]]
    result["content"]["lines"] = [result["content"]["text"]]
    errors = validate_manifest(result)
    if errors:
        raise ValueError("; ".join(errors))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base", type=Path, help="Manifest locale 0.4 con testo e brand approvati")
    parser.add_argument("proposals", type=Path, help="JSON con composition_candidates numeriche del modello")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        proposal_file = read_json(args.proposals)
        result = prepare(read_json(args.base), proposal_file.get("composition_candidates"), args.base.resolve().parent)
        atomic_write_json(args.output, result)
    except (ValueError, KeyError, OSError) as exc:
        parser.exit(2, f"Progetto non preparato: {exc}\n")
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
