# Submission blockers and review risks

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
2. **Hosted interaction proof and legacy resources** — v1.34 is deployed and its live resource
   exposes the honest **Open PNG** flow. Repeat the final click-through in ChatGPT, then confirm
   whether v1.26 through v1.33 should remain as compatibility aliases before freezing the candidate.

## Not blockers in the current design

- The local `.mcp.json` uses stdio because it belongs to the downloadable plugin package; the
  submission portal should receive the public Universal MCP URL separately.
- `produce_quote_card` is read-only at the MCP/server level: it returns an in-memory artifact and
  does not publish, persist, or modify external data. A user-initiated browser download is not an
  external server-side write.
- Empty connection/resource/redirect CSP allowlists remain coherent with the self-contained UI;
  v1.34 delegates temporary file delivery to the optional ChatGPT host bridge rather than fetching
  an external application origin directly and describes the resulting open-in-browser behavior.

## Approval gate for the next implementation pass

The following are material candidate changes and should be approved before implementation:

- approve the v1.26-v1.33 compatibility window;
- rebuild the plugin and Cloud Run source packages after the frozen source commit;
- configure the deployed candidate challenge route with the future portal token;
- repeat hosted visual/accessibility capture against the deployed v1.34 resource.
