#!/usr/bin/env python3
"""Persist explicit Quote Card Builder brand profiles outside the skill install."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
MAX_PROFILES = 30
MAX_NAME_LENGTH = 80
MAX_BRAND_BYTES = 100_000
COLOR_KEYS = ("primary", "accent", "background", "text")
HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_store_path() -> Path:
    configured = os.environ.get("QUOTE_CARD_PROFILE_STORE", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path.home() / ".quote-card-builder" / "profiles.json").resolve()


def empty_store() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "profiles": []}


def normalize_name(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("Il nome del profilo deve essere testuale")
    name = " ".join(value.split())
    if not name or len(name) > MAX_NAME_LENGTH:
        raise ValueError(f"Il nome del profilo deve contenere da 1 a {MAX_NAME_LENGTH} caratteri")
    return name


def normalize_brand(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("Il profilo deve contenere un brand valido")
    brand = copy.deepcopy(value)
    brand_name = brand.get("name")
    if not isinstance(brand_name, str) or not brand_name.strip():
        raise ValueError("Il brand deve avere un nome")
    colors = brand.get("colors")
    if not isinstance(colors, dict):
        raise ValueError("Il brand deve contenere la palette")
    for key in COLOR_KEYS:
        color = colors.get(key)
        if not isinstance(color, str) or not HEX_COLOR.fullmatch(color):
            raise ValueError(f"brand.colors.{key} deve essere un colore esadecimale #RRGGBB")
    font = brand.get("font")
    if not isinstance(font, dict) or not isinstance(font.get("family"), str) or not font["family"].strip():
        raise ValueError("Il brand deve contenere una famiglia tipografica")
    encoded = json.dumps(brand, ensure_ascii=False, sort_keys=True).encode("utf-8")
    if len(encoded) > MAX_BRAND_BYTES:
        raise ValueError("Il profilo di brand è troppo grande")
    return brand


def resolve_brand_assets(brand: dict[str, Any], base_dir: Path) -> dict[str, Any]:
    resolved = normalize_brand(brand)
    for section_name in ("font", "logo"):
        section = resolved.get(section_name)
        if not isinstance(section, dict):
            continue
        for key, value in list(section.items()):
            if not key.endswith("_path") or not isinstance(value, str) or not value.strip():
                continue
            candidate = Path(value).expanduser()
            if not candidate.is_absolute():
                candidate = base_dir / candidate
            section[key] = str(candidate.resolve())
    return resolved


def brand_fingerprint(brand: dict[str, Any]) -> str:
    normalized = normalize_brand(brand)
    payload = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def asset_status(brand: dict[str, Any]) -> dict[str, Any]:
    paths: list[str] = []
    for section in (brand.get("font"), brand.get("logo")):
        if not isinstance(section, dict):
            continue
        paths.extend(value for key, value in section.items() if key.endswith("_path") and isinstance(value, str) and value)
    missing = [value for value in paths if not Path(value).expanduser().is_file()]
    return {"ready": not missing, "missing": missing}


def profile_summary(profile: dict[str, Any]) -> dict[str, Any]:
    brand = profile["brand"]
    return {
        "id": profile["id"],
        "name": profile["name"],
        "brand_name": brand["name"],
        "colors": copy.deepcopy(brand["colors"]),
        "font_family": brand["font"]["family"],
        "assets": asset_status(brand),
        "updated_at": profile["updated_at"],
        "fingerprint": profile["fingerprint"],
    }


def read_store(path: Path | None = None) -> dict[str, Any]:
    store_path = (path or default_store_path()).expanduser().resolve()
    if not store_path.exists():
        return empty_store()
    try:
        value = json.loads(store_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Archivio profili non leggibile: {exc}") from exc
    if not isinstance(value, dict) or value.get("schema_version") != SCHEMA_VERSION or not isinstance(value.get("profiles"), list):
        raise ValueError("Archivio profili non valido")
    if len(value["profiles"]) > MAX_PROFILES:
        raise ValueError("Archivio profili oltre il limite consentito")
    normalized_profiles = []
    for item in value["profiles"]:
        if not isinstance(item, dict):
            raise ValueError("Archivio profili non valido")
        brand = normalize_brand(item.get("brand"))
        profile_id = item.get("id")
        if not isinstance(profile_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,63}", profile_id):
            raise ValueError("Identificatore profilo non valido")
        normalized_profiles.append({
            "id": profile_id,
            "name": normalize_name(item.get("name")),
            "brand": brand,
            "fingerprint": brand_fingerprint(brand),
            "created_at": item.get("created_at") if isinstance(item.get("created_at"), str) else now_iso(),
            "updated_at": item.get("updated_at") if isinstance(item.get("updated_at"), str) else now_iso(),
        })
    return {"schema_version": SCHEMA_VERSION, "profiles": normalized_profiles}


def atomic_write_store(path: Path, value: dict[str, Any]) -> None:
    path = path.expanduser().resolve()
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


def slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return (normalized or "profilo")[:48]


def save_profile(name: str, brand: dict[str, Any], path: Path | None = None) -> dict[str, Any]:
    profile_name = normalize_name(name)
    normalized_brand = normalize_brand(brand)
    store_path = (path or default_store_path()).expanduser().resolve()
    store = read_store(store_path)
    timestamp = now_iso()
    existing = next((item for item in store["profiles"] if item["name"].casefold() == profile_name.casefold()), None)
    if existing is None:
        if len(store["profiles"]) >= MAX_PROFILES:
            raise ValueError(f"Puoi salvare al massimo {MAX_PROFILES} profili")
        existing = {
            "id": f"{slug(profile_name)}-{secrets.token_hex(3)}",
            "name": profile_name,
            "created_at": timestamp,
        }
        store["profiles"].append(existing)
    existing.update({
        "name": profile_name,
        "brand": normalized_brand,
        "fingerprint": brand_fingerprint(normalized_brand),
        "updated_at": timestamp,
    })
    store["profiles"].sort(key=lambda item: item["name"].casefold())
    atomic_write_store(store_path, store)
    return copy.deepcopy(existing)


def list_profiles(path: Path | None = None) -> list[dict[str, Any]]:
    return [profile_summary(item) for item in read_store(path)["profiles"]]


def get_profile(profile_id: str, path: Path | None = None) -> dict[str, Any]:
    store = read_store(path)
    profile = next((item for item in store["profiles"] if item["id"] == profile_id), None)
    if profile is None:
        raise ValueError("Profilo non trovato")
    return copy.deepcopy(profile)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, help="Archivio alternativo, utile per test o portabilità")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list", help="Elenca i profili salvati")
    show_parser = subparsers.add_parser("show", help="Mostra un profilo completo")
    show_parser.add_argument("profile_id")
    save_parser = subparsers.add_parser("save", help="Salva il brand contenuto in un manifest")
    save_parser.add_argument("--name", required=True)
    save_parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "list":
            value: Any = {"store": str((args.store or default_store_path()).expanduser().resolve()), "profiles": list_profiles(args.store)}
        elif args.command == "show":
            value = get_profile(args.profile_id, args.store)
        else:
            manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
            if not isinstance(manifest, dict) or not isinstance(manifest.get("brand"), dict):
                raise ValueError("Il manifest non contiene un brand")
            value = save_profile(args.name, resolve_brand_assets(manifest["brand"], args.manifest.resolve().parent), args.store)
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return 0
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
