# Candidate evidence

Evidence date: 2026-09-07, Europe/Rome.

## Local v1.39 Windows delivery candidate — 2026-09-07

- Observed Windows result on released plugin 1.7.11: the user could create the quote card, but
  **Open PNG** produced no usable result.
- Candidate fix: plugin 1.7.12 with UI v1.39 keeps external opening only as a compatibility path.
  It prefers host-mediated `ui/download-file`, falls back to sending the PNG through `ui/message`,
  and can hand the validated temporary URL to the conversation when only the ChatGPT bridge is
  available. Host calls have bounded timeouts and visible failure states.
- Local verification: 237 tests passed with no skips in a fresh environment containing the pinned
  MCP dependency. Dedicated JavaScript tests cover native download, direct PNG transfer to chat,
  temporary-link hand-off, external-open compatibility, and rejection of unapproved download hosts.
- Local plugin package: `quote-card-builder-plugin-v1.7.12.zip`, archive-tested with no errors;
  SHA-256 `8c68b6f960f6f2181b72fc476e628c5056a61dde548c8fe90a80b1b3ace1410d`.
- Status boundary: this candidate is not yet deployed and has not yet completed a real Windows
  click-through. The deployed MCP App remains v1.38.

## Native MCP Apps PNG delivery — 2026-09-03

- Observed v1.37 desktop result: ChatGPT Desktop did not expose the optional ChatGPT file APIs, so
  the component reached its final Blob-link fallback and reported `Save request sent to this host`;
  the sandbox did not produce a visible save action.
- Fix: v1.38 negotiates MCP Apps protocol `2026-01-26`, completes
  `ui/notifications/initialized`, and reads the host capabilities returned by `ui/initialize`.
  It prefers `ui/download-file` with an embedded base64 PNG resource. If native download is absent
  but image messages are supported, it sends the PNG itself through `ui/message`. The old
  ChatGPT-specific upload/link APIs and local Blob remain compatibility fallbacks.
- Local verification: 228 tests passed, 9 optional tests skipped, and 210 subtests passed. Dedicated
  JavaScript tests validate the embedded PNG, filename, MIME type, native download request, and
  image-message fallback.
- Cloud Run source archive: `dist/quote-card-builder-cloudrun-v1.38-clean.tar.gz`.
  SHA-256: `9e650d54d7e37b8b36266990c2c19e138785535dc7945ce2b71e8eda19308561`.
- Cloud Build ID: `2b0aa6d0-fb05-4089-bc92-48986d6abd3c`, status `SUCCESS`.
- Image digest: `sha256:372ea9fe1eaa674328e18de6711b2bf0861cef4382588616a7c33a0a07de879b`.
- Cloud Run revision: `quote-card-builder-mcp-00074-mod`, tag `v138`, ready and receiving 100%
  of production traffic.
- Live verification: health 200; MCP initialize and initialized notification succeeded; v1.38
  resource read returned 175,218 bytes and contained `ui/download-file`, `ui/message`,
  `2026-01-26`, and the initialized notification; a complete editor canary returned
  `isError=false`, `valid=true`, and `rendered=true`.

## Chat hand-off delivery — 2026-09-03

- Observed v1.36 desktop result: the primary action reached the native-link fallback and reported
  `Direct link opened`, but ChatGPT Desktop's widget sandbox produced no external navigation.
- Fix: v1.37 removes the misleading visible direct-link fallback. When `openExternal` is absent but
  the ChatGPT conversation bridge is available, the primary action becomes **Send link to chat**.
  It associates the uploaded PNG through `setWidgetState.imageIds` and uses
  `sendFollowUpMessage` to request one host-rendered **Download PNG** link for the exact temporary
  URL. Hosts that expose `openExternal` retain **Open PNG**.
- Local verification: 226 tests passed, 9 optional tests skipped, and 210 subtests passed. Dedicated
  JavaScript tests cover both external-open and chat-hand-off capability sets.
- Cloud Run source archive: `dist/quote-card-builder-cloudrun-v1.37-clean.tar.gz`.
  SHA-256: `4d2b280aa64c2c192cfbce3435d883bf3ed9979067e4baaac5497c03591b71d9`.
