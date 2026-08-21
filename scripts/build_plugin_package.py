#!/usr/bin/env python3
"""Build the Quote Card Builder plugin from the canonical root skill."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_TEMPLATE = ROOT / "plugin"
PLUGIN_NAME = "quote-card-builder"
SKILL_FILES = ("SKILL.md", "README.md", "PRODUCT.md", "DESIGN.md")
SKILL_DIRECTORIES = ("agents", "assets", "references", "scripts")
IGNORED_NAMES = {".DS_Store", "__pycache__", "build_plugin_package.py"}


def _ignored(_directory: str, names: list[str]) -> set[str]:
    return {name for name in names if name in IGNORED_NAMES or name.endswith((".pyc", ".pyo"))}


def _skill_version() -> str:
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    match = re.search(r"Versione: \*\*(\d+\.\d+\.\d+)", text)
    if not match:
        raise ValueError("Versione della skill non trovata in SKILL.md")
    return match.group(1)


def _manifest() -> dict:
    path = PLUGIN_TEMPLATE / ".codex-plugin" / "plugin.json"
    return json.loads(path.read_text(encoding="utf-8"))


def validate_template() -> None:
    manifest = _manifest()
    if manifest.get("name") != PLUGIN_NAME:
        raise ValueError("Il nome del plugin non coincide con la cartella di destinazione")
    if manifest.get("version") != _skill_version():
        raise ValueError("La versione del plugin non coincide con la skill canonica")
    if manifest.get("skills") != "./skills/":
        raise ValueError("Il manifest deve dichiarare skills come ./skills/")
    if (PLUGIN_TEMPLATE / "skills").exists():
        raise ValueError("La copia generata della skill non deve essere salvata nel template")


def build_directory(destination: Path) -> Path:
    validate_template()
    plugin_root = destination / PLUGIN_NAME
    if plugin_root.exists():
        shutil.rmtree(plugin_root)
    shutil.copytree(PLUGIN_TEMPLATE, plugin_root, ignore=_ignored)

    skill_root = plugin_root / "skills" / PLUGIN_NAME
    skill_root.mkdir(parents=True)
    for relative in SKILL_FILES:
        shutil.copy2(ROOT / relative, skill_root / relative)
    for relative in SKILL_DIRECTORIES:
        shutil.copytree(ROOT / relative, skill_root / relative, ignore=_ignored)
    return plugin_root


def build_zip(output: Path) -> Path:
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="quote-card-builder-plugin-") as temporary:
        plugin_root = build_directory(Path(temporary))
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(plugin_root.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(plugin_root.parent))
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Percorso dello ZIP da creare")
    parser.add_argument("--directory", type=Path, help="Cartella in cui creare il plugin espanso")
    args = parser.parse_args()
    if bool(args.output) == bool(args.directory):
        parser.error("specificare esattamente uno tra --output e --directory")

    result = build_zip(args.output) if args.output else build_directory(args.directory.resolve())
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
