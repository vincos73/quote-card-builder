#!/usr/bin/env python3
"""Render an approved quote-card direction as a production social pack."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
import inspect_render as inspector
import rasterize as raster
import render_quote_card as proof


FORMAT_RATIOS = {"4x5": 4 / 5, "1x1": 1.0, "9x16": 9 / 16}
VERTICAL_POSITIONS = {"upper", "center", "lower"}
LOGO_MODES = {"auto", "hidden"}
GRAPHIC_MODES = {"auto", "hidden"}
OUTPUT_MODES = {"all", "4x5", "1x1", "9x16"}
SVG_MODES = {"auto", "keep", "discard"}


def add_error(errors: list[dict[str, str]], path: str, code: str, message: str) -> None:
    errors.append({"path": path, "code": code, "message": message})


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def proof_manifest_for_format(data: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    candidate = copy.deepcopy(data)
    candidate["schema_version"] = "0.2"
    candidate["state"] = "contenuto_approvato"
    candidate["direction"] = (data.get("approval") or {}).get("direction")
    candidate["canvas"] = {"width": 1440, "height": 1800}
    candidate["content"]["lines"] = item.get("lines")
    candidate.pop("approval", None)
    candidate.pop("formats", None)
    return candidate


def validate_production_manifest(data: Any, manifest_dir: Path) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    if not isinstance(data, dict):
        add_error(errors, "$", "type", "Il manifest deve essere un oggetto.")
        return errors
    if data.get("schema_version") != "0.3":
        add_error(errors, "schema_version", "unsupported", "La versione production supportata è 0.3.")
    if data.get("state") != "prova_visuale_approvata":
        add_error(errors, "state", "approval_required", "Il rendering richiede prova_visuale_approvata.")

    content = data.get("content")
    if not isinstance(content, dict):
        add_error(errors, "content", "type", "Il contenuto deve essere un oggetto.")
        content = {}
    text = content.get("text")
    if not isinstance(text, str) or not text.strip():
        add_error(errors, "content.text", "required", "Il testo approvato è obbligatorio.")
        text = ""

    approval = data.get("approval")
    if not isinstance(approval, dict):
        add_error(errors, "approval", "type", "L'approvazione deve essere un oggetto.")
        approval = {}
    if approval.get("direction") not in proof.DIRECTIONS:
        add_error(errors, "approval.direction", "enum", "La direzione approvata non è ammessa.")
    expected_hash = sha256_text(text)
    if approval.get("content_sha256") != expected_hash:
        add_error(errors, "approval.content_sha256", "content_changed", "Il testo non coincide con la prova approvata.")
    for key in ("approved_by", "approved_at"):
        value = approval.get(key)
        if not isinstance(value, str) or not value.strip():
            add_error(errors, f"approval.{key}", "required", "Il checkpoint deve essere registrato.")
    proof_path_value = approval.get("proof_path")
    if not isinstance(proof_path_value, str) or not proof_path_value.strip():
        add_error(errors, "approval.proof_path", "required", "Indicare la prova approvata.")
    elif not proof.resolve_asset(proof_path_value, manifest_dir).is_file():
        add_error(errors, "approval.proof_path", "missing", "La prova approvata non esiste.")

    formats = data.get("formats")
    if not isinstance(formats, list) or not formats:
        add_error(errors, "formats", "required", "Inserire almeno un formato production.")
        return errors

    seen: set[str] = set()
    for index, item in enumerate(formats):
        path = f"formats[{index}]"
        if not isinstance(item, dict):
            add_error(errors, path, "type", "Il formato deve essere un oggetto.")
            continue
        format_id = item.get("id")
        if format_id not in FORMAT_RATIOS:
            add_error(errors, f"{path}.id", "enum", "Usare 4x5, 1x1 o 9x16.")
        elif format_id in seen:
            add_error(errors, f"{path}.id", "duplicate", "Ogni formato può comparire una sola volta.")
        else:
            seen.add(format_id)
        width = item.get("width")
        height = item.get("height")
        text_scale = item.get("text_scale", 1.0)
        vertical_position = item.get("vertical_position", "center")
        if not isinstance(text_scale, (int, float)) or isinstance(text_scale, bool) or not 0.80 <= text_scale <= 1.08:
            add_error(errors, f"{path}.text_scale", "range", "La scala tipografica deve essere compresa fra 0.80 e 1.00; i valori legacy fino a 1.08 vengono limitati al massimo sicuro.")
        if vertical_position not in VERTICAL_POSITIONS:
            add_error(errors, f"{path}.vertical_position", "enum", "Usare upper, center o lower.")
        if not isinstance(width, int) or isinstance(width, bool) or width < 800:
            add_error(errors, f"{path}.width", "range", "La larghezza deve essere almeno 800 px.")
        if not isinstance(height, int) or isinstance(height, bool) or height < 800:
            add_error(errors, f"{path}.height", "range", "L'altezza deve essere almeno 800 px.")
        if (
            format_id in FORMAT_RATIOS
            and isinstance(width, int)
            and not isinstance(width, bool)
            and isinstance(height, int)
            and not isinstance(height, bool)
            and not math.isclose(width / height, FORMAT_RATIOS[format_id], rel_tol=0.001)
        ):
            add_error(errors, f"{path}", "ratio", f"Le dimensioni non rispettano il rapporto {format_id}.")

        common_errors = proof.validate_visual_manifest(proof_manifest_for_format(data, item), manifest_dir)
        for error in common_errors:
            mapped = dict(error)
            if mapped["path"] == "content.lines":
                mapped["path"] = f"{path}.lines"
            elif mapped["path"].startswith("content.lines"):
                mapped["path"] = mapped["path"].replace("content.lines", f"{path}.lines", 1)
            errors.append(mapped)

    presentation = data.get("presentation", {})
    if not isinstance(presentation, dict):
        add_error(errors, "presentation", "type", "La presentazione deve essere un oggetto.")
    else:
        logo_mode = presentation.get("logo_mode", "auto")
        if logo_mode not in LOGO_MODES:
            add_error(errors, "presentation.logo_mode", "enum", "Usare auto o hidden.")
        graphic_mode = presentation.get("graphic_mode", "auto")
        if graphic_mode not in GRAPHIC_MODES:
            add_error(errors, "presentation.graphic_mode", "enum", "Usare auto o hidden.")
        output_mode = presentation.get("output_mode")
        if output_mode is not None and output_mode not in OUTPUT_MODES:
            add_error(errors, "presentation.output_mode", "enum", "Usare all, 4x5, 1x1 o 9x16.")
        elif output_mode == "all" and seen != set(FORMAT_RATIOS):
            add_error(errors, "formats", "selection", "Con output_mode all sono richiesti tutti e tre i formati.")
        elif output_mode in FORMAT_RATIOS and seen != {output_mode}:
            add_error(errors, "formats", "selection", f"Il pacchetto deve contenere soltanto il formato {output_mode} scelto.")
    return errors


def available_text_width(data: dict[str, Any], direction: str, width: int, height: int) -> float:
    # proof.DIRECTION_GEOMETRY is the single source of truth shared with the
    # renderer; this module must never keep its own copy of a margin.
    return proof.direction_geometry(direction, width, height)["text_width"]


def vertical_limits(
    data: dict[str, Any], manifest_dir: Path, direction: str, width: int, height: int,
) -> tuple[float, float]:
    safe = width * 0.085
    presentation = data.get("presentation") or {}
    attribution = str((data.get("content") or {}).get("attribution", {}).get("label", "")).strip()
    upper_limit = safe

    if direction == "editorial":
        if presentation.get("logo_mode", "auto") != "hidden":
            logo = proof.logo_data(data["brand"], manifest_dir, light=False)
            if logo:
                upper_limit = max(upper_limit, height * 0.075 + width * 0.20 / logo[1] + height * 0.025)
        lower_limit = height * 0.82
    elif direction == "statement":
        if presentation.get("logo_mode", "auto") != "hidden":
            logo = proof.logo_data(data["brand"], manifest_dir, light=True)
            if logo:
                upper_limit = max(upper_limit, height * 0.055 + width * 0.20 / logo[1] + height * 0.03)
        lower_limit = height * 0.82
    else:
        if presentation.get("logo_mode", "auto") != "hidden":
            logo = proof.logo_data(data["brand"], manifest_dir, light=False)
            if logo:
                upper_limit = max(upper_limit, height * 0.10 + width * 0.20 / logo[1] + height * 0.03)
        lower_limit = height * 0.82
    return upper_limit, lower_limit


def resolve_statement_strong_rows(visual_lines: list[str], data: dict[str, Any]) -> set[int]:
    """render_svg falls back to an auto-generated signature style when
    content.styles/emphasis are both empty, but that fallback is computed
    inside render_svg itself -- mirror it here too, or an auto-signature
    strong row measures at its un-upscaled 1.0x width during fitting and
    then renders 1.12x larger, overflowing the fitted box.
    """
    content_styles = data["content"].get("styles")
    content_emphasis = data["content"].get("emphasis", "")
    if not content_styles and not content_emphasis and not data["content"].get("styles_customized"):
        content_styles = proof.initial_direction_styles(data["content"]["text"], "statement")
    return proof.statement_strong_rows(visual_lines, content_styles, content_emphasis)


def text_vertical_bounds(
    lines: list[str], font_size: float, data: dict[str, Any], direction: str,
    width: int, height: int, vertical_position: str,
) -> tuple[float, float]:
    geometry = proof.direction_geometry(direction, width, height, vertical_position)
    start_y = geometry["start_y"]
    # 0.82/0.28/0.72 are the block's ascender/descender reach beyond the
    # baselines; unlike the canvas geometry above they exist only here,
    # because the renderer never needs the block's outer bounds.
    if direction == "statement":
        visual_lines = proof.statement_visual_lines(lines, width, height)
        strong_rows = resolve_statement_strong_rows(visual_lines, data)
        block_height = proof.statement_block_height(font_size, visual_lines, strong_rows)
        return (start_y - font_size * 0.82, start_y + block_height - font_size * 0.72)
    line_height = font_size * geometry["line_ratio"]
    return (
        start_y - font_size * 0.82,
        start_y + line_height * (len(lines) - 1) + font_size * 0.28,
    )


def measure_text_box(
    lines: list[str], font_size: float, data: dict[str, Any], manifest_dir: Path,
    direction: str, width: int, height: int,
) -> tuple[float, float, str]:
    """Measure the same visual block used by both fitting and live QA."""
    proof.activate_font_metrics(data["brand"]["font"], manifest_dir)
    geometry = proof.direction_geometry(direction, width, height)
    if direction == "statement":
        visual_lines = proof.statement_visual_lines(lines, width, height)
        strong_rows = resolve_statement_strong_rows(visual_lines, data)
        measured_width = max(
            proof.visual_units(line.upper()) * font_size
            * (proof.STATEMENT_STRONG_MULTIPLIER if index in strong_rows else 1.0)
            for index, line in enumerate(visual_lines) if line
        )
        return (
            measured_width,
            proof.statement_block_height(font_size, visual_lines, strong_rows),
            "deterministic_statement_poster",
        )

    line_ratio = geometry["line_ratio"]
    font = data["brand"]["font"]
    font_value = font.get("medium_path") or font.get("regular_path")
    if font_value:
        try:
            from PIL import ImageFont

            face = ImageFont.truetype(
                str(proof.resolve_asset(font_value, manifest_dir)), max(1, round(font_size))
            )
            return (
                max(float(face.getlength(line)) for line in lines),
                font_size * line_ratio * len(lines),
                "pillow_real_metrics",
            )
        except (ImportError, OSError, ValueError):
            pass
    # editorial and contextual both render the quote at this tracking
    # (render_quote_card.render_svg); matching that here keeps this estimate
    # from over-predicting width and under-sizing the fitted font.
    tracking_em = geometry["tracking_em"]
    measured_width = max(
        proof.visual_units(line) * font_size + tracking_em * font_size * max(0, len(line) - 1)
        for line in lines
    )
    return (
        measured_width,
        font_size * line_ratio * len(lines),
        "font_metrics_ttf" if proof.font_metrics_active() else "deterministic_heuristic",
    )


def layout_measurement(
    lines: list[str], font_size: float, data: dict[str, Any], manifest_dir: Path,
    direction: str, width: int, height: int, vertical_position: str,
) -> dict[str, float | str | bool]:
    measured_width, measured_height, metric = measure_text_box(
        lines, font_size, data, manifest_dir, direction, width, height
    )
    available_width = available_text_width(data, direction, width, height)
    upper_limit, lower_limit = vertical_limits(data, manifest_dir, direction, width, height)
    text_top, text_bottom = text_vertical_bounds(
        lines, font_size, data, direction, width, height, vertical_position
    )
    width_fits = measured_width <= available_width + 0.5
    vertical_fits = text_top >= upper_limit - 0.5 and text_bottom <= lower_limit + 0.5
    return {
        "measured_width": measured_width,
        "measured_height": measured_height,
        "available_width": available_width,
        "upper_limit": upper_limit,
        "lower_limit": lower_limit,
        "text_top": text_top,
        "text_bottom": text_bottom,
        "metric": metric,
        "width_fits": width_fits,
        "vertical_fits": vertical_fits,
        "fits": width_fits and vertical_fits,
    }


def resolve_font_size(
    lines: list[str], data: dict[str, Any], manifest_dir: Path, direction: str,
    width: int, height: int, text_scale: float, vertical_position: str = "center",
) -> tuple[float, str, float, bool, float]:
    """Resolve the true maximum safe size, then apply an optional reduction."""
    maximum_size, fit_mode = fit_font_size(
        lines, data, manifest_dir, direction, width, height, vertical_position
    )
    requested_size = maximum_size * text_scale
    effective_size = min(requested_size, maximum_size)
    auto_fitted = requested_size > maximum_size + 0.01
    if auto_fitted:
        fit_mode = f"{fit_mode}_legacy_scale_capped"
    return effective_size, fit_mode, requested_size, auto_fitted, maximum_size


def fit_font_size(
    lines: list[str], data: dict[str, Any], manifest_dir: Path, direction: str,
    width: int, height: int, vertical_position: str = "center",
) -> tuple[float, str]:
    def fits(size: float) -> bool:
        return bool(layout_measurement(
            lines, size, data, manifest_dir, direction, width, height, vertical_position
        )["fits"])

    low, high = 1.0, float(max(width, height))
    for _ in range(40):
        middle = (low + high) / 2
        if fits(middle):
            low = middle
        else:
            high = middle
    maximum_size = low * 0.997
    metric = str(layout_measurement(
        lines, maximum_size, data, manifest_dir, direction, width, height, vertical_position
    )["metric"])
    return maximum_size, f"{metric}_max_fit"


def render_pack(
    data: dict[str, Any], manifest_path: Path, output_dir: Path, png_mode: str,
    node: Path | None, node_modules: Path | None, svg_mode: str = "auto"
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    direction = data["approval"]["direction"]
    basename = (data.get("output") or {}).get("basename", "quote-card")
    rendered: list[dict[str, Any]] = []
    contact_assets: list[Path] = []
    inspected: list[str] = []
    png_failures: list[str] = []
    png_backends: set[str] = set()

    for item in data["formats"]:
        adapted = proof_manifest_for_format(data, item)
        adapted["canvas"] = {"width": item["width"], "height": item["height"]}
        text_scale = float(item.get("text_scale", 1.0))
        size, fit_mode, requested_size, auto_fitted, maximum_size = resolve_font_size(
            item["lines"], adapted, manifest_path.parent, direction,
            item["width"], item["height"], text_scale, item.get("vertical_position", "center"),
        )
        presentation = data.get("presentation") or {}
        render_options = {
            "vertical_position": item.get("vertical_position", "center"),
            "logo_mode": presentation.get("logo_mode", "auto"),
            "graphic_mode": presentation.get("graphic_mode", "auto"),
        }
        stem = f"{basename}-{direction}-{item['id']}"
        svg_path = output_dir / f"{stem}.svg"
        svg = proof.render_svg(
            adapted,
            manifest_path.parent,
            direction,
            font_size_override=size,
            render_options=render_options,
        )
        # Read the finished drawing, not the estimate that produced it: a
        # production pack must never deliver a card whose text has left the
        # safe area or whose marks sit on the words.
        defects = inspector.inspect_render(
            svg, direction, item["width"], item["height"],
            vertical_position=render_options["vertical_position"],
        )
        if defects:
            raise RuntimeError(
                f"{item['id']}: " + "; ".join(defect["message"] for defect in defects)
            )
        inspected.append(item["id"])
        svg_path.write_text(svg, encoding="utf-8")
        png_path: Path | None = None
        png_backend: str | None = None
        if png_mode != "never":
            candidate = output_dir / f"{stem}.png"
            try:
                # Tries every converter present and checks what came back;
                # the old path swallowed the converter's own error, so a
                # missing PNG arrived with nothing to act on.
                png_backend = raster.rasterize(
                    svg_path, candidate, item["width"], item["height"],
                    node=node, node_modules=node_modules,
                )
                png_path = candidate
                png_backends.add(png_backend)
            except raster.RasterError as error:
                if png_mode == "required":
                    raise RuntimeError(f"{item['id']}: {error}") from error
                png_failures.append(f"{item['id']}: {error}")
        if svg_mode == "discard" and png_path is None:
            raise RuntimeError("Non è possibile eliminare l’SVG senza un PNG riuscito.")
        keep_svg = svg_mode == "keep" or png_path is None
        svg_record = {"path": svg_path.name, "sha256": sha256_file(svg_path)} if keep_svg else None
        if not keep_svg:
            svg_path.unlink()
        contact_assets.append(png_path or svg_path)
        rendered.append(
            {
                "format": item["id"],
                "width": item["width"],
                "height": item["height"],
                "lines": item["lines"],
                "font_size": size,
                "fitting": fit_mode,
                "text_scale": text_scale,
                "requested_font_size": requested_size,
                "maximum_font_size": maximum_size,
                "auto_fitted": auto_fitted,
                "vertical_position": render_options["vertical_position"],
                "graphic_mode": render_options["graphic_mode"],
                "png_backend": png_backend,
                "svg": svg_record,
                "png": {"path": png_path.name, "sha256": sha256_file(png_path)} if png_path else None,
            }
        )

    contact_sheet = output_dir / f"{basename}-{direction}-production.html"
    proof.write_contact_sheet(contact_assets, contact_sheet, f"Production pack — {data['brand']['name']}")
    colors = data["brand"]["colors"]
    approved_proof = proof.resolve_asset(data["approval"]["proof_path"], manifest_path.parent)
    qa_path = output_dir / f"{basename}-{direction}-production-qa.json"
    qa_data = {
        "schema_version": "0.3",
        "status": "automatic_checks_passed",
        "state": "qa",
        "content_sha256": sha256_text(data["content"]["text"]),
        "approval": {
            **data["approval"],
            "proof_sha256": sha256_file(approved_proof),
        },
        "checks": {
            "approved_direction": direction,
            "text_unchanged_in_every_format": True,
            "ratios_valid": True,
            "contrast": {
                "primary_on_background": round(proof.contrast_ratio(colors["primary"], colors["background"]), 2),
                "background_on_primary": round(proof.contrast_ratio(colors["background"], colors["primary"]), 2),
                "accent_on_primary": round(proof.contrast_ratio(colors["accent"], colors["primary"]), 2),
            },
            # Geometry and contrast are verified on the rendered SVG of
            # every format (see inspect_render), so nobody has to catch
            # overflow or colliding marks by eye. The flag below stays True
            # regardless: finalize_quote_card_pack clears it to record that
            # a human signed off editorially, which is a different claim
            # from "the drawing is geometrically sound".
            "render_inspection": {"formats": inspected, "defects": []},
            # Rasterisers disagree slightly on text metrics, so which one
            # produced these files is part of the artifact's provenance.
            "png_backends": sorted(png_backends),
            "png_failures": png_failures,
            "visual_inspection_required": True,
        },
        "formats": rendered,
        "contact_sheet": {"path": contact_sheet.name, "sha256": sha256_file(contact_sheet)},
    }
    qa_path.write_text(json.dumps(qa_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    warnings: list[str] = list(png_failures)
    # Rasterisers do not agree to the pixel: on the same card, headless
    # Chrome drew the widest row about 3% wider than sharp, close enough
    # to the safe-area edge to matter. A substitute backend is better than
    # no PNG, but the user is told which one drew their file.
    substitutes = sorted(png_backends - {raster.PRIMARY_BACKEND})
    if substitutes:
        warnings.append(
            f"PNG prodotti con {', '.join(substitutes)} invece di {raster.PRIMARY_BACKEND}: "
            "le metriche del testo possono differire lievemente dall'SVG verificato."
        )
    return {
        "valid": True,
        "state": "qa",
        "formats": rendered,
        "contact_sheet": str(contact_sheet),
        "qa_report": str(qa_path),
        "warnings": warnings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--png", choices=("never", "auto", "required"), default="auto")
    parser.add_argument("--svg", choices=("auto", "keep", "discard"), default="auto")
    parser.add_argument("--node", type=Path)
    parser.add_argument("--node-modules", type=Path)
    args = parser.parse_args(argv)

    try:
        manifest_path = args.manifest.resolve()
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"valid": False, "errors": [{"path": "$", "code": "read", "message": str(exc)}]}, ensure_ascii=False, indent=2))
        return 1

    errors = validate_production_manifest(data, manifest_path.parent)
    if errors:
        print(json.dumps({"valid": False, "errors": errors}, ensure_ascii=False, indent=2))
        return 1
    try:
        result = render_pack(data, manifest_path, args.output_dir, args.png, args.node, args.node_modules, args.svg)
    except (OSError, RuntimeError) as exc:
        print(json.dumps({"valid": False, "errors": [{"path": "output", "code": "render", "message": str(exc)}]}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
