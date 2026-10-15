"""Validated native geometry for the Urban / brutalista materico grammar."""

from __future__ import annotations

import copy
import math
import random
from typing import Any

from urban_artwork import ARTWORK_IDS, XEROX_ARTWORK_ID

ROLES = {"primary", "accent", "background", "text"}
_ALLOWED_ID = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
)


def _num(v: Any, path: str, lo: float, hi: float) -> float:
    if (
        not isinstance(v, (float, int))
        or isinstance(v, bool)
        or not math.isfinite(v)
        or not lo <= v <= hi
    ):
        raise ValueError(f"{path}: numero fuori intervallo.")
    return float(v)


def _identifier(value: Any, path: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 80
        or any(char not in _ALLOWED_ID for char in value)
    ):
        raise ValueError(
            f"{path}: usare un identificatore breve con lettere, numeri, - o _."
        )
    return value


def _role(value: Any, path: str) -> str:
    if not isinstance(value, str) or value not in ROLES:
        raise ValueError(f"{path}: ruolo colore non valido.")
    return value


def _box(v: Any, name: str) -> dict[str, float]:
    if not isinstance(v, dict) or set(v) != {"x", "y", "width", "height"}:
        raise ValueError(f"{name}: richiede x,y,width,height.")
    b = {k: _num(v[k], name + "." + k, 0, 1) for k in v}
    if (
        b["width"] <= 0
        or b["height"] <= 0
        or b["x"] + b["width"] > 1
        or b["y"] + b["height"] > 1
    ):
        raise ValueError(f"{name}: area non valida.")
    return b


def normalize_urban_composition(value: Any) -> dict[str, Any]:
    required = {
        "version",
        "grammar",
        "id",
        "quote_box",
        "author_box",
        "logo_box",
        "background_role",
        "text_role",
        "highlight_role",
        "blocks",
        "strips",
        "texture",
    }
    if (
        not isinstance(value, dict)
        or not required <= set(value)
        or set(value) - required - {"name", "quote_backing_role", "author_backing_role", "artwork_id"}
        or value.get("grammar") != "urban"
        or type(value.get("version")) is not int
        or value["version"] != 1
    ):
        raise ValueError("composition: scena urban non valida.")
    out = {
        "version": 1,
        "grammar": "urban",
        "id": _identifier(value["id"], "composition.id"),
    }
    if "artwork_id" in value:
        artwork_id = value["artwork_id"]
        if not isinstance(artwork_id, str) or artwork_id not in ARTWORK_IDS:
            raise ValueError("composition.artwork_id: sfondo Urban non disponibile.")
        out["artwork_id"] = artwork_id
    if "name" in value:
        if not isinstance(value["name"], str) or len(value["name"]) > 120:
            raise ValueError(
                "composition.name: usare una stringa di al massimo 120 caratteri."
            )
        out["name"] = value["name"]
    for k in ("quote_box", "author_box", "logo_box"):
        out[k] = _box(value[k], k)
    for k in ("background_role", "text_role", "highlight_role"):
        out[k] = _role(value[k], k)
    for k in ("quote_backing_role", "author_backing_role"):
        if k in value:
            out[k] = _role(value[k], k)
    blocks = value["blocks"]
    if not isinstance(blocks, list) or len(blocks) > 16:
        raise ValueError("blocks: massimo 16 elementi.")
    out["blocks"] = []
    block_ids: set[str] = set()
    for i, b in enumerate(blocks):
        if (
            not isinstance(b, dict)
            or set(b)
            - {"id", "shape", "color_role", "x", "y", "width", "height", "points"}
            or not {"id", "shape", "color_role", "x", "y", "width", "height"} <= set(b)
        ):
            raise ValueError(f"blocks[{i}]: struttura non valida.")
        path = f"blocks[{i}]"
        identifier = _identifier(b["id"], f"{path}.id")
        if identifier in block_ids:
            raise ValueError(f"{path}.id: identificatore duplicato.")
        block_ids.add(identifier)
        shape = b["shape"]
        if not isinstance(shape, str) or shape not in {"rect", "polygon"}:
            raise ValueError(f"{path}.shape: forma non valida.")
        item = {
            "id": identifier,
            "shape": shape,
            "color_role": _role(b["color_role"], f"{path}.color_role"),
        }
        item["x"] = _num(b["x"], f"{path}.x", -0.5, 1.5)
        item["y"] = _num(b["y"], f"{path}.y", -0.5, 1.5)
        item["width"] = _num(b["width"], f"{path}.width", 0.000001, 1)
        item["height"] = _num(b["height"], f"{path}.height", 0.000001, 1)
        if item["shape"] == "polygon":
            pts = b.get("points")
            if not isinstance(pts, list) or not 3 <= len(pts) <= 12:
                raise ValueError(f"blocks[{i}].points: vertici non validi.")
            item["points"] = [
                [_num(p[0], "point.x", -0.5, 1.5), _num(p[1], "point.y", -0.5, 1.5)]
                for p in pts
                if isinstance(p, (list, tuple)) and len(p) == 2
            ]
            if len(item["points"]) != len(pts):
                raise ValueError("vertice non valido.")
        out["blocks"].append(item)
    strips = value["strips"]
    if not isinstance(strips, list) or len(strips) > 12:
        raise ValueError("strips: massimo 12 fasce.")
    out["strips"] = []
    strip_ids: set[str] = set()
    for i, s in enumerate(strips):
        path = f"strips[{i}]"
        if not isinstance(s, dict) or set(s) != {
            "id",
            "color_role",
            "x1",
            "y1",
            "x2",
            "y2",
            "width",
        }:
            raise ValueError(f"{path}: struttura non valida.")
        identifier = _identifier(s["id"], f"{path}.id")
        if identifier in strip_ids:
            raise ValueError(f"{path}.id: identificatore duplicato.")
        strip_ids.add(identifier)
        out["strips"].append(
            {
                "id": identifier,
                "color_role": _role(s["color_role"], f"{path}.color_role"),
                **{
                    key: _num(s[key], f"{path}.{key}", 0.002, 0.2)
                    if key == "width"
                    else _num(s[key], f"{path}.{key}", -0.5, 1.5)
                    for key in ("x1", "y1", "x2", "y2", "width")
                },
            }
        )
    t = value["texture"]
    if (
        not isinstance(t, dict)
        or set(t) != {"seed", "dots", "scratches", "color_role"}
        or type(t["seed"]) is not int
        or not 0 <= t["seed"] <= 999999
        or type(t["dots"]) is not int
        or not 0 <= t["dots"] <= 160
        or type(t["scratches"]) is not int
        or not 0 <= t["scratches"] <= 24
    ):
        raise ValueError("texture: parametri non validi.")
    _role(t["color_role"], "texture.color_role")
    out["texture"] = dict(t)
    return out


