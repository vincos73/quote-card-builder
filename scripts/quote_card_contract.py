"""Shared limits for Quote Card Builder review and rendering."""

from __future__ import annotations


# The legacy review editor still uses a bounded composition contract. The
# renderer and MCP App accept any authored line split and fit it dynamically.
MAX_LINES = 6
