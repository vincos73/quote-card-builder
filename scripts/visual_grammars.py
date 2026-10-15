"""Validated, editable geometry for the experimental ribbon grammar.

Coordinates are data, never SVG source. The renderer is the only component
that turns these bounded numbers into path commands.
"""

from __future__ import annotations

import copy
import math
from typing import Any

COLOR_ROLES = frozenset({"primary", "accent", "background", "text"})
from urban_grammar import normalize_urban_composition, demo_urban_compositions
from urban_artwork import is_xerox
GRAMMAR_PRESENTATION_KEYS = frozenset({
    "visual_grammar", "composition", "quote_font_size", "author_font_size",
})


def _number(value: Any, path: str, low: float, high: float) -> float:
    if (not isinstance(value, (float, int)) or isinstance(value, bool)
            or not math.isfinite(value) or not low <= value <= high):
        raise ValueError(f"{path}: usare un numero finito da {low:g} a {high:g}.")
    return float(value)


def _identifier(value: Any, path: str) -> str:
    if (not isinstance(value, str) or not value or len(value) > 80
            or any(not (char.isascii() and (char.isalnum() or char in "_-")) for char in value)):
        raise ValueError(f"{path}: usare un identificatore breve con lettere, numeri, - o _.")
    return value


def _role(value: Any, path: str) -> str:
    if not isinstance(value, str) or value not in COLOR_ROLES:
        raise ValueError(f"{path}: usare primary, accent, background o text.")
    return value


def _box(value: Any, path: str) -> dict[str, float]:
    if not isinstance(value, dict) or set(value) != {"x", "y", "width", "height"}:
        raise ValueError(f"{path}: richiede x, y, width e height.")
    result = {key: _number(value[key], f"{path}.{key}", 0, 1) for key in value}
    if result["width"] <= 0 or result["height"] <= 0:
        raise ValueError(f"{path}: larghezza e altezza devono essere positive.")
    if result["x"] + result["width"] > 1.000001 or result["y"] + result["height"] > 1.000001:
        raise ValueError(f"{path}: l'area deve rientrare nella card.")
    return result


