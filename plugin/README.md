# Quote Card Builder plugin

This folder describes the local stdio plugin package for ChatGPT and Codex. Its bundled skill remains in Italian. The generated `skills/quote-card-builder/` copy comes from the canonical repository root; use `scripts/build_plugin_package.py` rather than editing that copy separately.

The hosted web package is separate: `web-plugin/` connects through streamable HTTP and includes an English skill for the remote editor. Build it with `python3 scripts/build_web_plugin_package.py`. It requires no local Python executor. Installing the stdio package does not publish or install the web package; neither operation proves public Plugin Directory availability.

## Current web MCP — 1.8.11 / UI v1.58

The remote server is live at 100% of production traffic. Nastri joins Blocks, Cutouts, Constellations and Gradient. The model can supply three different native numeric scenes; the user chooses and refines the selected scene in the same editor. Deterministic editor variations are labeled as demos and do not invoke a model.

The editor supports 4:5, 1:1 and 9:16, one format per PNG download. Nastri provides independent quote and author sizes and a relative size for selected words, alongside the existing text formatting controls. Visual warnings are descriptive, without correction buttons, and do not block preview or download. Invalid data or a technical failure that prevents creating the file remains an error.

Web bases are saved on the client/device when storage is available and include the card content, attribution and formatting as well as palette and geometry. Project JSON transfers the full card explicitly. New-quote reuse resets stale ranges and provenance; attribution comes from the optional reuse-dialog field, which may be prefilled and can be cleared. A text-only chat edit preserves unrequested fields. There is no account or device sync and no upload of brand fonts or logos. The local Visual Review Studio has a different style-base format that excludes quote and ranges.

For clear create/proceed intent from a readable URL, the host reads the source and opens one populated editor. The server does not fetch URLs. Missing attribution defaults to none unless supplied by the user or verified in the source; the neutral palette is the default. Follow-up chat edits use `quote_card_builder_update_editor` with the complete current snapshot and revision, preserving unspecified choices and rejecting stale updates. In ChatGPT, mention the plugin again when a follow-up needs its tool.

`quote_card_builder_open_workspace` with `{}` opens an empty workspace. When no draft is recovered, the UI shows a labeled editable example without an author. `quote_card_builder_open_editor` opens the populated editor once; `preview_quote_card` refreshes it without mounting another app. The current **Download PNG** action calls `produce_quote_card`, rasterizes the canonical SVG and initiates delivery with one click. It has no separate Generate or Send PNG to chat action. SVG and proposal images travel in MCP metadata; the model context keeps numeric scene data.

On 14 October 2026, the user confirmed that the ChatGPT test worked. This is user-reported operation, not a new automated test of the complete native host flow. The 475-test suite and remote protocol/PNG smoke evidence have their own scope. See [RELEASE-STATUS.md](../RELEASE-STATUS.md) and the [web ribbon reference](../references/ribbons-web-mcp.md) for the evidence and limits.

## Local transport and historical installation

The local package starts through `.mcp.json` using `uv run --frozen` from its bundled skill directory, with the included `pyproject.toml` and `uv.lock`. Only the stdio launcher enables `--local-file-delivery`; HTTP rejects that option. The UI-private `quote_card_builder_save_png` saves the exact canvas PNG to `~/Downloads/Quote Card Builder` and can open the confirmed file through `openai/files/open` when supported. Remote delivery uses host download capabilities and a verified temporary HTTPS link when required.

The user's installed local version remains **1.8.3**, with its older UI and **Generate PNG** followed by **Download PNG**. Its two-format interface and Send PNG to chat action are historical capabilities of that installation, not the current web UI. The Visual Review Studio is a separate local editor, with multi-format ZIP export and explicit local brand profiles.

Both current editors treat visual quality warnings as advisory; the local Visual Review Studio exports with `quality_policy: advisory`. The standalone CLI renderer retains `quality_policy: strict` as its default and can reject visual defects. Do not apply that standalone policy to the user's editor choices.

When a host genuinely cannot mount the app, `quote_card_builder_headless` provides an explicit SVG preview resource. Production through that fallback requires `ui_unavailable=true`, caller approval and the SHA-256 of the current preview. The fallback does not establish that a PNG was delivered. The local plugin package does not include the hosted deployment configuration or remote account storage.
