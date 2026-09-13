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
- **PASS** Three tools are exposed with explicit input and structured output schemas.
- **PASS** Every tool declares `readOnlyHint=true`, `destructiveHint=false`, and
  `openWorldHint=false`; the operations validate/render in memory and do not change external
  state.
- **PASS** Only `quote_card_builder_open_editor` is model-visible and linked to the UI resource.
- **PASS** `preview_quote_card` and `produce_quote_card` are app-private and do not open duplicate
  components.
- **PASS** The UI resource is `text/html;profile=mcp-app`, declares its domain, and has empty exact
  CSP allowlists because it is self-contained.
- **PASS** The local candidate has a configurable `/.well-known/openai-apps-challenge` route and
  returns `404` while no token is configured.
- **BLOCKED** Domain verification cannot be completed until the portal issues its token and the
  route is deployed with `OPENAI_APPS_CHALLENGE_TOKEN`.
- **PORTAL** Run **Scan Tools** against the final frozen server and resolve all reported issues.

## UI and behavior

- **PASS** Remote `resources/read` serves the deployed v1.34 resource and exposes the ChatGPT host
  file delivery path (`uploadFile` plus `getFileDownloadUrl`).
- **PASS** The inline editor has two main actions: **Update preview** and **Generate PNG**, with
  clear supporting labels and distinct primary/secondary hierarchy.
- **PASS** Quote, attribution, neutral/custom palette, direction, 4:5/1:1 format, authored line
  breaks, formatting ranges, scale, position, and motif are represented in editor state.
- **PASS** Generate revalidates through the canonical renderer and prepares a PNG in the browser.
- **PASS** Deployed v1.34 embeds Orbitron in a self-contained SVG wordmark with tightened optical
  spacing and uses ChatGPT's host file APIs for PNG delivery when available.
- **PASS** A hosted v1.33 test confirmed the title rendering and showed that ChatGPT opens the
  temporary PNG URL rather than forcing a browser download. Deployed v1.34 labels this behavior
  accurately as **Open PNG** and tells the user to save the image from the browser.
- **PASS** The deployed v1.34 production badge has no `TEST` suffix.
- **PASS** The deployed editor grows with its contents and no longer creates an internal
  `overflow:auto` scroll area.
- **FIX** Capture desktop and narrow-width visual evidence from the final production resource.
- **FIX** Verify the complete open-and-save flow in the hosted ChatGPT iframe; protocol and
  resource checks prove the delivery code is live but do not prove the user-visible click-through.
- **PORTAL** Confirm keyboard navigation, focus visibility, labels, contrast, and screen-reader
  behavior in the hosted ChatGPT iframe.

## Privacy and operations

- **PASS** No database or bucket is used by the application, and generated SVG data is returned in
  the response rather than retained by the application.
- **PASS** The component sanitizes inline SVG before inserting it into the DOM.
- **BLOCKED** Decide and document the production authentication posture. Current code is no-auth;
  older project documentation also says public beta access should be replaced before real use.
- **BLOCKED** Privacy copy must cover infrastructure/request logs even though the application does
  not persist quote-card content itself.
- **PASS** The local Dockerfile copies only the MCP server, adapter, application resource, canonical
  renderer, contract, and rasterization dependency.
- **PORTAL** Confirm rate limits, abuse monitoring, dependency-update process, incident contact,
  and retention/deletion statements.

## Release integrity

- **PASS** Local plugin manifest and canonical skill are `1.7.11`; local and deployed UI are v1.34.
- **PASS** The local plugin ZIP for 1.7.11 was rebuilt, archive-tested, and hashed.
- **PASS** The project suite passes when socket and headless-browser tests are allowed.
- **PASS** Remote resource `ui://quote-card-builder/preview/v1.34.html` is readable from the deployed MCP server.
- **PASS** Local v1.27 source packages have deterministic recorded SHA-256 hashes and clean archive
  listings.
- **PASS** The clean v1.34 source archive was built by Cloud Build and deployed as revision
  `quote-card-builder-mcp-00064-raf`; the image digest, 100% traffic split, health, MCP handshake,
  and resource descriptor are recorded in `submission/evidence.md`.
- **FIX** The worktree is detached and dirty; freeze the approved candidate in a clean, traceable
  commit before submission.
- **PASS** Deployment evidence for v1.34 is recorded after the corrective deploy.
- **PASS** The local v1.34 candidate retains v1.26 through v1.33 compatibility resources.
- **PASS** `pytest.ini` restricts default discovery to `tests/` and excludes `work/`.

## Final gate

Do not submit until every **BLOCKED** item is resolved, **Scan Tools** passes, the final UI is
visually checked in ChatGPT, and the exact frozen commit, package hashes, Cloud Run revision, image
digest, and reviewer test results are recorded together.
