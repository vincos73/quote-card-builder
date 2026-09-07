# Quote Card Builder submission pack

This folder prepares the OpenAI plugin submission while the remote MCP App remains in private
beta. It is documentation only: it does not submit, deploy, publish, install, or alter the
canonical Python renderer.

## Candidate under review

- Current candidate: plugin `1.7.12`, MCP App UI `v1.39`
- Deployed MCP App UI: `v1.38`
- Deployed revision: `quote-card-builder-mcp-00074-mod`, ready and receiving 100% of traffic
- Public MCP endpoint: `https://quote-card-builder-mcp-960066178304.europe-west8.run.app/mcp`
- Candidate UI resource: `ui://quote-card-builder/preview/v1.39.html`
- Authentication: none
- Persistence: none in the application runtime
- Canonical renderer: `scripts/render_quote_card.py`, reached through the thin MCP adapter

The local plugin package uses `.mcp.json` and stdio for development. The submission form must
instead receive the public Universal MCP URL above; a local marketplace entry or integration ID
is not a substitute for that URL.

## Contents

- `checklist.md`: readiness against the official submission sequence.
- `listing-draft.md`: reviewer-facing listing copy and unresolved listing fields.
- `reviewer-test-cases.md`: five positive and three negative reviewer-runnable cases.
- `evidence.md`: reproducible local and remote evidence for the current candidate.
- `blockers.md`: release blockers, review risks, and approval gates.

## Authority boundary

The Python renderer remains the single source of truth. The MCP server validates and transports
editor state, the HTML component edits that state and converts the returned SVG to a PNG in the
browser, and no second visual renderer is introduced by this pack.

Official references:

- [Submit your plugin](https://developers.openai.com/plugins/deploy/submission)
- [MCP server review requirements](https://developers.openai.com/plugins/deploy/app-review)
- [UI guidelines](https://developers.openai.com/plugins/concepts/ui-guidelines)
- [Security and privacy](https://developers.openai.com/plugins/guides/security-privacy)
