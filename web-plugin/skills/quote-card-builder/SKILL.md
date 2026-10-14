---
name: quote-card-builder
description: Create or refine quote cards in the hosted editor with native Nastri and Urban compositions, portable personal bases and brand assets. Use with an exact quote, readable text/source, or a saved base.
---

# Quote Card Builder — web MCP

Source candidate 1.9.0, editor v1.59. Check the connected editor's version before claiming these capabilities; the installed live service may still be older. Use the connected MCP tools. Preserve explicit text, attribution, palette, style and reuse choices.

At the first invocation, greet briefly in the user's language and continue the requested work. With no content or creation request, explain the supported inputs in chat. With an exact quote and creation intent, design and open one populated editor in the same turn. With longer supplied text, use a strong exact excerpt unless the user chose one already. With a URL and creation intent, read it through the host, select an exact quote and open the editor; the server does not read URLs. If only phrase discovery, comparison or explanation is requested, stay in chat. An explicit empty-editor request calls `quote_card_builder_open_workspace` with `{}`.

A name must be supplied by the user or established by the source; otherwise leave attribution empty. Omitted palette uses the neutral palette without claiming it is the user's brand. Do not infer a brand from a source or identity. Mark user-supplied words USER_SUPPLIED and source-checked exact words VERIFIED only after reading the source.

Nastri is the exploratory default for a new card without a chosen style. Preserve an explicit grammar, saved base, legacy style or restored draft. For Nastri read [the ribbon reference](references/ribbons-web-mcp.md); for Urban read [the Urban reference](references/urban-web-mcp.md). Design three different native scenes using the exact quote and palette. Pass explicit `style`, `visual_grammar`, `composition_candidates`, the recommended `composition` and `proposal_source: model` to `quote_card_builder_open_editor`. Reserve author space even when absent. Differences must involve geometry, rhythm and reading space, beyond color changes. Describe each direction briefly.

Default font sizes to automatic unless the user asks for exact sizes. Sparse bold, italic or highlight ranges can guide reading. Keep Unicode offsets faithful to the exact editor text, including newline and blank rows. Quote and author sizes are independent; size ranges are relative to the quote. Never shorten or rewrite words to fit. An explicit manual size remains fixed even if an advisory appears.

The editor offers demo scenes when no model scenes were supplied. They are deterministic examples, not authored proposals. **Create in this style** explicitly requests new compositions through the host chat when supported. It preserves the current card and asks the model to design new scenes; use the current snapshot and revision to update them. **Demo variations** remains a distinct deterministic action. Do not claim that demos were model-designed or that a failed host message started a model request.

Follow-up changes use `quote_card_builder_update_editor`, with current `base_snapshot`, `base_revision` and only requested `patch` fields. Do not reopen or reset the editor. Keep all unmentioned corrections. Text-only changes preserve style, palette, geometry, author and brand. When words change, clear obsolete ranges and default to EDITED/UNVERIFIED unless the new wording was verified. Whitespace-only changes preserve editorial status and remap ranges.

Uploaded font/logo files stay in the editor and project JSON. Model context contains `brand_kit_attached` and compact `brand_summary`, not file bytes. When the server returns `deferred_render: true`, the mounted editor applies the validated patch to its current assets and renders the preview. Do not substitute a font or claim that the server already rendered that deferred result. A fresh editor must restore its complete project to recover those assets.

Read [personal bases](references/personal-bases.md) for reuse. A base retains design and brand without quote, author, word ranges or evidence; a project retains the full card. Old web bases preserve their original card as a recoverable saved project during migration. **Reuse this card** retains the selected design; a new quote resets ranges and quote size. The optional author field determines attribution and may be cleared. The common JSON formats transfer between web and local editors; storage remains on the client/device without account synchronization.

Read [brand kits](references/brand-kits.md) for font/logo upload and portable assets. Palette values remain exact. The web can show or hide an uploaded logo, import/export the kit and include it in bases/projects. Font and logo identify the brand, independently from attribution.

The user chooses 4:5, 1:1 or 9:16. Preview, selected proposal and PNG share the exact numeric composition and current editor contents. Graphic advisories are descriptive, non-blocking and contain no correction controls. Invalid data, missing resources and PNG failures are technical errors. Remote delivery uses the returned HTTPS PNG as an image and download link. Use the headless fallback only after an actual host UI failure, with approval and matching current preview hash as required by that tool.
