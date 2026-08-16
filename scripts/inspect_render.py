#!/usr/bin/env python3
"""Inspect a *rendered* quote-card SVG and report visual defects.

Every other check in this project validates a prediction: the fitting pass
computes where text will land, and the quality gate trusts that number.
When the prediction is wrong the gate reports success while the card is
visibly broken -- which is exactly how a Poster overflow shipped with
``valid: true``.

This module closes that loop. It parses the SVG that was actually produced
and measures the geometry that is actually in it, so a defect has to
survive both the estimate and the drawing to reach a user.

It is deliberately dependency-free and deterministic: the same SVG always
yields the same findings, so it can run inside the live quality gate and
inside CI without a browser or a rasteriser.
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
import render_quote_card as proof


SVG_NS = "{http://www.w3.org/2000/svg}"

# Fractions of the font size covering a glyph above and below the baseline.
# Generous rather than exact: this module must not invent defects, so the
# box is a little tighter than the real ink for clearance checks and a
# little looser for containment checks (see CONTAINMENT_TOLERANCE).
ASCENT_RATIO = 0.75
DESCENT_RATIO = 0.22
# Rounding in the SVG is 0.1px; anything under a pixel is not a defect.
CONTAINMENT_TOLERANCE = 1.0
# WCAG 2.1: 4.5:1 for text, 3:1 for meaningful non-text.
TEXT_CONTRAST = 4.5
NON_TEXT_CONTRAST = 3.0


def _tag(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _classes(element: ET.Element) -> set[str]:
    return set(element.attrib.get("class", "").split())


def _float(element: ET.Element, key: str, default: float | None = None) -> float | None:
    raw = element.attrib.get(key)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def text_width(value: str, font_size: float, tracking_em: float) -> float:
    """Width of ``value`` as the renderer draws it, tracking included.

    Mirrors highlight_rects' own measurement so a band and the glyphs it
    sits behind cannot be judged by two different rulers.
    """
    if not value:
        return 0.0
    return (
        proof.visual_units(value) * font_size
        + tracking_em * font_size * max(0, len(value) - 1)
    )


def _tracking_em(element: ET.Element, inherited: float) -> float:
    style = element.attrib.get("style", "")
    marker = "letter-spacing:"
    if marker not in style:
        return inherited
    raw = style.split(marker, 1)[1].split(";", 1)[0].strip()
    if not raw.endswith("em"):
        return inherited
    try:
        return float(raw[:-2])
    except ValueError:
        return inherited


def text_boxes(root: ET.Element) -> list[dict[str, Any]]:
    """Bounding boxes for every drawn run of text.

    A ``<text>`` carries defaults its ``<tspan>`` rows may override, and a
    row may itself wrap nested tspans for emphasis; the row's own text is
    what gets drawn, so rows are measured and bare ``<text>`` is measured
    only when it has no rows of its own.
    """
    boxes: list[dict[str, Any]] = []
    for text_el in root.iter(f"{SVG_NS}text"):
        base_x = _float(text_el, "x", 0.0) or 0.0
        base_y = _float(text_el, "y", 0.0) or 0.0
        base_size = _float(text_el, "font-size", 0.0) or 0.0
        base_fill = text_el.attrib.get("fill", "")
        anchor = text_el.attrib.get("text-anchor", "start")
        tracking = _tracking_em(text_el, 0.0)
        classes = _classes(text_el)
        rows = text_el.findall(f"{SVG_NS}tspan")
        candidates: list[tuple[ET.Element | None, str]] = (
            [(row, "".join(row.itertext())) for row in rows]
            if rows
            else [(None, "".join(text_el.itertext()))]
        )
        for row, content in candidates:
            if not content.strip():
                continue
            source = row if row is not None else text_el
            size = _float(source, "font-size", base_size) or base_size
            if size <= 0:
                continue
            x = _float(source, "x", base_x) or base_x
            y = _float(source, "y", base_y) or base_y
            width = text_width(content, size, _tracking_em(source, tracking))
            if anchor == "end":
                x0 = x - width
            elif anchor == "middle":
                x0 = x - width / 2
            else:
                x0 = x
            boxes.append({
                "kind": "text",
                "classes": classes | _classes(source),
                "text": content,
                "font_size": size,
                "fill": source.attrib.get("fill", base_fill),
                "box": (x0, y - size * ASCENT_RATIO, x0 + width, y + size * DESCENT_RATIO),
            })
    return boxes


def _path_points(data: str) -> list[tuple[float, float]]:
    """Absolute points of the simple M/V/H paths this renderer emits."""
    points: list[tuple[float, float]] = []
    x = y = 0.0
    tokens = data.replace(",", " ").split()
    index = 0
    while index < len(tokens):
        command = tokens[index]
        index += 1
        try:
            if command in {"M", "L"}:
                x, y = float(tokens[index]), float(tokens[index + 1])
                index += 2
            elif command == "V":
                y = float(tokens[index])
                index += 1
            elif command == "H":
                x = float(tokens[index])
                index += 1
            else:
                # Curves (the editorial contours) are decorative and never
                # participate in clearance checks; skip their operands.
                continue
        except (IndexError, ValueError):
            break
        points.append((x, y))
    return points


def decoration_boxes(root: ET.Element) -> list[dict[str, Any]]:
    """Bounding boxes for the marks that frame the quote.

    Only elements that can crowd the text are included. The direction
    graphics live in the margins by construction and are excluded, or every
    card would report a false collision with its own background pattern.
    """
    boxes: list[dict[str, Any]] = []
    for element in root.iter():
        classes = _classes(element)
        if not classes & {"quote-corner-mark"}:
            continue
        points = _path_points(element.attrib.get("d", ""))
        if not points:
            continue
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        boxes.append({
            "kind": "decoration",
            "classes": classes,
            "stroke": element.attrib.get("stroke", ""),
            "box": (min(xs), min(ys), max(xs), max(ys)),
        })
    return boxes


def _overlap(first: tuple[float, ...], second: tuple[float, ...]) -> float:
    """Area shared by two boxes; 0.0 when they merely touch."""
    dx = min(first[2], second[2]) - max(first[0], second[0])
    dy = min(first[3], second[3]) - max(first[1], second[1])
    return dx * dy if dx > 0 and dy > 0 else 0.0


def _grounds(root: ET.Element, width: int, height: int) -> list[tuple[tuple[float, ...], str]]:
    """Filled rectangles a foreground element may sit on, back to front."""
    grounds: list[tuple[tuple[float, ...], str]] = []
    for rect in root.iter(f"{SVG_NS}rect"):
        fill = rect.attrib.get("fill", "")
        if not proof.HEX_COLOR.match(fill):
            continue
        x = _float(rect, "x", 0.0) or 0.0
        y = _float(rect, "y", 0.0) or 0.0
        rect_width = _float(rect, "width", 0.0) or 0.0
        rect_height = _float(rect, "height", 0.0) or 0.0
        grounds.append(((x, y, x + rect_width, y + rect_height), fill))
    return grounds


def ground_for(box: tuple[float, ...], grounds: list[tuple[tuple[float, ...], str]]) -> str:
    """Colour behind ``box``: the last painted rect that covers its centre."""
    centre = ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)
    found = ""
    for rect, fill in grounds:
        if rect[0] <= centre[0] <= rect[2] and rect[1] <= centre[1] <= rect[3]:
            found = fill
    return found


def inspect_render(
    svg: str, direction: str, width: int, height: int,
    *, vertical_position: str = "center",
) -> list[dict[str, str]]:
    """Report every visual defect visible in an already-rendered card."""
    findings: list[dict[str, str]] = []

    def report(code: str, message: str) -> None:
        findings.append({"code": code, "message": message})

    try:
        root = ET.fromstring(svg)
    except ET.ParseError as error:
        return [{"code": "svg_invalid", "message": f"SVG non analizzabile: {error}"}]

    geometry = proof.direction_geometry(direction, width, height, vertical_position)
    safe_left = geometry["text_x"]
    safe_right = geometry["text_x"] + geometry["text_width"]
    texts = text_boxes(root)
    decorations = decoration_boxes(root)
    grounds = _grounds(root, width, height)

    quotes = [item for item in texts if "quote" in item["classes"]]
    attributions = [item for item in texts if "attribution" in item["classes"]]

    # 1. The quote must stay inside the margin the user sees as the guide.
    for item in quotes:
        box = item["box"]
        excerpt = item["text"][:40]
        if box[0] < safe_left - CONTAINMENT_TOLERANCE:
            report(
                "text_outside_safe_area",
                f"{direction}: «{excerpt}» inizia a {box[0]:.1f}px, "
                f"prima del margine di sicurezza ({safe_left:.1f}px).",
            )
        if box[2] > safe_right + CONTAINMENT_TOLERANCE:
            report(
                "text_outside_safe_area",
                f"{direction}: «{excerpt}» arriva a {box[2]:.1f}px, "
                f"oltre il margine di sicurezza ({safe_right:.1f}px).",
            )
        if box[1] < -CONTAINMENT_TOLERANCE or box[3] > height + CONTAINMENT_TOLERANCE:
            report(
                "text_outside_canvas",
                f"{direction}: «{excerpt}» esce dalla tela in verticale.",
            )

    # 2. Nothing may sit on top of the quote or the attribution.
    for mark in decorations:
        for item in quotes + attributions:
            if _overlap(mark["box"], item["box"]) > 0:
                report(
                    "decoration_overlaps_text",
                    f"{direction}: un segno decorativo si sovrappone a "
                    f"«{item['text'][:40]}».",
                )
    for attribution in attributions:
        for quote in quotes:
            if _overlap(attribution["box"], quote["box"]) > 0:
                report(
                    "attribution_overlaps_quote",
                    f"{direction}: l'attribuzione si sovrappone alla citazione.",
                )

    # 3. Everything drawn must actually read against what is behind it.
    #    The manifest validator checks the palette's declared pairs; this
    #    checks the pairs that were really emitted, which is where an
    #    accent-on-background stroke slipped through at 1.07:1.
    for item in texts:
        fill = item["fill"]
        ground = ground_for(item["box"], grounds)
        if not proof.HEX_COLOR.match(fill) or not proof.HEX_COLOR.match(ground):
            continue
        ratio = proof.contrast_ratio(fill, ground)
        if ratio < TEXT_CONTRAST:
            report(
                "text_contrast",
                f"{direction}: «{item['text'][:40]}» rende {ratio:.2f}:1 su "
                f"{ground} (minimo {TEXT_CONTRAST}:1).",
            )
    for mark in decorations:
        stroke = mark["stroke"]
        ground = ground_for(mark["box"], grounds)
        if not proof.HEX_COLOR.match(stroke) or not proof.HEX_COLOR.match(ground):
            continue
        ratio = proof.contrast_ratio(stroke, ground)
        if ratio < NON_TEXT_CONTRAST:
            report(
                "decoration_contrast",
                f"{direction}: un segno decorativo rende {ratio:.2f}:1 su "
                f"{ground} (minimo {NON_TEXT_CONTRAST}:1).",
            )

    return findings
