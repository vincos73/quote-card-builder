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
