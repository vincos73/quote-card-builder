#!/usr/bin/env python3
"""Persist reusable visual styles separately from brand profiles."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
import sys
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
import brand_profiles
from apply_card_review import DIRECTIONS, LOGO_MODES, GRAPHIC_MODES, OUTPUT_MODES, VERTICAL_POSITIONS
from render_quote_card import GRAPHIC_VARIANTS, graphic_seed_allowed


SCHEMA_VERSION = 1
MAX_STYLES = 50
MAX_NAME_LENGTH = 80
PALETTE_KEYS = ("primary", "accent", "background", "text")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_store_path() -> Path:
    configured = os.environ.get("QUOTE_CARD_STYLE_STORE", "").strip()
    return (Path(configured).expanduser() if configured else Path.home() / ".quote-card-builder" / "styles.json").resolve()


def empty_store() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "styles": []}


def normalize_name(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("Il nome dello stile deve essere testuale")
    value = " ".join(value.split())
    if not value or len(value) > MAX_NAME_LENGTH:
        raise ValueError(f"Il nome dello stile deve contenere da 1 a {MAX_NAME_LENGTH} caratteri")
    return value


def _resolve_and_check_assets(brand: dict[str, Any], base_dir: Path | None = None, check_assets: bool = True) -> dict[str, Any]:
    result = brand_profiles.resolve_brand_assets(brand, base_dir or Path.cwd())
    missing: list[str] = []
    for section in (result.get("font"), result.get("logo")):
        if not isinstance(section, dict):
            continue
        for key, value in section.items():
            if key.endswith("_path") and isinstance(value, str) and value and not Path(value).is_file():
                missing.append(value)
    if missing and check_assets:
        raise ValueError("Asset dello stile non disponibili: " + ", ".join(missing))
    return result


def _normalize_presentation(value: Any, direction: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("presentation dello stile non valida")
    allowed = {"logo_mode", "graphic_mode", "graphic_variant", "graphic_seed", "output_mode"}
    if set(value) - allowed:
        raise ValueError("presentation contiene campi non salvabili nello stile")
    presentation = {"logo_mode": value.get("logo_mode", "auto"), "graphic_mode": value.get("graphic_mode", "auto"),
                    "graphic_variant": value.get("graphic_variant", "default"), "graphic_seed": value.get("graphic_seed", 0),
                    "output_mode": value.get("output_mode", "all")}
    if presentation["logo_mode"] not in LOGO_MODES or presentation["graphic_mode"] not in GRAPHIC_MODES:
        raise ValueError("presentation.logo_mode o graphic_mode non valido")
    if presentation["output_mode"] not in OUTPUT_MODES:
        raise ValueError("presentation.output_mode non valido")
    if presentation["graphic_variant"] not in GRAPHIC_VARIANTS.get(direction, set()):
        raise ValueError("presentation.graphic_variant non appartiene alla direzione selezionata")
    if not graphic_seed_allowed(presentation["graphic_seed"]):
        raise ValueError("presentation.graphic_seed deve essere un intero da 0 a 999999")
    return presentation


def _normalize_formats(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise ValueError("formats dello stile non validi")
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, dict) or item.get("id") not in {"4x5", "1x1", "9x16"} or item["id"] in seen:
            raise ValueError("formats dello stile contengono identificatori non validi o duplicati")
        scale = item.get("text_scale")
        position = item.get("vertical_position")
        if not isinstance(scale, (int, float)) or isinstance(scale, bool) or not 0.80 <= scale <= 1.08:
            raise ValueError(f"formats[{item['id']}] text_scale non valido")
        if position not in VERTICAL_POSITIONS:
            raise ValueError(f"formats[{item['id']}] vertical_position non valido")
        result.append({"id": item["id"], "text_scale": scale, "vertical_position": position})
        seen.add(item["id"])
    return result


def _normalize_palette(value: Any) -> dict[str, str]:
    """Keep the legacy raw-draft API as strict as the editor API."""
    if not isinstance(value, dict) or set(value) != set(PALETTE_KEYS):
        raise ValueError("palette deve contenere soltanto primary, accent, background e text")
    palette: dict[str, str] = {}
    for key in PALETTE_KEYS:
        color = value[key]
        if not isinstance(color, str) or not brand_profiles.HEX_COLOR.fullmatch(color):
            raise ValueError(f"palette.{key} deve essere un colore esadecimale #RRGGBB")
        palette[key] = color.upper()
    return palette


def _style_payload(name: Any, candidate: dict[str, Any], base_dir: Path | None = None, check_assets: bool = True) -> dict[str, Any]:
    direction = candidate.get("direction")
    if direction not in DIRECTIONS:
        raise ValueError("direction dello stile non valida")
    brand = _resolve_and_check_assets(candidate.get("brand"), base_dir, check_assets)
    return {"name": normalize_name(name), "brand": brand, "direction": direction,
            "presentation": _normalize_presentation(candidate.get("presentation"), direction),
            "formats": _normalize_formats(candidate.get("formats"))}


def _style_id(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-")[:48] or "stile"
    return f"{slug}-{hashlib.sha256(name.encode()).hexdigest()[:8]}"


def _normalize_item(item: Any, base_dir: Path | None = None) -> dict[str, Any]:
    if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,63}", item["id"]):
        raise ValueError("Archivio stili non valido")
    payload = _style_payload(item.get("name"), item, base_dir, check_assets=False)
    return {"id": item["id"], **payload, "created_at": item.get("created_at", now_iso()), "updated_at": item.get("updated_at", now_iso())}


def read_store(path: Path | None = None) -> dict[str, Any]:
    store_path = (path or default_store_path()).expanduser().resolve()
    if not store_path.exists():
        return empty_store()
    try:
        value = json.loads(store_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Archivio stili non leggibile: {exc}") from exc
    if not isinstance(value, dict) or value.get("schema_version") != SCHEMA_VERSION or not isinstance(value.get("styles"), list):
        raise ValueError("Archivio stili non valido")
    if len(value["styles"]) > MAX_STYLES:
        raise ValueError("Archivio stili oltre il limite consentito")
    return {"schema_version": SCHEMA_VERSION, "styles": [_normalize_item(item) for item in value["styles"]]}


def atomic_write_store(path: Path, value: dict[str, Any]) -> None:
    path = path.expanduser().resolve(); path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(6)}.tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2); stream.write("\n"); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def save_style(name: str, draft: dict[str, Any], manifest: dict[str, Any] | None = None,
               path: Path | None = None, base_dir: Path | None = None) -> dict[str, Any]:
    candidate = copy.deepcopy(draft)
    if manifest is not None and "schema_version" not in candidate:
        candidate = copy.deepcopy(manifest)
        candidate.update({key: copy.deepcopy(draft[key]) for key in ("direction", "presentation", "formats") if key in draft})
        if "palette" in draft:
            candidate["brand"] = copy.deepcopy(candidate["brand"])
            candidate["brand"]["colors"] = _normalize_palette(draft["palette"])
    payload = _style_payload(name, candidate, base_dir)
    store_path = (path or default_store_path()).expanduser().resolve(); store = read_store(store_path)
    existing = next((item for item in store["styles"] if item["name"].casefold() == payload["name"].casefold()), None)
    timestamp = now_iso()
    if existing is None:
        if len(store["styles"]) >= MAX_STYLES: raise ValueError(f"Puoi salvare al massimo {MAX_STYLES} stili")
        existing = {"id": _style_id(payload["name"]), "created_at": timestamp}; store["styles"].append(existing)
    existing.update(payload); existing["updated_at"] = timestamp
    store["styles"].sort(key=lambda item: item["name"].casefold()); atomic_write_store(store_path, store)
    return copy.deepcopy(existing)


def list_styles(path: Path | None = None) -> list[dict[str, Any]]:
    return copy.deepcopy(read_store(path)["styles"])


def get_style(style_id: str, path: Path | None = None) -> dict[str, Any]:
    item = next((item for item in read_store(path)["styles"] if item["id"] == style_id), None)
    if item is None: raise ValueError("Stile non trovato")
    item["brand"] = _resolve_and_check_assets(item["brand"])
    return copy.deepcopy(item)


def apply_style(style_id: str, draft: dict[str, Any], current: dict[str, Any], path: Path | None = None,
                base_dir: Path | None = None) -> dict[str, Any]:
    style = get_style(style_id, path)
    candidate = copy.deepcopy(draft)
    if "schema_version" not in candidate:
        candidate = copy.deepcopy(current)
        candidate.update({key: copy.deepcopy(draft[key]) for key in ("direction", "presentation", "formats") if key in draft})
    candidate["brand"] = copy.deepcopy(style["brand"])
    candidate["direction"] = style["direction"]
    candidate["presentation"] = copy.deepcopy(style["presentation"])
    current_formats = {item["id"]: item for item in candidate.get("formats", [])}
    for settings in style["formats"]:
        if settings["id"] in current_formats:
            current_formats[settings["id"]].update({"text_scale": settings["text_scale"], "vertical_position": settings["vertical_position"]})
    # Applying a style is a preview/editor state transformation. The manifest
    # is deliberately not persisted here, so its revision must remain the
    # same and the returned session can be submitted against that manifest.
    candidate["revision"] = int(current.get("revision", candidate.get("revision", 1)))
    return candidate
