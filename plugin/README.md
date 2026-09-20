# Quote Card Builder plugin

This is the Quote Card Builder plugin package for ChatGPT and Codex.

The included skill remains in Italian and guides the user from quote selection through Visual Review Studio and production of approved social formats. The remote MCP App interface and plugin metadata are in English.

The contents of `skills/quote-card-builder/` are generated from the canonical skill at the repository root. Do not edit that copy separately; use `scripts/build_plugin_package.py` to create a synchronized package.

The plugin includes a local MCP vertical slice: `.mcp.json` starts the stdio server with
`uv run --frozen` from the bundled skill directory, using its included `pyproject.toml` and
`uv.lock`. Before opening the editor, the skill asks only for the quote, visible attribution or
none, and a neutral or custom palette. It does not ask for tone or style and does not replace the
app with direct file generation unless the host explicitly reports that the UI cannot mount; in
that case the dedicated headless fallback requires an explicit production approval. If the user names a style spontaneously, it is only
passed as an editor preselection.
`quote_card_builder_open_editor` opens one interface with a 4:5 or 1:1 SVG preview based on
those choices. `preview_quote_card` is the data tool called by the UI to refresh the same
preview without opening another component. `produce_quote_card` is called only by the
**Generate PNG** button and prepares a capability-based delivery action. It prefers the standard
MCP Apps **Download PNG** request (`ui/download-file`), which lets the host save an embedded PNG
from its sandbox. In ChatGPT it next uploads a real file with `window.openai.uploadFile`, resolves
its temporary URL with `getFileDownloadUrl`, and exposes a direct **Download PNG** action. Image
messages through `ui/message` remain a fallback only for hosts without file APIs; non-sandboxed
hosts can retain the local Blob fallback.
The application server does not persist the generated card. The UI exposes Blocks, Cutouts,
Constellations, and Gradient, with deterministic pattern variations and an explicit editable
palette in addition to the neutral profile.

The skill remains the orchestrator of the full local workflow. The thin MCP adapter does not
replace the canonical Python renderer or the complete Visual Review Studio workflow. The MCP
dependency is pinned in `skills/quote-card-builder/pyproject.toml` and locked in
`skills/quote-card-builder/uv.lock`; follow the
[pilot documentation](skills/quote-card-builder/references/mcp-pilot.md) for local testing.
The server also includes an optional MCP App HTML resource. App calls keep the canonical SVG in
`_meta.quoteCard.svg` and return compact structured state; when a host genuinely cannot mount the
iframe, the model-visible `quote_card_builder_headless` tool returns an explicit SVG resource.
Production through that fallback requires `ui_unavailable=true`, caller approval, and the SHA-256
of the current preview. The package does not include Cloud Run
deployment configuration, remote authentication, or storage.
