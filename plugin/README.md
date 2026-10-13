# Quote Card Builder plugin

This is the Quote Card Builder plugin package for ChatGPT and Codex.

The included skill remains in Italian and guides the user through quote selection and visual review. The plugin includes a local MCP server and interactive app; the plugin metadata is in English.

The contents of `skills/quote-card-builder/` are generated from the canonical skill at the repository root. Do not edit that copy separately; use `scripts/build_plugin_package.py` to create a synchronized package.

In release 1.8.8/UI v1.56, a populated URL open and two consecutive updates in the native editor were verified; the current remote version is 1.8.10/UI v1.57. For clear create/proceed intent from a readable URL, the host reads the source and opens one populated editor. The server does not fetch URLs. Missing attribution defaults to none unless supplied by the user or verified in the source; the neutral palette is the default. Subsequent explicit chat edits use the revision-checked `quote_card_builder_update_editor` tool to preserve unspecified editor choices. In ChatGPT, mention the plugin in every follow-up to make its update tool available. Production, browser, and native evidence is recorded in the repository's `RELEASE-STATUS.md`. Automated browser tests use a simulated MCP Apps host.

Version 1.8.10/UI v1.57 is live at 100% of production traffic. Short semantic lines make initial quotes more readable on smartphones without rewriting the source. Attribution is smaller; UI caption CSS is scoped so it no longer changes SVG attribution in the preview. Two focused tests and the remote version/resource/render checks passed. Native ChatGPT and download visual checks are left to the user. See `RELEASE-STATUS.md` for evidence and limits.
The model can also call it with `{}` when the user selects the plugin without a quote, opening an
empty editor. The user edits the quote; absent attribution defaults to none and neutral palette stays selected. Explicit named attribution is preserved, while an intentional named-but-empty choice remains incomplete. `quote_card_builder_open_editor` opens a fullscreen content tab for a quote already
selected or sourced in conversation. In the local 1.8.3 installation, Generate PNG precedes Download PNG.
The remote v1.57 workspace has one Download PNG action that generates and saves the file;
it has no Send PNG to chat action. The remote server returns an empty state; unless a draft is
recovered, UI v1.57 shows the editable four-line sample quote with bold, italic, and highlighted text,
with no author name. Neutral palette is the default when no explicit palette choice exists; formatting
and whitespace edits preserve the demo choices. If explicit quote
content arrives while the demo is untouched, it replaces the sample. For a clear proceed request, the model selects a source quote and opens the populated editor without asking for quote, attribution, or palette confirmation. The workspace can recover its draft locally; it does
not sync drafts across devices or conversations, associate project files or mentions, or apply
model-suggested edits automatically. Local installation does not imply remote publication.

The plugin's MCP server starts through `.mcp.json` with
`uv run --frozen` from the bundled skill directory, using its included `pyproject.toml` and
`uv.lock`. For the guided conversational editor, the skill uses supplied or source-verified attribution and defaults to none and the neutral palette. It does not ask for tone or style and does not replace the
app with direct file generation unless the host explicitly reports that the UI cannot mount; in
that case the dedicated headless fallback requires an explicit production approval. If the user names a style spontaneously, it is only
passed as an editor preselection.
`quote_card_builder_open_editor` opens one interface with a 4:5 or 1:1 SVG preview based on
those choices. `preview_quote_card` is the data tool called by the UI to refresh the same
preview without opening another component. `produce_quote_card` is called only by the
**Generate PNG** button and prepares a capability-based delivery action. **Download PNG** uses the
local UI-private `quote_card_builder_save_png` action to save the exact canvas PNG in
`~/Downloads/Quote Card Builder`. With the `openai/files` host capability it also opens the saved
file using `openai/files/open`. **Send PNG to chat** sends that existing absolute file path via
`ui/message` for a Markdown image and download link. This is enabled only by the local stdio
launcher flag `--local-file-delivery`; HTTP rejects this flag and cannot save local PNGs. Remote
hosts retain native `ui/download-file`, ChatGPT file URLs, and browser Blob compatibility paths.
The UI exposes Blocks, Cutouts,
Constellations, and Gradient, with deterministic pattern variations and an explicit editable
palette in addition to the neutral profile.

The skill remains the orchestrator of the full Visual Review Studio workflow. The thin MCP adapter does not
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
