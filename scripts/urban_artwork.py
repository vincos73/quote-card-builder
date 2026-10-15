"""Versioned artwork bundled with both Quote Card Builder runtimes.

Scenes store a small, stable identifier. The renderer embeds the registered
image in each SVG; workspace state and personal bases never duplicate it.
"""
from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
XEROX_ARTWORK_ID = "urban-xerox-lime-v1"
ARTWORK_IDS = frozenset({XEROX_ARTWORK_ID})
XEROX_COLORS = {
    "primary": "#171714", "accent": "#D3E600",
    "background": "#F3EFE1", "text": "#171714",
}


def is_xerox(composition: Any) -> bool:
    return isinstance(composition, dict) and composition.get("artwork_id") == XEROX_ARTWORK_ID


def xerox_font() -> dict[str, str]:
    font = str(ROOT / "assets/card-editor/fonts/BarlowCondensed-Black.ttf")
    return {"family": "Barlow Condensed Black", "regular_path": font, "bold_path": font}


@lru_cache(maxsize=1)
def artwork_data_uri(artwork_id: str) -> str:
    if not isinstance(artwork_id, str) or artwork_id not in ARTWORK_IDS:
        raise ValueError("Urban artwork is not registered.")
    # Never interpret a scene identifier as an arbitrary filesystem path or URL.
    path = ROOT / "assets/urban/urban-xerox-lime-v1.png"
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")
