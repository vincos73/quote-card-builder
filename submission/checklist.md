# Submission checklist

> **Historical snapshot:** This checklist records the local review from 2026-09-20 for package
> `1.7.16` and UI resource `v1.40`. Every **PASS** below applies only to that reviewed snapshot;
> it is not evidence for candidate `1.8.10`, a current deployment, or an installed plugin. Use the
> root `RELEASE-STATUS.md` for the current distribution state once it is added.

Status legend for the 2026-09-20 review: **PASS** verified on that review snapshot; **PORTAL** had
to be verified in the OpenAI submission flow; **BLOCKED** required input or decision was missing;
**FIX** candidate work was recommended before submission; **HISTORICAL** evidence for an earlier
candidate only.

Local review: 2026-09-20. Package version: `1.7.16`. UI resource: `v1.40`.
This checklist distinguishes local source/tests from hosted behavior. No deployment, installation,
or public release was performed during this review. Earlier deployment records remain in
`submission/evidence.md`; they do not verify the current candidate or current remote state.

## Account and submission channel

- **PORTAL** Publisher identity is verified and matches the public listing identity.
- **PORTAL** The submitting account has Apps Management write access (`api.apps.write`).
- **PORTAL** The OpenAI project uses global data residency; an EU-residency project cannot submit
  an MCP server at the time this checklist was prepared.
- **PASS** The candidate is correctly treated as a plugin with an MCP server, not as a skills-only
  package.
- **HISTORICAL** A public Universal MCP URL is recorded in the deployment evidence. Recheck it
  against the frozen release candidate before submission.

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

- **HISTORICAL** HTTPS `/health` and Streamable HTTP initialization were verified for the earlier
  deployment. Repeat both against the final deployment and record its negotiated protocol.
- **PASS** Four tools have explicit input and structured output schemas.
- **PASS** MCP initialization reports the project version `1.7.16`; primary routing and
  headless approval requirements appear within the first 512 instruction characters.
- **PASS** Legacy editor calls retain `svg` and `svg_data_uri`; current UI updates opt into
  `compact_output: true` and receive SVG through metadata. The initial editor response retains
  legacy fields for cached components. Headless results have a separate compact schema.
- **PASS** Every tool declares `readOnlyHint=true`, `destructiveHint=false`, and
  `openWorldHint=false`; the operations validate/render in memory and do not change external
  state.
- **PASS** `quote_card_builder_open_editor` is model-visible and linked to the UI resource.
- **PASS** `quote_card_builder_headless` is also model-visible, without an attached UI. It requires
  reported UI unavailability; production requires explicit caller approval bound to the current
  preview hash. The approval flag is a caller declaration, not proof of human consent.
- **PASS** `preview_quote_card` and `produce_quote_card` are app-private and do not open duplicate
  components.
- **PASS** The UI resource is `text/html;profile=mcp-app`, declares its domain, keeps connection and
  resource CSP allowlists empty, and limits redirects to the observed ChatGPT temporary-file origin.
- **PASS** The local candidate has a configurable `/.well-known/openai-apps-challenge` route and
  returns `404` while no token is configured.
- **BLOCKED** Domain verification cannot be completed until the portal issues its token and the
  route is deployed with `OPENAI_APPS_CHALLENGE_TOKEN`.
- **PORTAL** Run **Scan Tools** against the final frozen server and resolve all reported issues.

## UI and behavior

- **PASS** The local resource exposes standard MCP Apps native download (`ui/download-file`) and
  PNG chat transfer (`ui/message`), plus the older ChatGPT-specific delivery path as a fallback.
- **PASS** The inline editor has two main actions: **Update preview** and **Generate PNG**, with
  clear supporting labels and distinct primary/secondary hierarchy.
- **PASS** Quote, attribution, neutral/custom palette, direction, 4:5/1:1 format, authored line
  breaks, formatting ranges, scale, position, and motif are represented in editor state.
- **PASS** Generate revalidates through the canonical renderer and prepares a PNG in the browser.
- **PASS** The local UI uses host theme variables and native fonts, without a branded masthead.
  Draft persistence, model context updates, stale export protection, and bounded bridge calls
  have local regression coverage.
- **PASS** A local browser harness verified light/dark themes, a 360px viewport, draft restoration,
  and PNG bytes accepted by a simulated host. This does not verify ChatGPT or saving to disk.
- **HISTORICAL** Earlier hosted tests and v1.38 delivery/resource evidence remain available in
  `submission/evidence.md`. They are not proof of the v1.40 user-visible flow.
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
- **FIX** Read the official [authentication guide](https://developers.openai.com/plugins/build/auth)
  at the distribution step before deciding the production posture.
- **BLOCKED** Privacy copy must cover infrastructure/request logs even though the application does
  not persist quote-card content itself.
- **PASS** The Dockerfile includes the server, renderer dependencies, and bundled UI assets;
  container-contract tests check the required runtime files.
- **PORTAL** Confirm rate limits, abuse monitoring, dependency-update process, incident contact,
  and retention/deletion statements.

## Release integrity

- **PASS** At review time, the local plugin manifest, project metadata, and canonical skill
  identified `1.7.16`; the local UI resource was `v1.40`.
- **PASS** The existing `.codex-plugin/plugin.json` and `.mcp.json` layout remains officially
  supported. Migration to portable root `plugin.json`/`mcp.json` is optional for this package;
  it requires updating the builder and validators together, not renaming files.
- **PASS** On 2026-09-20 the final local suite ran **281 tests, zero skips, all passed** using
  `python -m unittest discover -s tests -v` in the isolated MCP-enabled Python 3.14 environment.
  Coverage includes stdio/HTTP protocol calls and launching the packaged MCP server. The official
  skill validator and `git diff --check` also pass. These are not a Docker image build or hosted
  ChatGPT certification.
- **PASS** Skill routing distinguishes MCP, standalone local editing, observed UI failure, and
  explicit user choices. The shared standalone-capable skill does not require a remote MCP
  dependency; the downloadable plugin bundles its stdio configuration.
- **FIX** Freeze the final source in a clean, traceable commit, rebuild packages, archive-test
  them, and record hashes for those exact artifacts before release publication.
- **HISTORICAL** The v1.38 source archive was built by Cloud Build and deployed as revision
  `quote-card-builder-mcp-00074-mod`; the image digest, 100% traffic split, health, MCP handshake,
  and resource descriptor are recorded in `submission/evidence.md`. Historical ZIP versions and
  hashes do not establish integrity of the current worktree.
- **PASS** The local candidate retains v1.26 through v1.39 compatibility resource aliases.
  Aliases serve updated HTML when fetched; already mounted or cached components additionally
  require a backward-compatible tool response contract.
- **PASS** `pytest.ini` restricts default discovery to `tests/` and excludes `work/`.

## Final gate

Do not submit until every **BLOCKED** item is resolved, **Scan Tools** passes, the final UI is
visually checked in ChatGPT, and the exact frozen commit, package hashes, Cloud Run revision, image
digest, and reviewer test results are recorded together.
