#!/usr/bin/env python3
"""Build the web MCP server source from the canonical Docker COPY inputs."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import shlex
import tempfile
import tomllib
import zipfile


ROOT = Path(__file__).resolve().parents[1]
NAME = "quote-card-builder-web-mcp-server"
ORIGIN = "https://quote-card-builder-mcp-960066178304.europe-west8.run.app"
FEATURES = ["ribbons", "urban", "urban_xerox", "portable_personal_bases", "portable_brand_kit", "visual_advisories", "three_output_formats"]
GCLOUD_IGNORE = b"__pycache__/\n*.py[cod]\n"
ROOT_FILES = {"Dockerfile", "requirements-mcp.txt", "pyproject.toml", "uv.lock"}
ASSET_DIRECTORIES = {"assets/card-editor/fonts", "assets/mcp-editor"}
ASSET_FILES = {"assets/card-editor/vincos-lockup-white.svg", "assets/card-editor/quote-card-builder-wordmark.svg",
               "assets/urban/urban-xerox-lime-v1.png"}


def _read_source(root: Path, relative: str) -> bytes:
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"Invalid source path: {relative}")
    source = root / path
    if source.is_symlink() or any(parent.is_symlink() for parent in source.parents if parent != root and parent.is_relative_to(root)):
        raise ValueError(f"Symlink source is not allowed: {relative}")
    if not source.is_file() or not source.resolve().is_relative_to(root):
        raise ValueError(f"Missing or external source: {relative}")
    return source.read_bytes()


def source_files(root: Path = ROOT) -> dict[str, bytes]:
    root = root.resolve()
    files = {relative: _read_source(root, relative) for relative in sorted(ROOT_FILES)}
    dockerfile = files["Dockerfile"].decode("utf-8").replace("\\\n", " ")
    for instruction in re.findall(r"(?m)^COPY\s+(.+)$", dockerfile):
        tokens = json.loads(instruction) if instruction.lstrip().startswith("[") else shlex.split(instruction)
        if not isinstance(tokens, list) or len(tokens) < 2 or any(not isinstance(token, str) for token in tokens):
            raise ValueError("Unsupported Docker COPY instruction.")
        for relative in tokens[:-1]:
            cleaned = relative.rstrip("/")
            if cleaned in ASSET_DIRECTORIES:
                directory = root / cleaned
                if directory.is_symlink() or not directory.is_dir():
                    raise ValueError(f"Missing or symlink asset directory: {relative}")
                for path in sorted(directory.rglob("*")):
                    if path.is_symlink():
                        raise ValueError(f"Symlink asset is not allowed: {path.relative_to(root)}")
                    if path.is_file() and path.name != ".DS_Store" and "__pycache__" not in path.parts:
                        name = path.relative_to(root).as_posix()
                        files[name] = _read_source(root, name)
            elif (cleaned in ROOT_FILES or cleaned in ASSET_FILES
                  or re.fullmatch(r"scripts/[A-Za-z0-9_-]+\.py", cleaned)):
                files[cleaned] = _read_source(root, cleaned)
            else:
                raise ValueError(f"Docker COPY source outside the web server allowlist: {relative}")
    files[".gcloudignore"] = GCLOUD_IGNORE
    bundled = {Path(name).stem for name in files if name.startswith("scripts/") and name.endswith(".py")}
    local = {path.stem for path in (root / "scripts").glob("*.py")}
    for name, content in files.items():
        if not name.startswith("scripts/") or not name.endswith(".py"):
            continue
        for node in ast.walk(ast.parse(content.decode("utf-8"), filename=name)):
            imported = ([item.name.split(".", 1)[0] for item in node.names] if isinstance(node, ast.Import)
                        else [node.module.split(".", 1)[0]] if isinstance(node, ast.ImportFrom) and node.module else [])
            missing = (set(imported) & local) - bundled
            if missing:
                raise ValueError(f"Missing local import in {name}: {', '.join(sorted(missing))}")
    return dict(sorted(files.items()))


def build_info(files: dict[str, bytes]) -> dict:
    version = tomllib.loads(files["pyproject.toml"].decode("utf-8"))["project"]["version"]
    if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("The canonical runtime version must be a semantic version.")
    strings = {}
    for node in ast.parse(files["scripts/mcp_app.py"].decode("utf-8")).body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            strings.update({target.id: node.value.value for target in node.targets if isinstance(target, ast.Name)})
    ui_version = strings.get("QUOTE_CARD_APP_VERSION")
    if not isinstance(ui_version, str) or not re.fullmatch(r"v\d+\.\d+", ui_version):
        raise ValueError("The canonical UI must declare a literal version.")
    for key in ("QUOTE_CARD_PREVIEW_RESOURCE", "QUOTE_CARD_WORKSPACE_RESOURCE"):
        if not strings.get(key, "").endswith(f"/{ui_version}.html"):
            raise ValueError(f"UI version does not match {key}.")
    hashes = {name: hashlib.sha256(content).hexdigest() for name, content in sorted(files.items())}
    canonical = json.dumps(hashes, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {"version": version, "ui_version": ui_version, "file_count": len(hashes), "files": hashes,
            "content_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
            "auth": "none", "origin": ORIGIN, "features": FEATURES.copy()}


def payload(root: Path = ROOT) -> tuple[dict[str, bytes], dict]:
    files = source_files(root)
    info = build_info(files)
    files["BUILD-INFO.json"] = (json.dumps(info, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    return files, info


def _output_path(path: Path, *, new_directory: bool = False) -> Path:
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
        raise ValueError(f"Symlink output is not allowed: {path}")
    resolved = path.resolve()
    if new_directory and resolved.exists():
        raise ValueError(f"Refusing to overwrite frozen server source: {resolved}")
    if not new_directory and resolved.exists() and not resolved.is_file():
        raise ValueError(f"Output is not a regular file: {resolved}")
    return resolved


def build_directory(destination: Path, *, root: Path = ROOT, contents: dict[str, bytes] | None = None) -> Path:
    destination = _output_path(destination, new_directory=True)
    files = contents if contents is not None else payload(root)[0]
    destination.mkdir(parents=True, exist_ok=False)
    for relative, content in files.items():
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    return destination


def build_zip(output: Path, *, root: Path = ROOT, contents: dict[str, bytes] | None = None) -> Path:
    output = _output_path(output)
    checksum_path = _output_path(output.with_suffix(".sha256"))
    files = contents if contents is not None else payload(root)[0]
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=output.parent, suffix=".zip", delete=False) as temporary:
        temporary_path = Path(temporary.name)
    try:
        with zipfile.ZipFile(temporary_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, content in sorted(files.items()):
                entry = zipfile.ZipInfo(f"{NAME}/{name}")
                entry.date_time = (1980, 1, 1, 0, 0, 0)
                entry.compress_type = zipfile.ZIP_DEFLATED
                entry.create_system = 3
                entry.external_attr = 0o100644 << 16
                archive.writestr(entry, content)
        with zipfile.ZipFile(temporary_path) as archive:
            if archive.testzip() is not None:
                raise ValueError("Invalid server source archive.")
        temporary_path.replace(output)
    finally:
        temporary_path.unlink(missing_ok=True)
    checksum_path.write_text(f"{hashlib.sha256(output.read_bytes()).hexdigest()}  {output.name}\n", encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="web MCP server ZIP, with a sibling SHA-256 file")
    parser.add_argument("--directory", type=Path, help="new isolated Docker build/deploy source directory")
    args = parser.parse_args()
    if not args.output and not args.directory:
        parser.error("Provide --output, --directory, or both.")
    try:
        if args.output:
            _output_path(args.output)
            _output_path(args.output.with_suffix(".sha256"))
        if args.directory:
            _output_path(args.directory, new_directory=True)
        files, info = payload()
        result = {key: info[key] for key in ("version", "ui_version", "file_count", "content_sha256")}
        if args.directory:
            result["directory"] = str(build_directory(args.directory, contents=files))
        if args.output:
            result["zip"] = str(build_zip(args.output, contents=files))
    except (OSError, ValueError, SyntaxError, KeyError) as error:
        raise SystemExit(str(error)) from error
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
