# Submission blockers and review risks

> **Historical snapshot:** These blockers were recorded for the September 2026 submission review
> of package `1.7.16` and UI resource `v1.40`. They do not establish the state of candidate
> `1.8.10` or the live service. Consult the root `RELEASE-STATUS.md` for current
> source, publication, installation, and deployment state.

## P0 — resolve before submission

1. **Publisher and portal eligibility** — verify publisher identity, Apps Management write access,
   and a global-residency OpenAI project.
2. **Public legal and support surface** — provide approved product website, support, privacy, and
   terms URLs under an identity consistent with the listing.
3. **Domain verification** — obtain the portal token, deploy the implemented challenge route with
   `OPENAI_APPS_CHALLENGE_TOKEN`, and verify that it serves the exact value.
4. **Authentication and privacy posture** — choose whether the stateless app remains no-auth in
   production, reconcile that choice with older pilot documentation, and describe infrastructure
   logs and retention accurately.
5. **Production identity assets** — approve the publisher label, logo, availability countries, and
   release notes.
6. **Frozen candidate** — create a clean traceable source commit, rebuild packages, record new
   hashes, and preserve the verified historical deployment evidence against that commit.
7. **Portal review** — run Scan Tools and all eight reviewer cases against the frozen deployment.

## P1 — fix or make an explicit submission decision

1. **Visual and accessibility evidence** — capture final desktop/narrow screenshots and complete a
   hosted keyboard/screen-reader pass.
2. **Hosted interaction proof and legacy resources** — the historical local v1.40 candidate prefers
   `ui/download-file`, with PNG transfer through `ui/message` as a fallback. Verify the complete
   flow in ChatGPT after deployment. Preserve v1.26 through v1.39 aliases and compatible tool
   responses for already mounted older components. Recorded v1.38 deployment evidence is
   historical, not a verification of this candidate.

## Not blockers in the reviewed design

- The local `.mcp.json` uses stdio because it belongs to the downloadable plugin package; the
  submission portal should receive the public Universal MCP URL separately.
- The compatibility manifest `.codex-plugin/plugin.json` remains supported. Adopting the portable
  manifest layout is a separate packaging improvement, not a prerequisite for this local fix.
- `produce_quote_card` is read-only at the MCP/server level: it returns an in-memory artifact and
  does not publish, persist, or modify external data. A user-initiated browser download is not an
  external server-side write.
- Empty connection and resource CSP allowlists remain coherent with the self-contained UI. The
  redirect allowlist is intentionally limited to the observed ChatGPT temporary-file origin and
  is shared by the current resource and every compatibility alias.

## Distribution work remaining

The user authorized the local compatibility, server, skill, and checklist corrections. That work
does not publish a release or change the deployed service. Before distribution:

- read the official authentication guide and choose the production posture;
- rebuild the plugin and Cloud Run source packages from the frozen source commit;
- configure the deployed candidate challenge route once the portal token is available;
- repeat hosted visual/accessibility capture and reviewer cases against the exact deployed candidate.
