# Candidate evidence

Evidence date: 2026-08-25, Europe/Rome.

## Local production candidate

- Canonical skill and plugin manifest: `1.7.11`.
- MCP App badge: `v1.34` without a test suffix.
- Current UI resource: `ui://quote-card-builder/preview/v1.34.html`.
- Compatibility resources: v1.26 through v1.33.
- Domain challenge route: implemented, disabled with `404` until a portal token is configured.
- Deployment status: v1.34 is deployed as revision `quote-card-builder-mcp-00064-raf`, ready and
  receiving 100% of production traffic.
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

- `plugin/.codex-plugin/plugin.json`: version `1.7.11`.
- `scripts/mcp_app.py`: badge `v1.34` and current resource
  `ui://quote-card-builder/preview/v1.34.html`.
- Local v1.34 keeps v1.26 through v1.33 compatibility aliases.
- Remote v1.34 resource evidence is recorded below. A fresh hosted ChatGPT click-through remains a
  separate, required verification.

## Deployment evidence

The following evidence applies to the deployed v1.34 candidate.

- Cloud Run service: `quote-card-builder-mcp`.
- Project: `quote-card-builder-mcp`.
- Region: `europe-west8`.
- Cloud Build ID: `6e563164-b49c-4a66-81a0-2b262c85ef7e`, status `SUCCESS`.
- Revision observed after deployment: `quote-card-builder-mcp-00064-raf`, ready and receiving 100%
  traffic.
- Image deployed:
  `europe-west8-docker.pkg.dev/quote-card-builder-mcp/quote-card-builder/quote-card-builder@sha256:97a0410f1c452a07085bfcc59133c08ca48dd872d0be538bcc0dfa893c02c135`.
- Image digest:
  `sha256:97a0410f1c452a07085bfcc59133c08ca48dd872d0be538bcc0dfa893c02c135`.
- Public service URL: `https://quote-card-builder-mcp-960066178304.europe-west8.run.app`.
- Live health response:
  `{"status":"ok","service":"quote-card-builder","mcp_path":"/mcp"}`.
- Live MCP `initialize`: HTTP 200, protocol `2025-06-18`, English workflow instructions.
- Live MCP `resources/read` for `ui://quote-card-builder/preview/v1.34.html` returns a 168,928-byte
  response containing the v1.34 component, **Open PNG**, and **Prepare image**; the obsolete
  **Download PNG** and **Prepare final download** copy is absent.
- Live health response and MCP handshake were verified after routing 100% traffic to v1.34. The
  handshake returned protocol `2025-06-18` and a valid MCP session ID; the initialized
  notification returned HTTP 202.
- Live challenge route returns HTTP 404 while `OPENAI_APPS_CHALLENGE_TOKEN` is intentionally unset.

The first v1.27 revision, `quote-card-builder-mcp-00044-25p`, exposed a missing embedded logo asset
during `resources/read`. Traffic was immediately returned to the working v1.26 revision. The
Dockerfile was corrected, the container contract test was extended, and only corrected revision
`00045-mdw` was then assigned production traffic.

## Package evidence

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

Docker is not installed in the local execution environment. The v1.34 source archive was built by
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
