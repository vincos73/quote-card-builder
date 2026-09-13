#!/usr/bin/env python3
"""Render a small raster proof board for Editorial/Gradient review."""

from __future__ import annotations

import argparse
import copy
import shutil
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
import rasterize
import render_quote_card as renderer


RUNTIME_ROOT = Path("/Users/vincos/.cache/codex-runtimes/codex-primary-runtime/dependencies")
DEFAULT_NODE = RUNTIME_ROOT / "node/bin/node"
DEFAULT_NODE_MODULES = RUNTIME_ROOT / "node/node_modules"


def proof_manifest() -> dict:
    return {
        "canvas": {"width": 1080, "height": 1350},
        "content": {
            "text": "La chiarezza non riempie lo spazio.\nGli dà una direzione.",
            "lines": ["La chiarezza non", "riempie lo spazio.", "Gli dà una direzione."],
            "emphasis": "", "styles": [], "styles_customized": True,
            "attribution": {"label": "VINCOS", "role": "publisher"},
        },
        "brand": {
            "name": "Gradient proof", "font": {"family": "Arial"},
            "colors": {"primary": "#072743", "accent": "#E3F4FF", "background": "#FEFDFB", "text": "#323232"},
        },
        "presentation": {"graphic_mode": "auto", "graphic_variant": "gradient", "graphic_seed": 0,
                           "logo_mode": "hidden"},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("output/gradient-proof"))
    parser.add_argument("--seeds", type=int, nargs="+", default=[7, 42, 1842, 999999])
    parser.add_argument("--node", type=Path, default=DEFAULT_NODE)
    parser.add_argument("--node-modules", type=Path, default=DEFAULT_NODE_MODULES)
    args = parser.parse_args(argv)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest = proof_manifest()
    for seed in args.seeds:
        data = copy.deepcopy(manifest)
        data["presentation"]["graphic_seed"] = seed
        svg = renderer.render_svg(data, Path.cwd(), "editorial")
        svg_path = args.output_dir / f"editorial-gradient-seed-{seed}.svg"
        png_path = args.output_dir / f"editorial-gradient-seed-{seed}.png"
        svg_path.write_text(svg, encoding="utf-8")
        rasterize.rasterize(svg_path, png_path, 1080, 1350, node=args.node, node_modules=args.node_modules)
    renderer.write_contact_sheet(
        [args.output_dir / f"editorial-gradient-seed-{seed}.png" for seed in args.seeds],
        args.output_dir / "gradient-proof.html", "Editorial / Gradient proof board",
        alt_text="Quattro prove raster della variante Editorial Gradient con seed differenti.",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
