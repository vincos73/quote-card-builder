#!/usr/bin/env python3
"""Build the remote-only MCP plugin without a local executor or stdio server."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "web-plugin"
NAME = "quote-card-builder-web"
REFERENCE = ROOT / "references" / "ribbons-web-mcp.md"


def build_zip(output: Path) -> Path:
    manifest = json.loads((TEMPLATE / "plugin.json").read_text(encoding="utf-8"))
    mcp = json.loads((TEMPLATE / "mcp.json").read_text(encoding="utf-8"))
    version = manifest["version"]
    canonical = re.search(r'Versione: \*\*(\d+\.\d+\.\d+)', (ROOT / "SKILL.md").read_text())
    if manifest["name"] != NAME or canonical is None or canonical.group(1) != version:
        raise ValueError("Web package identity/version differs from canonical source.")
    interface = manifest["extensions"]["com.openai"]["interface"]
    if len(interface["shortDescription"]) > 30:
        raise ValueError("Web package subtitle exceeds 30 characters.")
    servers = mcp["mcpServers"]
    if set(servers) != {"quote-card-builder"} or servers["quote-card-builder"] != {
        "type": "streamable-http",
        "url": "https://quote-card-builder-mcp-960066178304.europe-west8.run.app/mcp",
    }:
        raise ValueError("Unexpected web MCP endpoint or local executor configuration.")
    files = {}
    for path in sorted(TEMPLATE.rglob("*")):
        if path.is_symlink():
            raise ValueError("Symlinks are not allowed in web package.")
        if path.is_file():
            files[path.relative_to(TEMPLATE).as_posix()] = path.read_bytes()
    files["skills/quote-card-builder/references/ribbons-web-mcp.md"] = REFERENCE.read_bytes()
    hashes = {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}
    ui_version = re.search(r'QUOTE_CARD_APP_VERSION = "(v[^"\n]+)"', (ROOT / "scripts/mcp_app.py").read_text()).group(1)
    for reference in ("urban-web-mcp.md", "personal-bases.md", "brand-kits.md"):
        files[f"skills/quote-card-builder/references/{reference}"] = (ROOT / "references" / reference).read_bytes()
    hashes = {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}
    info = {"version": version, "ui_version": ui_version, "transport": "streamable-http",
            "requires_local_executor": False, "files": hashes,
            "content_sha256": hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()}
    files["BUILD-INFO.json"] = (json.dumps(info, indent=2) + "\n").encode()
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=output.parent, suffix=".zip", delete=False) as temporary:
        temporary_path = Path(temporary.name)
    try:
        with zipfile.ZipFile(temporary_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, data in sorted(files.items()):
                entry = zipfile.ZipInfo(f"{NAME}/{name}")
                entry.date_time = (1980, 1, 1, 0, 0, 0)
                entry.compress_type = zipfile.ZIP_DEFLATED
                entry.external_attr = 0o100644 << 16
                archive.writestr(entry, data)
        with zipfile.ZipFile(temporary_path) as archive:
            if archive.testzip() is not None:
                raise ValueError("Invalid web package archive.")
        temporary_path.replace(output)
    finally:
        temporary_path.unlink(missing_ok=True)
    checksum = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(".sha256").write_text(f"{checksum}  {output.name}\n")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    print(build_zip(parser.parse_args().output))
