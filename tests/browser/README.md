# Workspace browser verification

This optional smoke test uses a real isolated Chrome browser, the actual MCP
client/server and renderer, and a **simulated MCP Apps host**. It does not prove
installation, sidebar discovery, OAuth, or file delivery inside Codex/ChatGPT.

With project dependencies installed from `uv.lock`, start:

```sh
uv run --frozen python tests/browser/host.py
```

In another terminal, with `playwright` available to Node and Google Chrome installed:

```sh
node tests/browser/workspace.cjs
```

Use `NODE_PATH` if Playwright is supplied by an external runtime. The test does not
use a personal browser profile. `QCB_TEST_PORT` overrides localhost port 8766 in
both commands. Stop the Python server with Ctrl-C afterwards.

Evidence is written under `work/extensions-verification/`: browser results,
desktop and narrow screenshots, and the PNG actually downloaded. The assertions
cover the editable demo, explicit decisions, one-click preview/export/download,
local draft recovery, custom-to-neutral reset, invalid colors, host theme, narrow
layout, clearing a draft and its model context, the guided editor path, local PNG
delivery, exact bytes, and reuse after an unchanged click. It does not send chat
messages.

## Remote PNG smoke test

This separate optional test reads the deployed workspace HTML resource and
forwards browser `tools/call` requests to the real deployed Streamable HTTP MCP
server. The browser still runs inside a simulated MCP Apps host. It verifies
the delayed Italian example, restore/input precedence, the no-attribution/neutral defaults, legacy attribution recovery, named-blank blocking, one-click production and
download, retry and reuse behavior, exact PNG bytes, and a 375px layout. It
records any chat messages and requires the count to remain zero. It does not
verify delivery inside the Codex/ChatGPT client.

Set `QCB_REMOTE_MCP_URL` to the deployed MCP endpoint, including its `/mcp`
path. Start the host and smoke test in separate terminals:

```sh
QCB_REMOTE_MCP_URL=https://deployed-host.example/mcp QCB_REMOTE_TEST_FAIL_FIRST_PUBLISH=1 uv run --frozen python tests/browser/remote_host.py
QCB_REMOTE_MCP_URL=https://deployed-host.example/mcp node tests/browser/remote.cjs
```

The host test fails the first PNG publication once by default to exercise retry;
set `QCB_REMOTE_TEST_FAIL_FIRST_PUBLISH=0` to skip that injected failure. The
Node command needs Playwright and Google Chrome. If Playwright is installed
in a separate Node runtime, set `NODE_PATH` to that runtime's package directory.
`QCB_REMOTE_TEST_PORT` overrides localhost port 8776 for both commands. The
test writes its desktop/mobile screenshots, result JSON, and actual downloaded PNGs under
`work/remote-mcp/browser-1.8.8/`, keeping earlier browser evidence intact.
It also calls the deployed `quote_card_builder_update_editor` with the current
assistant-visible snapshot and checks that a tagged chat edit preserves unrelated
choices, ignores a replayed tool input, keeps later manual edits, seeds a fresh
widget, and yields to a conflicting restored draft.
Run `workspace.cjs` separately to verify the local delivery path; the remote
test asserts that it never invokes the local PNG save tool.

## Local ribbon editor smoke test

This separate test opens the actual local `card-editor` and its HTTP server,
with three numeric compositions, committed Barlow font files and the Vincos
logo. It uses a fresh isolated directory for the project, saved styles, brand
profiles and browser evidence. It never changes active user configuration or
starts a Codex chatbot. It does not verify the native Codex or ChatGPT host.

Choose a fresh output directory and a Node runtime with `playwright`, `sharp`
and Google Chrome available. In the first terminal:

```sh
NODE_PATH=/path/to/node_modules uv run --frozen python tests/browser/ribbons_host.py --output-dir /tmp/qcb-ribbons-smoke --node /path/to/node --node-modules /path/to/node_modules
```

In another terminal:

```sh
NODE_PATH=/path/to/node_modules QCB_RIBBON_OUTPUT=/tmp/qcb-ribbons-smoke /path/to/node tests/browser/ribbons.cjs
```

The host selects an available localhost port and writes `ready.json`. The test
reads that file; `QCB_RIBBON_URL` can override the URL but must still target
localhost. The optional host `--brand-assets` flag accepts the v05 asset folder
containing `fonts/barlow` and `logo` for that exact experimental palette. Without
it, the test uses only committed assets and a dark version of the same palette.
Missing required fonts or logos are reported as an error, rather than silently
substituted. Use a new output directory for each full test and stop the host
with Ctrl-C afterwards.

Assertions cover all three composition thumbnails, selection, automatic size
freezing, local span size, bold, highlights on wrapped lines, an optional author,
draft recovery, saved base reuse, varied geometry, Unicode replacement without
stale emphasis, project JSON import/export, explicit overflow warnings and local
PNG export. The approved SVG must remain identical to the selected preview, and
the exported PNG must match a Chrome rendering of that preview pixel for pixel.
`report.json`, `text-metrics.json`, `pixel-comparison.json`, screenshots and PNGs
record the observed result; structural QA does not certify artistic quality.

## Xerox/lime workspace smoke test

With the simulated host and local MCP server running on port 8787, run the real
browser workflow with:

```sh
QCB_TEST_PORT=8787 uv run python tests/browser/host.py
QCB_XEROX_TEST_URL=http://127.0.0.1:8787 node tests/browser/xerox.cjs
```

It checks the registered artwork and default font, geometric Urban choices,
uploaded brand font and SVG logo, saved base and project recovery, local draft
reload, mobile width, and downloaded PNG dimensions in 4:5, 1:1, and 9:16.
Evidence is written to `work/xerox-browser-verification/`.