def xerox_composition() -> dict[str, Any]:
    """The selected Xerox/lime experiment, with native editable type lanes."""
    return normalize_urban_composition({
        "version": 1, "grammar": "urban", "id": "urban-xerox-lime",
        "name": "Xerox / lime", "artwork_id": XEROX_ARTWORK_ID,
        "quote_box": {"x": .067, "y": .037, "width": .65, "height": .525},
        "author_box": {"x": .072, "y": .59, "width": .52, "height": .06},
        "logo_box": {"x": .072, "y": .665, "width": .20, "height": .035},
        "background_role": "background", "text_role": "text", "highlight_role": "accent",
        "blocks": [], "strips": [],
        "texture": {"seed": 0, "dots": 0, "scratches": 0, "color_role": "text"},
    })


def demo_urban_compositions(text: str = "", seed: int = 0) -> list[dict[str, Any]]:
    density = min(1, max(0, (len(text) - 90) / 300))
    s = int(seed) % 1000000
    common = {
        "version": 1,
        "grammar": "urban",
        "background_role": "background",
        "text_role": "text",
        "highlight_role": "accent",
        "quote_backing_role": "background",
        "author_backing_role": "background",
        "author_box": {"x": 0.09, "y": 0.82, "width": 0.70, "height": 0.075},
        "logo_box": {"x": 0.09, "y": 0.925, "width": 0.22, "height": 0.035},
    }

    def scene(id, name, q, blocks, strips):
        return normalize_urban_composition(
            {
                **copy.deepcopy(common),
                "id": id,
                "name": name,
                "quote_box": q,
                "blocks": blocks,
                "strips": strips,
                "texture": {
                    "seed": s,
                    "dots": 36,
                    "scratches": 4,
                    "color_role": "text",
                },
            }
        )

    return [
        scene(
            "urban-offset-panel",
            "Offset panel / headline",
            {"x": 0.10, "y": 0.24, "width": 0.73, "height": 0.49 - density * 0.07},
            [
                {
                    "id": "panel",
                    "shape": "rect",
                    "color_role": "primary",
                    "x": 0.04,
                    "y": 0.10,
                    "width": 0.40,
                    "height": 0.73,
                },
                {
                    "id": "accent",
                    "shape": "rect",
                    "color_role": "accent",
                    "x": 0.77,
                    "y": 0.15,
                    "width": 0.13,
                    "height": 0.035,
                },
            ],
            [],
        ),
        scene(
            "urban-diagonal-poster",
            "Diagonal print poster",
            {"x": 0.10, "y": 0.19, "width": 0.76, "height": 0.53 - density * 0.06},
            [
                {
                    "id": "diagonal",
                    "shape": "polygon",
                    "color_role": "primary",
                    "x": 0,
                    "y": 0,
                    "width": 1,
                    "height": 1,
                    "points": [
                        [-0.2, 0.55],
                        [0.58, -0.12],
                        [0.81, -0.12],
                        [0.03, 0.55],
                    ],
                },
                {
                    "id": "bar",
                    "shape": "rect",
                    "color_role": "accent",
                    "x": 0.78,
                    "y": 0.63,
                    "width": 0.12,
                    "height": 0.018,
                },
            ],
            [
                {
                    "id": "rule",
                    "color_role": "text",
                    "x1": 0.10,
                    "y1": 0.755,
                    "x2": 0.90,
                    "y2": 0.755,
                    "width": 0.003,
                }
            ],
        ),
        scene(
            "urban-stacked-columns",
            "Stacked column composition",
            {"x": 0.13, "y": 0.25, "width": 0.73, "height": 0.44 - density * 0.05},
            [
                {
                    "id": "column",
                    "shape": "rect",
                    "color_role": "primary",
                    "x": 0.04,
                    "y": 0.12,
                    "width": 0.045,
                    "height": 0.68,
                },
                {
                    "id": "cap",
                    "shape": "rect",
                    "color_role": "accent",
                    "x": 0.13,
                    "y": 0.15,
                    "width": 0.66,
                    "height": 0.035,
                },
            ],
            [
                {
                    "id": "rule-top",
                    "color_role": "text",
                    "x1": 0.13,
                    "y1": 0.20,
                    "x2": 0.86,
                    "y2": 0.20,
                    "width": 0.0025,
                },
                {
                    "id": "rule-bottom",
                    "color_role": "primary",
                    "x1": 0.13,
                    "y1": 0.74,
                    "x2": 0.86,
                    "y2": 0.74,
                    "width": 0.004,
                },
            ],
        ),
    ]