- Cloud Build ID: `28db8a20-e652-482a-a586-fca88590330c`, status `SUCCESS`.
- Image digest: `sha256:fdda0aa6ccaf61647b1b3e991b064e419f2d6417be4437da1f902c8bed95d91b`.
- Cloud Run revision: `quote-card-builder-mcp-00072-xiv`, tag `v137`; it received 100% of traffic
  before the v1.38 promotion and is now retained with 0% traffic.
- Live verification: health 200, initialize 200, initialized notification 202, v1.37 resource read
  200 (173,884 bytes), and a complete editor canary 200 with `isError=false`.

## Desktop interaction resize and diagnostics — 2026-09-03

- Reported behavior on ChatGPT Desktop: neither **Open PNG** nor **Direct link** produced a visible
  result, and the widget status did not appear to change.
- Fix: the component now reports dynamic height through both the portable
  `ui/notifications/size-changed` notification and ChatGPT's `notifyIntrinsicHeight` extension.
  **Open PNG** changes status before invoking `openExternal` and replaces an unbounded host wait
  with a five-second timeout and visible error.
- Local verification: 225 tests passed, 9 optional tests skipped, and 210 subtests passed.
- Cloud Run source archive: `dist/quote-card-builder-cloudrun-v1.36-clean.tar.gz`.
  SHA-256: `ebcd393c09f443f20a0c7809294f56ec9f0bebd3abaf48d950f3ef998c8f5d6e`.
- Cloud Build ID: `4b69ffaa-04c6-47bb-9a7a-4c7ffc478a2c`, status `SUCCESS`.
- Image digest: `sha256:7bd59a77bad7cce4ee516d0c1e140152208a31c12ee085495c35c90e9655c483`.
- Cloud Run revision: `quote-card-builder-mcp-00070-vod`, tag `v136`; it received 100% of traffic
  before the v1.37 promotion and is now retained with 0% traffic.
- Live verification: health, MCP initialize/initialized, v1.36 `resources/read`, and a complete
  `quote_card_builder_open_editor` canary passed. Final click-through remains a user-visible hosted
  verification step.

## Delivery fallback hotfix — 2026-09-03

- Cause addressed: the hosted **Open PNG** action could rely on the host external-open bridge
  without leaving a usable browser link when that bridge did not visibly open a tab.
- Fix: the direct PNG link is now exposed whenever a delivery URL exists, and the button falls
  back to activating that normal browser link when the host bridge is unavailable.
- Cloud Build ID: `8400f30a-0737-430c-a5c7-4138324cb6dd`, status `SUCCESS`.
- Image digest: `sha256:d4fb824b4876d64cdeebfbc4632b088633e9c6b8a8ae52623923650f2ce15021`.
- Cloud Run revision: `quote-card-builder-mcp-00068-val`; it received 100% of production traffic
  before the v1.36 promotion and is now retained by revision name with 0% traffic.
- Live verification: health and MCP handshake passed; the served v1.35 resource contains
  `Open PNG`, `Direct link`, and `directDownload.click()`.
- Local verification: 225 tests passed, with one protocol test skipped because the MCP SDK is not
  installed in the local environment.

## Deployed v1.35 candidate — 2026-09-03

- Local MCP App badge and resource: `v1.35` and
  `ui://quote-card-builder/preview/v1.35.html`.
- The temporary ChatGPT file URL is resolved and origin-validated before **Open PNG** is enabled.
- v1.26 through v1.34 compatibility resources share the same redirect allowlist and serve the
  current v1.35 component.
- The interface offers a direct recovery link and no longer claims that a tab opened when it can
  only prove that the host accepted the request.
- Local result: 234 tests passed, including the MCP protocol and HTTP transport suite.
- Deployment status: revision `quote-card-builder-mcp-00066-doc` is ready and receives 100% of
  production traffic. The previous v1.34 revision remains available through its `v134` tag.

## Historical deployed v1.34 baseline

- Canonical skill and plugin manifest: `1.7.11`.
- MCP App badge: `v1.34` without a test suffix.
- Current UI resource: `ui://quote-card-builder/preview/v1.34.html`.
- Compatibility resources: v1.26 through v1.33.
- Domain challenge route: implemented, disabled with `404` until a portal token is configured.
- Historical deployment: revision `quote-card-builder-mcp-00064-raf`, retained through its `v134`
  tag with 0% of production traffic after the v1.35 promotion.
