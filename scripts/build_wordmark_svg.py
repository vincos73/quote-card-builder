#!/usr/bin/env python3
"""Build the self-contained Orbitron product wordmark used by the MCP iframe."""

from __future__ import annotations

import base64
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FONT = ROOT / "assets" / "card-editor" / "fonts" / "Orbitron-Variable-latin.woff2"
OUTPUT = ROOT / "assets" / "card-editor" / "quote-card-builder-wordmark.svg"


def build_wordmark() -> str:
    """Return a portable SVG that embeds the approved Orbitron variable font."""
    font_data = base64.b64encode(FONT.read_bytes()).decode("ascii")
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<!-- Generated from Orbitron-Variable-latin.woff2 (OFL-1.1). Keep self-contained for the MCP iframe. -->
<svg xmlns="http://www.w3.org/2000/svg" width="660" height="64" viewBox="0 0 660 64" role="img" aria-label="Quote Card Builder">
  <title>Quote Card Builder</title>
  <style><![CDATA[
    @font-face {{
      font-family: 'QCB Orbitron';
      src: url('data:font/woff2;base64,{font_data}') format('woff2');
      font-style: normal;
      font-weight: 400 900;
    }}
    .wordmark {{ font-family: 'QCB Orbitron', sans-serif; text-transform: uppercase; dominant-baseline: alphabetic; }}
  ]]></style>
  <text class="wordmark" x="0" y="48" fill="#B9D936" font-size="43" font-weight="700" letter-spacing="1.6">QUOTE CARD</text>
  <text class="wordmark" x="372" y="48" fill="#9B86AD" font-size="43" font-weight="400" letter-spacing="2.4">BUILDER</text>
</svg>
'''


if __name__ == "__main__":
    OUTPUT.write_text(build_wordmark(), encoding="utf-8")
