"""Shared limits for Quote Card Builder review and rendering."""

from __future__ import annotations


# Six lines is the product contract used by the renderer and by every backend
# boundary that accepts an editable line split.
MAX_LINES = 6