- Header typography: v1.34 embeds the approved `Orbitron-Variable-latin.woff2` in the product SVG,
  prevents host font fallback, and tightens the optical spacing between the two title groups.
- PNG delivery: v1.34 converts the canonical SVG to PNG in the browser, uploads it through the
  optional ChatGPT file bridge with `library: false`, requests a temporary download URL, and opens
  that URL through the host. Other compatible hosts retain the local Blob fallback.
- Hosted behavior observed after deployment: ChatGPT presents its external-link confirmation and
  opens the temporary PNG URL in a browser tab; it does not force a download. Deployed v1.34
  therefore labels the action **Open PNG** and instructs the user to save from the browser.

The actual local Streamable HTTP server was started with a non-production test value for
`OPENAI_APPS_CHALLENGE_TOKEN`. Both `/health` and `/.well-known/openai-apps-challenge` returned
HTTP 200; the challenge body matched the configured test value. No token value is retained in
this public evidence pack.

## Version alignment

- `plugin/.codex-plugin/plugin.json`: local candidate version `1.7.12`.
- `scripts/mcp_app.py`: local candidate badge `v1.39` and resource
  `ui://quote-card-builder/preview/v1.39.html`; the deployed candidate remains v1.38.
- Local v1.39 keeps v1.26 through v1.38 compatibility aliases; deployed v1.38 keeps v1.26 through
  v1.37.
- Remote v1.38 resource evidence is recorded above. A fresh hosted ChatGPT click-through remains a
  separate, required verification.

## Deployment evidence

The following evidence applies to the deployed v1.35 candidate.

- Cloud Run service: `quote-card-builder-mcp`.
- Project: `quote-card-builder-mcp`.
- Region: `europe-west8`.
- Cloud Build ID: `8f434ba7-f3a1-47e2-9859-afa856e50ab1`, status `SUCCESS`.
- Revision observed after deployment: `quote-card-builder-mcp-00066-doc`, ready and receiving 100%
  traffic.
- Image deployed:
  `europe-west8-docker.pkg.dev/quote-card-builder-mcp/quote-card-builder/quote-card-builder@sha256:6803e300d242a0e44c0ab664eee9c781cc890a8c71509be9ad87e64992529544`.
- Image digest:
  `sha256:6803e300d242a0e44c0ab664eee9c781cc890a8c71509be9ad87e64992529544`.
- Public service URL: `https://quote-card-builder-mcp-960066178304.europe-west8.run.app`.
- Live health response:
  `{"status":"ok","service":"quote-card-builder","mcp_path":"/mcp"}`.
- Live MCP `initialize`: HTTP 200, protocol `2025-06-18`, English workflow instructions.
- Live MCP `resources/read` for `ui://quote-card-builder/preview/v1.35.html` returns a 170,118-byte
  response containing the v1.35 component, **Open PNG**, **Direct link**, URL validation, and the
  exact temporary-file redirect origin.
- Live health response and MCP handshake were verified after routing 100% traffic to v1.35. The
  handshake returned protocol `2025-06-18` and a valid MCP session ID; the initialized
  notification returned HTTP 202.
- A direct canary `tools/call` to `quote_card_builder_open_editor` returned HTTP 200,
  `isError=false`, `valid=true`, the requested statement direction, and a rendered SVG.
- Live challenge route returns HTTP 404 while `OPENAI_APPS_CHALLENGE_TOKEN` is intentionally unset.

The first v1.27 revision, `quote-card-builder-mcp-00044-25p`, exposed a missing embedded logo asset
during `resources/read`. Traffic was immediately returned to the working v1.26 revision. The
Dockerfile was corrected, the container contract test was extended, and only corrected revision
`00045-mdw` was then assigned production traffic.

## Package evidence

- Cloud Run source archive: `dist/quote-card-builder-cloudrun-v1.35-clean.tar.gz`
  - SHA-256: `ede96ef7cdf8a0d8dc47d7dfdd4ac8a76c020a3277b8568dfaa57de2efbaa662`
  - contains 21 allowlisted deployment files and no detected credentials
  - uploaded, built, and deployed as Cloud Build `8f434ba7-f3a1-47e2-9859-afa856e50ab1`