def normalize_composition(value: Any) -> dict[str, Any]:
    """Return a detached validated composition, or raise ValueError.

    A cubic path has 1+3*n points. Each triple after the initial point is
    its two controls and endpoint; arbitrary lengths/shapes are supported.
    """
    if isinstance(value, dict) and value.get("grammar") == "urban":
        return normalize_urban_composition(value)
    required = {"version", "id", "quote_box", "author_box", "logo_box",
                "background_role", "text_role", "highlight_role", "ribbons", "crossings"}
    if not isinstance(value, dict) or not required <= set(value) or set(value) - required - {"name"}:
        raise ValueError("composition: struttura incompleta o campi non ammessi.")
    if type(value["version"]) is not int or value["version"] != 1:
        raise ValueError("composition.version: la versione supportata è 1.")
    result: dict[str, Any] = {"version": 1, "id": _identifier(value["id"], "composition.id")}
    if "name" in value:
        if not isinstance(value["name"], str) or len(value["name"]) > 120:
            raise ValueError("composition.name: usare un nome di al massimo 120 caratteri.")
        result["name"] = value["name"]
    for key in ("quote_box", "author_box", "logo_box"):
        result[key] = _box(value[key], f"composition.{key}")
    for key in ("background_role", "text_role", "highlight_role"):
        result[key] = _role(value[key], f"composition.{key}")
    ribbons = value["ribbons"]
    if not isinstance(ribbons, list) or not 1 <= len(ribbons) <= 8:
        raise ValueError("composition.ribbons: inserire da 1 a 8 nastri.")
    result["ribbons"] = []
    identifiers: set[str] = set()
    for index, item in enumerate(ribbons):
        path = f"composition.ribbons[{index}]"
        if not isinstance(item, dict) or set(item) != {"id", "color_role", "width_ratio", "points"}:
            raise ValueError(f"{path}: richiede id, color_role, width_ratio e points.")
        identifier = _identifier(item["id"], f"{path}.id")
        if identifier in identifiers:
            raise ValueError(f"{path}.id: identificatore duplicato.")
        identifiers.add(identifier)
        points = item["points"]
        if not isinstance(points, list) or not 4 <= len(points) <= 37 or (len(points) - 1) % 3:
            raise ValueError(f"{path}.points: usare 1+3*n punti, da 4 a 37.")
        normalized_points = []
        for point_index, point in enumerate(points):
            if not isinstance(point, (list, tuple)) or len(point) != 2:
                raise ValueError(f"{path}.points[{point_index}]: usare una coppia x,y.")
            normalized_points.append([
                _number(coordinate, f"{path}.points[{point_index}]", -0.5, 1.5)
                for coordinate in point
            ])
        result["ribbons"].append({
            "id": identifier, "color_role": _role(item["color_role"], f"{path}.color_role"),
            "width_ratio": _number(item["width_ratio"], f"{path}.width_ratio", 0.015, 0.3),
            "points": normalized_points,
        })
    crossings = value["crossings"]
    if not isinstance(crossings, list) or len(crossings) > 32:
        raise ValueError("composition.crossings: usare al massimo 32 incroci.")
    by_id = {item["id"]: item for item in result["ribbons"]}
    result["crossings"] = []
    for index, item in enumerate(crossings):
        path = f"composition.crossings[{index}]"
        if not isinstance(item, dict) or set(item) != {"over", "under", "segment", "t"}:
            raise ValueError(f"{path}: richiede over, under, segment e t.")
        over, under = item["over"], item["under"]
        if (not isinstance(over, str) or not isinstance(under, str) or over == under
                or over not in by_id or under not in by_id):
            raise ValueError(f"{path}: indicare due nastri distinti esistenti.")
        segment = item["segment"]
        if (type(segment) is not int
                or not 0 <= segment < (len(by_id[over]["points"]) - 1) // 3):
            raise ValueError(f"{path}.segment: segmento del nastro superiore non valido.")
        result["crossings"].append({"over": over, "under": under, "segment": segment,
                                     "t": _number(item["t"], f"{path}.t", 0, 1)})
    return result


def normalize_grammar_presentation(value: Any) -> dict[str, Any]:
    """Validate only grammar extras, leaving legacy presentation to its owner."""
    if not isinstance(value, dict):
        raise ValueError("presentation: deve essere un oggetto.")
    extras = set(value) & GRAMMAR_PRESENTATION_KEYS
    if not extras:
        return {}
    if value.get("visual_grammar") not in {"ribbons", "urban"}:
        raise ValueError("presentation.visual_grammar: grammatica non supportata.")
    grammar = value["visual_grammar"]
    result: dict[str, Any] = {"visual_grammar": grammar}
    if "composition" not in value:
        raise ValueError("presentation.composition: scegliere una composizione.")
    result["composition"] = normalize_composition(value["composition"])
    for key in ("quote_font_size", "author_font_size"):
        if key in value:
            result[key] = _number(value[key], f"presentation.{key}", 8, 720)
    if grammar == "urban" and result["composition"].get("grammar") != "urban":
        raise ValueError("presentation.composition: scena urban richiesta.")
    if grammar == "ribbons" and result["composition"].get("grammar") == "urban":
        raise ValueError("presentation.composition: scena ribbons richiesta.")
    return result


def cubic_point(points: list[list[float]], segment: int, t: float) -> tuple[float, float]:
    first = segment * 3
    p0, p1, p2, p3 = points[first:first + 4]
    u = 1 - t
    return tuple(u**3 * p0[axis] + 3*u*u*t*p1[axis] + 3*u*t*t*p2[axis] + t**3*p3[axis]
                 for axis in (0, 1))  # type: ignore[return-value]


def demo_compositions(text: str = "", seed: int = 0, grammar: str = "ribbons") -> list[dict[str, Any]]:
    """Explicit demo choices, never advertised as model-created proposals.

    Consumers may instead submit arbitrary validated compositions. These
    three drawings simply make the first editor usable without a model call.
    """
    if grammar == "urban": return demo_urban_compositions(text, seed)
    length = len(text)
    density = min(1.0, max(0.0, (length - 65) / 280))
    shift = ((int(seed) % 17) - 8) * 0.003
    def box(x: float, y: float, width: float, height: float) -> dict[str, float]:
        return {"x": x, "y": y, "width": width, "height": height}
    def ribbon(identifier: str, role: str, points: list[list[float]], thickness: float = 0.10) -> dict[str, Any]:
        return {"id": identifier, "color_role": role, "width_ratio": thickness,
                "points": points}
    shared = {"version": 1, "background_role": "background", "text_role": "text",
              "highlight_role": "accent", "logo_box": box(.07, .925, .18, .035)}
    proposals = [
        {**shared, "id": "demo-side-loops", "name": "Anse laterali",
         "quote_box": box(.27, .12, .64, .49 + .07*density),
         "author_box": box(.27, .64 + .07*density, .58, .09),
         "ribbons": [
             ribbon("blue", "primary", [[-.12,.04],[.20,.04],[.05,.30],[.115,.49],
                                         [.13,.70],[.13,.865],[.13,.865],
                                         [.19,.865],[.29,.865],[.37,.865],
                                         [.69,.86],[.72,1.02],[.99,1.08]], .105),
             ribbon("pink", "accent", [[1.15,.18],[.93,.12],[1.02,.45],[.99,.64],
                                         [1.05,1.0],[.67,.94],[.54,.94],
                                         [.38,1.01],[.69,1.14],[.92,.99]], .075),
         ], "crossings": [{"over": "blue", "under": "pink", "segment": 3, "t": .35}]},
        {**shared, "id": "demo-roof-weave", "name": "Intreccio in alto",
         "quote_box": box(.08, .38 - .035*density, .82, .38 + .07*density),
         "author_box": box(.08, .80 + .03*density, .67, .07),
         "ribbons": [
             ribbon("pink", "accent", [[-.14,.21],[.04,.02],[.43,.46],[.61,.20],
                                         [.76,-.03],[1.18,.13],[.97,.34]], .10),
             ribbon("blue", "primary", [[-.13,.01],[.09,.34],[.32,-.02],[.44,.11],
                                         [.65,.40],[.84,.06],[1.13,.16]], .12),
         ], "crossings": [{"over": "pink", "under": "blue", "segment": 0, "t": .71}]},
        {**shared, "id": "demo-diagonal-aperture", "name": "Apertura diagonale",
         "quote_box": box(.09, .11, .70, .51 + .07*density),
         "author_box": box(.09, .66 + .06*density, .61, .08),
         "ribbons": [
             ribbon("blue", "primary", [[.60,-.14],[1.25,.02],[1.20,.54],[.96,.76],
                                         [.68,1.00],[.28,.98],[.09,1.18]], .13),
             ribbon("pink", "accent", [[1.17,.05],[1.02,.04],[1.10,.88],[.69,.92],
                                         [.44,1.10],[.08,.95],[-.16,1.05]], .09),
         ], "crossings": [{"over": "blue", "under": "pink", "segment": 1, "t": .38}]},
    ]
    for item in proposals:
        # Alter controls, never swap the fixed semantic areas accidentally.
        for path in item["ribbons"]:
            for index, point in enumerate(path["points"]):
                if index % 3:
                    point[0] += shift
    return [normalize_composition(item) for item in proposals]


def variation_compositions(
    base_composition: Any, text: str = "", seed: int = 0,
) -> list[dict[str, Any]]:
    """Declared demo recompositions inheriting the saved visual recipe.

    These are local scaffold-based suggestions, never model-generated
    directions. In addition to palette roles and stroke widths, inherit
    the base's ribbon repertoire and approximate its handle-to-chord ratio
    so a taut drawing does not silently become a much looser one.
    """
    base = normalize_composition(base_composition)
    if base.get("grammar") == "urban":
        if is_xerox(base):
            # A fresh quote keeps the selected artwork and its typography.
            # Replacing it with vector posters would lose the user's base.
            return [copy.deepcopy(base)]
        proposals = demo_compositions(text, seed, grammar="urban")
        for index, proposal in enumerate(proposals):
            for key in ("background_role", "text_role", "highlight_role"):
                proposal[key] = base[key]
            proposal["id"] = f"demo-variation-{base['id'][:52]}-{index+1}"
            proposal["name"] = f"{base.get('name', 'Urban')[:80]} — variazione dimostrativa {index+1}"
            proposal["texture"] = copy.deepcopy(base["texture"])
        return [normalize_composition(item) for item in proposals]
    proposals = demo_compositions(text, seed)

    def curvature(points: list[list[float]]) -> float:
        ratios = []
        for start in range(0, len(points) - 1, 3):
            p0, p1, p2, p3 = points[start:start + 4]
            chord = math.dist(p0, p3)
            if chord > .02:
                ratios.append((math.dist(p0, p1) + math.dist(p2, p3)) / chord)
        return sum(ratios) / len(ratios) if ratios else 1.0

    def bounded(value: float) -> float:
        return max(-.5, min(1.5, value))

    for proposal_index, proposal in enumerate(proposals):
        for key in ("background_role", "text_role", "highlight_role"):
            proposal[key] = base[key]
        proposal["id"] = f"demo-variation-{base['id'][:52]}-{proposal_index + 1}"
        base_name = base.get("name") or "Nastri"
        proposal["name"] = f"{base_name[:80]} — variazione dimostrativa {proposal_index + 1}"
        scaffolds = proposal["ribbons"]
        inherited_paths = []
        source_ids: dict[str, str] = {}
        source_use_count: dict[str, int] = {}
        for index, original in enumerate(base["ribbons"]):
            scaffold = next((path for path in scaffolds if path["id"] == original["id"]), None)
            if scaffold is None:
                scaffold = next((path for path in scaffolds if path["color_role"] == original["color_role"]), None)
            if scaffold is None:
                scaffold = scaffolds[index % len(scaffolds)]
            points = copy.deepcopy(scaffold["points"])
            # Each extra ribbon must have its own path, rather than becoming
            # an invisible duplicate underneath the first matching role.
            count = source_use_count.get(scaffold["id"], 0)
            source_use_count[scaffold["id"]] = count + 1
            offset = (.055 * math.ceil(count / 2) * (1 if count % 2 else -1)) if count else 0.0
            handle_ratio = max(.65, min(1.35, curvature(original["points"]) / max(.1, curvature(points))))
            for start in range(0, len(points) - 1, 3):
                first, control1, control2, last = points[start:start + 4]
                points[start + 1] = [bounded(first[axis] + (control1[axis] - first[axis]) * handle_ratio)
                                     for axis in (0, 1)]
                points[start + 2] = [bounded(last[axis] + (control2[axis] - last[axis]) * handle_ratio)
                                     for axis in (0, 1)]
            if offset:
                points = [[bounded(point[0] + offset), bounded(point[1] - offset / 2)] for point in points]
            inherited_paths.append({"id": original["id"], "color_role": original["color_role"],
                                    "width_ratio": original["width_ratio"], "points": points})
            source_ids.setdefault(scaffold["id"], original["id"])
        proposal["ribbons"] = inherited_paths
        proposal["crossings"] = [
            {**crossing, "over": source_ids[crossing["over"]], "under": source_ids[crossing["under"]]}
            for crossing in proposal["crossings"]
            if (crossing["over"] in source_ids and crossing["under"] in source_ids
                and source_ids[crossing["over"]] != source_ids[crossing["under"]])
        ]
    return [normalize_composition(proposal) for proposal in proposals]
