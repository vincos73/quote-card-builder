# Submission checklist

Status legend: **PASS** verified on the current candidate; **PORTAL** must be verified in the
OpenAI submission flow; **BLOCKED** required input or decision is missing; **FIX** candidate work
is recommended before submission.

## Account and submission channel

- **PORTAL** Publisher identity is verified and matches the public listing identity.
- **PORTAL** The submitting account has Apps Management write access (`api.apps.write`).
- **PORTAL** The OpenAI project uses global data residency; an EU-residency project cannot submit
  an MCP server at the time this checklist was prepared.
- **PASS** The candidate is correctly treated as a plugin with an MCP server, not as a skills-only
  package.
- **PASS** The remote Universal MCP URL is known and public.

## Listing

- **PASS** English display name, short description, long description, developer name, category,
  brand color, and three starter prompts have a draft.
- **BLOCKED** Public product website under the publisher's control is not selected.
- **BLOCKED** Public support URL is not selected.
- **BLOCKED** Public privacy policy URL is not selected.
- **BLOCKED** Public terms-of-service URL is not selected.
- **BLOCKED** Production logo is not selected and exported to the portal's required dimensions.
- **BLOCKED** Availability countries have not been selected.
- **BLOCKED** Initial release notes have not been approved.

## MCP server

- **PASS** `/health` responds successfully over HTTPS.
- **PASS** Streamable HTTP `initialize` succeeds with protocol `2025-06-18`.
- **PASS** Four server tools are exposed with explicit input and structured output schemas.
- **PASS** Every tool declares `readOnlyHint=true`, `destructiveHint=false`, and
  `openWorldHint=false`; the operations validate/render in memory and do not change external
  state.
- **PASS** `quote_card_builder_open_editor` and the explicit
  `quote_card_builder_headless` fallback are model-visible; only the editor is linked to the UI
  resource.
- **PASS** `preview_quote_card` and `produce_quote_card` are app-private and do not open duplicate
  components.
- **PASS** The UI resource is `text/html;profile=mcp-app`, declares its domain, keeps connect,
  resource, frame, and base-URI allowlists empty, and limits legacy `openExternal` redirects to
  three exact ChatGPT file origins. Unknown regional origins use the local Blob fallback.
- **PASS** The local candidate has a configurable `/.well-known/openai-apps-challenge` route and
  returns `404` while no token is configured.
- **BLOCKED** Domain verification cannot be completed until the portal issues its token and the
  route is deployed with `OPENAI_APPS_CHALLENGE_TOKEN`.
- **PASS** ChatGPT developer-mode **Aggiorna / Scan Tools** completed against the frozen v1.45
  server on 2026-09-20. It discovered the two public tools, the optional Style preselection, and
  `ui://quote-card-builder/preview/v1.45.html`.

## UI and behavior

- **PASS** Remote `resources/read` serves the deployed v1.45 resource and exposes the ChatGPT host
  file delivery path (`uploadFile` plus `getFileDownloadUrl`) with a local Blob fallback for
  temporary URLs outside the exact redirect allowlist.
- **PASS** The inline editor has two main actions: **Update preview** and **Generate PNG**, with
  clear supporting labels and distinct primary/secondary hierarchy.
- **PASS** Quote, attribution, neutral/custom palette, direction, 4:5/1:1 format, authored line
  breaks, formatting ranges, scale, position, and motif are represented in editor state.
- **PASS** Generate revalidates through the canonical renderer and prepares a PNG in the browser.
- **PASS** Deployed v1.45 preserves the branded masthead, Vincos lockup, visible version badge,
  Barlow interface typography, Plotter Bench palette, square controls, and embedded Orbitron
  wordmark while retaining the host APIs and ChatGPT file delivery integration.
- **PASS** A hosted v1.45 test confirmed that **Generate PNG** prepares the image and **Download
  PNG** opens the complete 1440 by 1800 PNG in a new browser tab. Sending a link to the chat is an
  optional secondary action.
- **PASS** The deployed v1.45 production badge is visible at the upper right and has no `TEST`
  suffix.
- **PASS** The deployed editor grows with its contents and no longer creates an internal
  `overflow:auto` scroll area.
- **PASS** Desktop visual inspection of the exact v1.45 HTML confirmed the restored interface and
  visible badge; narrow-width hosted evidence remains part of the pre-submission browser review.
- **PASS** The complete generate-and-open flow was verified in the hosted ChatGPT iframe on
  2026-09-20; the opened PNG was visibly complete and readable.
- **PORTAL** Confirm keyboard navigation, focus visibility, labels, contrast, and screen-reader
  behavior in the hosted ChatGPT iframe.

## Privacy and operations

- **PASS** No database or bucket is used by the application, and generated SVG data is returned in
  the response rather than retained by the application.
- **PASS** The component sanitizes inline SVG before inserting it into the DOM.
- **PASS** The current test-phase authentication posture is explicitly no-auth. The service is
  stateless and in-memory and neither reads user-specific records nor changes external data.
- **BLOCKED** Before adding user-specific data or external writes, implement and document OAuth
  2.1 and re-run the authentication review.
- **BLOCKED** Privacy copy must cover infrastructure/request logs even though the application does
  not persist quote-card content itself.
- **PASS** The local Dockerfile copies only the MCP server, adapter, application resource, canonical
  renderer, contract, and rasterization dependency.
- **PORTAL** Confirm rate limits, abuse monitoring, dependency-update process, incident contact,
  and retention/deletion statements.

## Release integrity

- **PASS** Local plugin manifest, canonical skill, and remote server are `1.7.21`; local and
  deployed UI are v1.45.
- **PASS** Historical plugin ZIP evidence for 1.7.11 remains recorded; the current v1.45 Cloud Run
  source archive is hashed below.
- **PASS** The project suite passes when socket and headless-browser tests are allowed.
- **PASS** Remote resource `ui://quote-card-builder/preview/v1.41.html` is readable from the
  deployed MCP server.
- **PASS** Local v1.27 source packages have deterministic recorded SHA-256 hashes and clean archive
  listings.
- **PASS** The clean v1.45 source archive has SHA-256
  `6e0cfb655485d246ab8f8ab7a44520bfc574df81463c885fa1124480178754d9` and was deployed as
  revision `quote-card-builder-mcp-00097-qax` with image digest
  `sha256:3d92d083193c40b448c586e809cd46d006a668408bf2f0a1221d64ea7dd6c56f`; the 100% traffic split,
  health, MCP handshake, and resource descriptor are recorded in `submission/evidence.md`.
- **PASS** The v1.45 correction is frozen in clean commit `86b5e2b` on branch
  `codex/qcb-remote-v1.45`.
- **PASS** Deployment, visual-regression, ChatGPT Scan Tools, and hosted PNG evidence for v1.45 is
  recorded after promotion.
- **PASS** The local v1.45 candidate retains compatibility resources through v1.44.
- **PASS** `pytest.ini` restricts default discovery to `tests/` and excludes `work/`.

## Final gate

Do not submit until every **BLOCKED** item is resolved, the final UI is
visually checked in ChatGPT, and the exact frozen commit, package hashes, Cloud Run revision, image
digest, and reviewer test results are recorded together.