- Local v1.35 plugin candidate: `/tmp/quote-card-builder-plugin-v1.7.11-ui-v1.35.zip`
  - SHA-256: `2a72eb2cba201f4a273b4ea755964b1c0cff331c364b21526cec46a861482c9f`
  - archive-tested with `unzip -t`

- Local v1.31 candidate package: `dist/quote-card-builder-plugin-v1.7.11.zip`
  - SHA-256: `3642108255c659f2a6c1db48ecb2778e15bfd90ccfbb5bbbee72c1c401177f3c`
  - archive-tested with `unzip -t`
  - `unzip -t`: no errors
- Cloud Run source archive: `dist/quote-card-builder-cloudrun-v1.34-clean.tar.gz`
  - SHA-256: `f41b0509483f63d4cf2f6d6421baf3445803c1627f27a0e5cb87aa12e897cb63`
  - archive listing verified locally and in Cloud Shell; built without macOS extended headers
  - uploaded, built, and deployed as Cloud Build `6e563164-b49c-4a66-81a0-2b262c85ef7e`

Historical v1.28 deployment evidence remains in the repository history; the prior production
revision was `quote-card-builder-mcp-00047-tpj` with image digest
`sha256:f5df9d06a66350b11428e39cb2e0eac658a1c3903b7996b06c78fbb3b82ea81a`.

Historical v1.27 package evidence remains for auditability:

- Local production package: `dist/quote-card-builder-plugin-v1.7.7.zip`
  - SHA-256: `4d46b5af9f94ca35d9b8de1e7aad4659d6069cafec7d3487b53afba5117139eb`
  - 45 archive entries
  - `unzip -t`: no errors
  - official local plugin validator: passed
- Local production source: `dist/quote-card-builder-cloudrun-v1.27-fixed.tar.gz`
  - SHA-256: `15e25d071d6f2539c29506651bc299dc201db9b4834527949d823351ae3bf220`
  - contains only Docker configuration, the MCP/renderer dependency chain, bundled fonts, and the
    approved Vincos lockup used by the self-contained UI
  - no `work/`, `__pycache__`, `.pyc`, `.DS_Store`, or AppleDouble entries found by the archive
    hygiene check

The previously observed production package remains:

- `dist/quote-card-builder-plugin-v1.7.6.zip` —
  `384a4957931e54877df34dc53d68847aa90b57b1336af4738b5aeebb24220535`.
- `dist/quote-card-builder-cloudrun-v1.26.tar.gz` —
  `d05af3659176c253cfb91442be7ce4f735886041fa78a472d82a8a16dc80d51e`.

## Test evidence

Verified command:

```text
python3 -m pytest -q tests
```

The complete test suite passes when socket and headless-browser tests are allowed:

```text
225 passed, 9 skipped, 210 subtests passed in 4.62s
```

The same suite inside the restricted sandbox produced three environmental failures (two denied
localhost binds and one denied Chrome process); the unrestricted verification above passed.

The local production candidate adds `pytest.ini`, so bare `python3 -m pytest -q` is constrained to
the canonical `tests/` directory and does not collect archives under `work/`.

Docker is not installed in the local execution environment. The v1.35 source archive was built by
Cloud Build; the resulting image digest, Cloud Run revision, traffic split, MCP handshake,
resource payload, and health response are recorded above. A fresh visual click-through and real
open-and-save flow in the hosted ChatGPT iframe remain required before submission.

## Architectural evidence

- `scripts/mcp_server.py` imports the MCP adapter from `mcp_quote_card.py`.
- `mcp_quote_card.py` delegates rendering to `render_quote_card.py`.
- The MCP UI transports editor state and sanitizes returned SVG before DOM insertion.
- Browser-side PNG conversion consumes the canonical SVG; it does not redraw the card with a
  separate layout engine.
- The server declares no external write, destructive, or open-world behavior for any tool.

## Reproducibility caveat

The worktree is detached and contains modified and untracked files. The package hashes and remote
revision above identify the observed candidate, but a clean source commit has not yet been frozen
as its reproducible release origin.
