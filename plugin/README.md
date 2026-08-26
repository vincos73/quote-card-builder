# Quote Card Builder plugin

This is the Quote Card Builder plugin package for ChatGPT and Codex.

The included skill remains in Italian and guides the user from quote selection through Visual Review Studio and production of approved social formats. The remote MCP App interface and plugin metadata are in English.

The contents of `skills/quote-card-builder/` are generated from the canonical skill at the repository root. Do not edit that copy separately; use `scripts/build_plugin_package.py` to create a synchronized package.

The plugin includes a local MCP vertical slice: `.mcp.json` starts the stdio server.
Before opening the editor, the skill always asks for the quote, visible attribution or none,
a neutral or custom palette, and the Editorial, Poster, or Frame direction. It does not ask
for tone and does not replace the app with a file generated directly in chat.
`quote_card_builder_open_editor` opens one interface with a 4:5 or 1:1 SVG preview based on
those choices. `preview_quote_card` is the data tool called by the UI to refresh the same
preview without opening another component. `produce_quote_card` is called only by the
**Generate PNG** button and prepares an **Open PNG** action. In ChatGPT it uses the optional host
file APIs with `library: false`, opens the temporary PNG in a browser tab, and tells the user to
save it from the browser; compatible hosts without those APIs retain a local Blob fallback.
The application server does not persist the generated card. The UI exposes
the internal `editorial`, `statement`, and `contextual` directions and an explicit custom
palette in addition to the neutral profile.

The skill remains the orchestrator of the full local workflow. The thin MCP adapter does not
replace the canonical Python renderer or the complete Visual Review Studio workflow. The MCP
dependency is pinned in `skills/quote-card-builder/requirements-mcp.txt`; follow the
[pilot documentation](skills/quote-card-builder/references/mcp-pilot.md) for local testing.
The server also includes an optional MCP App HTML resource and structured SVG output as a
fallback for hosts that do not mount the iframe. The package does not include Cloud Run
deployment configuration, remote authentication, or storage.
