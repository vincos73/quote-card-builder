#!/usr/bin/env python3
"""Build the Quote Card Builder plugin from the canonical root skill."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import tempfile
import tomllib
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_TEMPLATE = ROOT / "plugin"
PLUGIN_NAME = "quote-card-builder"
SKILL_FILES = (
    "SKILL.md",
    "README.md",
    "PRODUCT.md",
    "DESIGN.md",
    "requirements-mcp.txt",
    "pyproject.toml",
    "uv.lock",
)
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
    path = PLUGIN_TEMPLATE / "plugin.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _legacy_manifest() -> dict:
    path = PLUGIN_TEMPLATE / ".codex-plugin" / "plugin.json"
    return json.loads(path.read_text(encoding="utf-8"))


def validate_template() -> None:
    manifest = _manifest()
    legacy = _legacy_manifest()
    interface = manifest.get("extensions", {}).get("com.openai", {}).get("interface")
    if manifest.get("$schema") != "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json":
        raise ValueError("Il manifest root deve usare lo schema Agent Plugins 1.0")
    if not isinstance(interface, dict):
        raise ValueError("Il manifest root deve contenere extensions.com.openai.interface")
    if any(manifest.get(key) != legacy.get(key) for key in ("name", "version", "description", "author", "homepage", "repository", "keywords")):
        raise ValueError("L'identità e i metadati del manifest moderno devono coincidere con l'overlay legacy")
    if interface != legacy.get("interface"):
        raise ValueError("L'interfaccia moderna e quella dell'overlay legacy devono coincidere")
    prompts = interface.get("defaultPrompt")
    if not isinstance(prompts, list) or len(prompts) > 3:
        raise ValueError("Il defaultPrompt deve contenere al massimo tre prompt")
    if set(manifest) & {"skills", "mcpServers", "interface", "apps"}:
        raise ValueError("Il manifest moderno usa percorsi fissi: skills, mcpServers, interface e apps non sono campi root")
    if manifest.get("name") != PLUGIN_NAME:
        raise ValueError("Il nome del plugin non coincide con la cartella di destinazione")
    if manifest.get("version") != _skill_version():
        raise ValueError("La versione del plugin non coincide con la skill canonica")
    if legacy.get("skills") != "./skills/":
        raise ValueError("L'overlay legacy deve dichiarare skills come ./skills/")
    if legacy.get("mcpServers") != "./.mcp.json":
        raise ValueError("L'overlay legacy deve dichiarare mcpServers come ./.mcp.json")
    if (PLUGIN_TEMPLATE / "plugin.json").is_symlink() or not (PLUGIN_TEMPLATE / "plugin.json").is_file():
        raise ValueError("Manca il manifest moderno plugin.json")
    modern_mcp_path = PLUGIN_TEMPLATE / "mcp.json"
    if not modern_mcp_path.is_file():
        raise ValueError("Manca la configurazione MCP portabile mcp.json")
    modern_mcp = json.loads(modern_mcp_path.read_text(encoding="utf-8"))
    if modern_mcp.get("$schema") != "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json":
        raise ValueError("mcp.json deve usare lo schema Agent Plugins 1.0")
    modern_servers = modern_mcp.get("mcpServers")
    modern_server = modern_servers.get(PLUGIN_NAME) if isinstance(modern_servers, dict) else None
    if not isinstance(modern_server, dict) or modern_server.get("type") != "stdio":
        raise ValueError("mcp.json deve dichiarare il server stdio quote-card-builder")
    modern_args = ["run", "--frozen", "python",
                   "${PLUGIN_ROOT}/skills/quote-card-builder/scripts/mcp_server.py", "--local-file-delivery"]
    modern_cwd = "${PLUGIN_ROOT}/skills/quote-card-builder"
    if modern_server.get("command") != "uv" or modern_server.get("args") != modern_args or modern_server.get("cwd") != modern_cwd:
        raise ValueError("mcp.json deve puntare al runtime stdio portabile incluso nel plugin")
    mcp_path = PLUGIN_TEMPLATE / ".mcp.json"
    if not mcp_path.is_file():
        raise ValueError("Il template deve contenere .mcp.json")
    mcp_config = json.loads(mcp_path.read_text(encoding="utf-8"))
    servers = mcp_config.get("mcpServers")
    server = servers.get(PLUGIN_NAME) if isinstance(servers, dict) else None
    if not isinstance(server, dict) or server.get("command") != "uv":
        raise ValueError(".mcp.json deve dichiarare il runtime uv del plugin")
    if server.get("args") != ["run", "--frozen", "python", "scripts/mcp_server.py", "--local-file-delivery"]:
        raise ValueError(".mcp.json deve avviare il server MCP dal lockfile incluso")
    if server.get("cwd") != "skills/quote-card-builder":
        raise ValueError(".mcp.json deve avviare uv dalla skill inclusa")
    if server.get("command") != modern_server.get("command") or server.get("args")[:3] != modern_server.get("args")[:3] or server.get("args")[4:] != modern_server.get("args")[4:]:
        raise ValueError("I launcher MCP moderno e legacy devono avviare lo stesso runtime stdio")
    for filename in ("pyproject.toml", "uv.lock"):
        if not (ROOT / filename).is_file():
            raise ValueError(f"Manca il runtime riproducibile: {filename}")
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    if project.get("project", {}).get("version") != manifest["version"]:
        raise ValueError("La versione del runtime MCP non coincide con il plugin e la skill")
    project_data = project["project"]
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    locked_project = next(
        (package for package in lock.get("package", []) if package.get("name") == project_data["name"]),
        None,
    )
    if not locked_project or locked_project.get("version") != manifest["version"]:
        raise ValueError("La versione nel lockfile non coincide con il runtime MCP")
    requirements = {
        line.strip() for line in (ROOT / "requirements-mcp.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    if requirements != set(project_data.get("dependencies", [])):
        raise ValueError("Le dipendenze del container non coincidono con il runtime MCP")
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
    files = {
        path.relative_to(plugin_root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(plugin_root.rglob("*")) if path.is_file()
    }
    canonical = json.dumps(files, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    build_info = {
        "schema_version": 1,
        "name": PLUGIN_NAME,
        "version": _manifest()["version"],
        "content_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "files": files,
    }
    (plugin_root / "BUILD-INFO.json").write_text(
        json.dumps(build_info, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return plugin_root


def build_zip(output: Path) -> Path:
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="quote-card-builder-plugin-") as temporary:
        plugin_root = build_directory(Path(temporary))
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(plugin_root.rglob("*")):
                if path.is_file():
                    entry = zipfile.ZipInfo(path.relative_to(plugin_root.parent).as_posix())
                    entry.date_time = (1980, 1, 1, 0, 0, 0)
                    entry.compress_type = zipfile.ZIP_DEFLATED
                    entry.create_system = 3
                    entry.external_attr = 0o100644 << 16
                    archive.writestr(entry, path.read_bytes())
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
