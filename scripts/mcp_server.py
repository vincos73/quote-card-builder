#!/usr/bin/env python3
"""MCP server for Quote Card Builder's preview and SVG production slice."""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import os
import struct
import sys
import tempfile
import tomllib
import zlib
from pathlib import Path
from typing import Annotated, Literal

try:
    from mcp.server import MCPServer
    from mcp.server.apps import APP_MIME_TYPE, Apps, ResourceCsp
    from mcp.server.mcpserver.resources import TextResource
    from mcp.server.transport_security import TransportSecuritySettings
    from mcp_types import (
        CallToolResult,
        EmbeddedResource,
        ImageContent,
        TextContent,
        TextResourceContents,
        ToolAnnotations,
    )
    from pydantic import BaseModel, Field, model_serializer, model_validator
    from openai_mcp_extensions import (
        OpenAIExtensions,
        OpenAIGlobalEntrypoint,
        OpenAIThreadEntrypoint,
        OpenAIUiResourceMetadata,
        OpenAIUiToolMetadata,
    )
    from starlette.requests import Request
    from starlette.concurrency import run_in_threadpool
    from starlette.responses import JSONResponse, PlainTextResponse, Response
except ImportError as exc:  # pragma: no cover - exercised by the launcher, not the core tests
    raise SystemExit(
        "MCP SDK missing: create a virtual environment and install requirements-mcp.txt before starting the server."
    ) from exc

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from mcp_quote_card import preview_quote_card as render_preview
import render_quote_card as canonical_renderer
from remote_png_store import (
    RemotePngBusy,
    RemotePngNotFound,
    RemotePngRateLimited,
    configured_public_origin,
    get_remote_png_store,
    remote_delivery_configured,
)
from mcp_app import (
    QUOTE_CARD_DOWNLOAD_REDIRECT_DOMAINS,
    QUOTE_CARD_LEGACY_PREVIEW_RESOURCES,
    QUOTE_CARD_PREVIEW_DOMAIN,
    QUOTE_CARD_PREVIEW_RESOURCE,
    QUOTE_CARD_WORKSPACE_RESOURCE,
    quote_card_preview_html,
)


def _project_version() -> str:
    """Read the bundled project's canonical version in root, Docker, or plugin layouts."""
    manifest = SCRIPT_DIR.parent / "pyproject.toml"
    with manifest.open("rb") as handle:
        project = tomllib.load(handle).get("project", {})
    version = project.get("version") if isinstance(project, dict) else None
    if not isinstance(version, str) or not version:
        raise RuntimeError(f"Missing canonical project version in {manifest}")
    return version


MCP_SERVER_VERSION = _project_version()
LOCAL_FILE_DELIVERY = False  # Enabled explicitly by the local stdio launcher only.
MAX_PNG_BYTES = 8 * 1024 * 1024
MCP_HTTP_MAX_REQUEST_BYTES = 12 * 1024 * 1024


class StyleRange(BaseModel):
    start: int = Field(ge=0, description="Starting Unicode offset, inclusive.")
    end: int = Field(gt=0, description="Ending Unicode offset, exclusive.")
    type: Literal["bold", "italic", "underline", "highlight", "accent", "outline", "size"]
    scale: float | None = Field(default=None, ge=.5, le=2.5, description="Required for size: relative scale 0.5–2.5.")

    @model_validator(mode="before")
    @classmethod
    def validate_size(cls, value):
        if isinstance(value, dict):
            scale = value.get("scale")
            if value.get("type") == "size" and (scale is None or isinstance(scale, bool)):
                raise ValueError("Size ranges require a numeric scale.")
            if value.get("type") != "size" and scale is not None:
                raise ValueError("Only size ranges may contain scale.")
        return value

    @model_serializer
    def serialize_range(self):
        result = {"start": self.start, "end": self.end, "type": self.type}
        if self.type == "size":
            result["scale"] = self.scale
        return result


class GrammarFields(BaseModel):
    """Canonical, portable scene state shared by tools and the editor."""

    brand_kit: dict[str, object] | None = Field(default=None, description="Portable qcb-brand-kit v1, with embedded user-provided font and logo assets. Preserve through edits; no server brand archive.")
    logo_mode: Literal["auto", "hidden"] = "auto"
    visual_grammar: Literal["ribbons", "urban"] | None = Field(default=None, description="Native editable visual grammar: ribbons (Nastri) or urban (print poster); omit for legacy styles.")
    composition: dict[str, object] | None = Field(default=None, description=(
        "Native ribbon scene: version=1, id, optional name; quote_box, author_box, logo_box each {x,y,width,height} within 0..1; "
        "background_role,text_role,highlight_role from primary/accent/background/text; ribbons [{id,color_role,width_ratio:0.015..0.3,points:[[x,y],...]}] "
        "with 1+3*n points (4..37), coordinates -0.5..1.5, interpreted as start then cubic controls/end; crossings [{over,under,segment,t:0..1}]. "
        "For urban, scene grammar='urban', blocks (rect/polygon), strips and texture contain bounded numeric print-poster geometry. "
        "Optional artwork_id='urban-xerox-lime-v1' selects the bundled Xerox/lime image with editable native text; no image URLs, paths or base64 in a scene. "
        "Compose around quote, optional author and logo. Preserve user-authored scenes exactly."
    ))
    composition_candidates: list[dict[str, object]] = Field(default_factory=list, max_length=3, description="Up to three distinct native scenes for selection; empty means no gallery. Model scenes require proposal_source=model.")
    proposal_source: Literal["model", "demo"] | None = None
    quote_font_size: float | None = Field(default=None, ge=8, le=720, description="Absolute quote size in 1440px canvas pixels; omitted means automatic fit. Explicit values are preserved.")
    author_font_size: float | None = Field(default=None, ge=8, le=720, description="Independent attribution size in canvas pixels.")


class PaletteColors(BaseModel):
    primary: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$", description="Primary color #RRGGBB.")
    accent: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$", description="Accent color #RRGGBB.")
    background: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$", description="Background color #RRGGBB.")
    text: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$", description="Text and metadata color #RRGGBB.")


class PaletteInput(BaseModel):
    name: str = Field(min_length=1, max_length=80, description="User-provided palette name.")
    colors: PaletteColors


class PreviewQuoteCardInput(GrammarFields):
    text: str = Field(min_length=1, max_length=600, description="Quote card text.")
    format: Literal["4x5", "1x1", "9x16"] = Field(default="4x5", description="Card format: portrait 4x5, square 1x1, or story 9x16.")
    attribution: str = Field(default="", max_length=160, description="Optional visible attribution.")
    transformation: Literal["VERBATIM", "EDITED", "PARAPHRASE", "AI_GENERATED"] = "VERBATIM"
    evidence_status: Literal["VERIFIED", "USER_SUPPLIED", "UNVERIFIED", "CONFLICT"] = "USER_SUPPLIED"
    direction: Literal["editorial", "statement", "contextual"] = "editorial"
    graphic_mode: Literal["auto", "hidden"] = Field(default="auto", description="Automatic or hidden graphic motif.")
    graphic_variant: str = Field(default="default", description="Motif variant compatible with the selected direction.")
    graphic_seed: int = Field(default=0, ge=0, le=999999, description="Deterministic motif variation.")
    text_scale: float = Field(default=1.0, ge=0.8, le=1.0, description="Text scale relative to the available maximum.")
    vertical_position: Literal["upper", "center", "lower"] = Field(default="center", description="Vertical position of the text block.")
    palette: PaletteInput | None = Field(
        default=None,
        description="Palette explicitly selected by the user; when omitted, use the neutral profile.",
    )
    lines: list[str] | None = Field(default=None, description="Explicit line breaks with no fixed limit; when omitted, use one line.")
    styles: list[StyleRange] | None = Field(default=None, max_length=64)
    alt_text: str = Field(default="", max_length=400, description="Optional replacement for the automatic alt text.")
    output_image: bool = Field(default=False, description="Compatibility option: when true, include ImageContent in a preview response.")
    presentation: dict[str, object] | None = Field(default=None, description="Optional native presentation mapping; canonical output uses the flattened scene fields.")
    reuse_composition: dict[str, object] | None = Field(default=None, description="Saved scene for deterministic style variations when no new scene/candidates are supplied; output is labelled demo.")


class EditorState(GrammarFields):
    """Authoritative editor snapshot echoed by every render tool result."""

    text: str
    format: Literal["4x5", "1x1", "9x16"] = "4x5"
    attribution: str
    profile_mode: Literal["neutral", "custom"]
    transformation: Literal["VERBATIM", "EDITED", "PARAPHRASE", "AI_GENERATED"]
    evidence_status: Literal["VERIFIED", "USER_SUPPLIED", "UNVERIFIED", "CONFLICT"]
    direction: Literal["editorial", "statement", "contextual"]
    graphic_mode: Literal["auto", "hidden"]
    graphic_variant: str
    graphic_seed: int
    text_scale: float
    vertical_position: Literal["upper", "center", "lower"]
    palette: PaletteInput | None = None
    lines: list[str] | None = None
    styles: list[StyleRange] = Field(default_factory=list)
    alt_text: str = ""
    brand_kit_attached: bool = False
    brand_summary: dict[str, object] | None = None


class ValidationIssue(BaseModel):
    path: str
    code: str
    message: str
    severity: Literal["advisory"] | None = None


class RenderedQuoteCard(GrammarFields):
    """Internal result from the canonical renderer, including SVG bytes."""

    valid: bool
    rendered: bool
    profile: str
    direction: Literal["editorial", "statement", "contextual"]
    graphic_mode: Literal["auto", "hidden"] = "auto"
    graphic_variant: str = "default"
    text_scale: float = 1.0
    vertical_position: Literal["upper", "center", "lower"] = "center"
    format: Literal["4x5", "1x1", "9x16"]
    width: int
    height: int
    svg: str | None
    svg_data_uri: str | None
    svg_sha256: str | None = None
    palette: dict[str, str]
    alt_text: str
    warnings: list[ValidationIssue]
    errors: list[ValidationIssue]
    editorial_responsibility: Literal["caller"]
    declaration: dict[str, object] | None = None
    editor_state: EditorState | None = None
    ribbon_layout: dict[str, object] | None = None
    composition_previews: list[dict[str, object]] = Field(default_factory=list)


class CompactQuoteCardOutput(GrammarFields):
    """Compact structured output shared with the model and the MCP App.

    The default wire payload preserves legacy ``svg`` and ``svg_data_uri`` fields
    for existing consumers. New UI calls opt into the compact envelope and
    receive the SVG in ``CallToolResult._meta.quoteCard.svg``.
    """

    valid: bool
    rendered: bool
    profile: str
    direction: Literal["editorial", "statement", "contextual"]
    graphic_mode: Literal["auto", "hidden"] = "auto"
    graphic_variant: str = "default"
    text_scale: float = 1.0
    vertical_position: Literal["upper", "center", "lower"] = "center"
    format: Literal["4x5", "1x1", "9x16"]
    width: int
    height: int
    svg_sha256: str | None = None
    palette: dict[str, str]
    alt_text: str
    warnings: list[ValidationIssue]
    errors: list[ValidationIssue]
    editorial_responsibility: Literal["caller"]
    declaration: dict[str, object] | None = None
    editor_state: EditorState | None = None
    ribbon_layout: dict[str, object] | None = None
    composition_previews: list[dict[str, object]] = Field(default_factory=list)


class PreviewQuoteCardOutput(CompactQuoteCardOutput):
    """Preview output with an optional legacy structured SVG field."""

    svg: str | None = None
    svg_data_uri: str | None = None


class ProduceQuoteCardOutput(PreviewQuoteCardOutput):
    produced: bool
    filename: str | None
    mime_type: Literal["image/svg+xml"] = "image/svg+xml"
    local_file_delivery: bool = False
    remote_file_delivery: bool = False


class SavedPngOutput(BaseModel):
    path: str
    filename: str
    mime_type: Literal["image/png"] = "image/png"
    sha256: str


class PublishedPngOutput(BaseModel):
    url: str
    filename: str
    mime_type: Literal["image/png"] = "image/png"
    sha256: str
    expires_at: str


class HeadlessQuoteCardOutput(CompactQuoteCardOutput):
    """Compact output for the explicit no-UI fallback."""

    produced: bool
    filename: str | None
    mime_type: Literal["image/svg+xml"] = "image/svg+xml"
    action: Literal["preview", "produce"]
    ui_unavailable: bool
    approval_required: bool
    approval_received: bool
    resource_uri: str | None = None


class WorkspaceOpenOutput(BaseModel):
    """Explicit initial state returned by the global workspace entrypoint."""

    mode: Literal["workspace"] = "workspace"
    workspace_state: Literal["empty"] = "empty"
    rendered: Literal[False] = False
    editor_state: None = None


apps = Apps()
openai_extensions = OpenAIExtensions()
_REMOTE_EXPORT_ORIGIN = configured_public_origin()
_REMOTE_CSP_DOMAINS = [_REMOTE_EXPORT_ORIGIN] if _REMOTE_EXPORT_ORIGIN else []
_EDITOR_CSP = ResourceCsp(
    connect_domains=_REMOTE_CSP_DOMAINS,
    resource_domains=_REMOTE_CSP_DOMAINS,
    frame_domains=[],
    base_uri_domains=[],
)


def _add_preview_resource(uri: str, *, legacy: bool = False, workspace: bool = False) -> None:
    """Register the shared editor with entrypoint-specific display metadata."""
    if workspace:
        name = "quote-card-workspace-ui"
        title = "Quote Card Builder workspace"
        description = "Fullscreen workspace that opens without fabricating a quote card."
        display_modes = OpenAIUiResourceMetadata(
            available_display_modes=["fullscreen"],
            preferred_display_mode="fullscreen",
        )
        prefers_border = False
    else:
        name = "quote-card-preview-compatibility" if legacy else "quote-card-preview-ui"
        title = "Quote Card Builder preview (compatibility alias)" if legacy else "Quote Card Builder preview"
        description = (
            "Compatibility alias that serves the current editor version."
            if legacy
            else "Editor for viewing and updating a validated quote card in a content tab."
        )
        display_modes = OpenAIUiResourceMetadata(
            available_display_modes=["fullscreen"] if not legacy else ["inline"],
            preferred_display_mode="fullscreen" if not legacy else "inline",
        )
        prefers_border = True

    apps.add_resource(
        TextResource(
            uri=uri,
            name=name,
            title=title,
            description=description,
            mime_type=APP_MIME_TYPE,
            text=quote_card_preview_html(workspace=workspace),
            meta={
                "ui": {
                    "csp": _EDITOR_CSP.model_dump(by_alias=True, exclude_none=True),
                    "domain": QUOTE_CARD_PREVIEW_DOMAIN,
                    "prefersBorder": prefers_border,
                },
                "openai/ui": display_modes.model_dump(by_alias=True, exclude_none=True),
                "openai/widgetCSP": {
                    "connect_domains": list(_REMOTE_CSP_DOMAINS),
                    "resource_domains": list(_REMOTE_CSP_DOMAINS),
                    "redirect_domains": [
                        *QUOTE_CARD_DOWNLOAD_REDIRECT_DOMAINS,
                        *_REMOTE_CSP_DOMAINS,
                    ],
                },
            },
        )
    )


_add_preview_resource(QUOTE_CARD_PREVIEW_RESOURCE)
for _legacy_preview_uri in QUOTE_CARD_LEGACY_PREVIEW_RESOURCES:
    _add_preview_resource(_legacy_preview_uri, legacy=True)
_add_preview_resource("ui://quote-card-builder/workspace/v1.58.html", legacy=True, workspace=True)
_add_preview_resource(QUOTE_CARD_WORKSPACE_RESOURCE, workspace=True)


@apps.tool(
    resource_uri=QUOTE_CARD_WORKSPACE_RESOURCE,
    visibility=["app", "model"],
    name="quote_card_builder_open_workspace",
    title="Quote Card Builder",
    description=(
        "Open a Quote Card Builder workspace in a content tab. Use when the user selects the "
        "plugin or asks to test it without providing a quote. It accepts no inputs and does not "
        "render or invent user content. The v1.53 UI may show an editable four-line demo with "
        "bold, italic, and highlighted text; v1.54 defaults absent attribution to none so the user can view text "
        "without being prompted. Preserve explicit named attribution; an intentional named choice with blank text remains incomplete. "
        "Editing the demo retains none attribution. The user supplies the quote and choices in the editor."
    ),
    annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False),
    meta={
        "openai/ui": OpenAIUiToolMetadata(
            entrypoints=[OpenAIGlobalEntrypoint(), OpenAIThreadEntrypoint()],
        ).model_dump(by_alias=True, exclude_none=True),
        "openai/toolInvocation/invoking": "Opening Quote Card Builder…",
        "openai/toolInvocation/invoked": "Quote Card Builder workspace ready.",
    },
    structured_output=True,
)
def quote_card_builder_open_workspace() -> WorkspaceOpenOutput:
    """Open a blank workspace without invoking the renderer."""
    output = WorkspaceOpenOutput()
    return CallToolResult(
        content=[
            TextContent(
                type="text",
                text="Quote Card Builder opened with an empty workspace. No card was rendered.",
            )
        ],
        structuredContent=output.model_dump(mode="json"),
        isError=False,
    )


@apps.tool(
    resource_uri=QUOTE_CARD_PREVIEW_RESOURCE,
    visibility=["model"],
    name="quote_card_builder_open_editor",
    title="Open Quote Card Builder",
    description=(
        "Use this for a clear request to create or proceed with a quote card, including a supplied URL. "
        "For a URL, the host/model reads the source, selects a strong exact quote, and opens the editor once with that quote; this server does not fetch URLs. "
        "For an initial medium or long quote, optimize for a strong mobile poster: use 6–9 short, semantically balanced lines for about 20–40 words, adapting line count to the quote. Aim for roughly 12–20 characters per line and keep most lines within 22 characters as a soft guide; never strand an article, conjunction, preposition, or verb on its own line. Let the quote occupy about 45–60% of the card height without a large empty center. At a 375px viewport, aim for readable quote type around 30–40px (about 115–155px on the 1440px canvas); break a long row semantically instead of shrinking the whole quote. Preserve every word, punctuation mark, negation, and qualifier for VERBATIM/VERIFIED text; never shorten verified wording automatically. "
        "Use 1–3 short emphasis ranges, usually only two style types from bold, italic, and highlight. Emphasize the central claim, not every word or a whole long line. Respect an explicit plain layout or user-supplied lines/styles, including an empty styles list; never rewrite an existing quote's user-authored layout unless asked. Style offsets are zero-based Unicode code-point indexes with an exclusive end, measured against text exactly as lines joined by newline. If text already contains newlines and lines is omitted, those rows are used. Keep short quotes visually strong without forcing extra lines or styles. Example layout for the supplied sentence: ‘L’IA aiuta / a chiarire i problemi / e a valutare / le opzioni; / il giudizio / e la responsabilità / restano alle persone.’ "
        "Default missing attribution to none and palette to neutral without asking. Preserve a named attribution only when supplied by the user or verified in the source. "
        "Ask only when the source cannot be read or the user's intent/content remains materially ambiguous. "
        "For a requested Nastri/ribbons or geometric Urban card, supply three genuinely different native composition_candidates with proposal_source='model', or preserve the chosen composition. "
        "For Urban Xerox/lime, reuse the registered artwork composition with proposal_source='demo'; do not replace it with geometric posters or invent three generated artworks. "
        "style='urban' without a scene opens the bundled Xerox/lime composition. Its image colors are fixed; quote, author, font and logo remain editable. "
        "The model chooses geometry and reading space for authored scenes. Inline size uses type='size' and scale 0.5–2.5. Visual warnings are advisory and preserve user choices. "
        "The user chooses style in the editor; use Blocks, Cutouts, Constellations, or Gradient only as an "
        "optional preselection volunteered by the user. Do not use image generation or a local "
        "filesystem. Do not ask for quote, attribution, or palette confirmation when the user said to proceed. Call this tool exactly once and do not "
        "call preview_quote_card or produce_quote_card first: the UI handles later updates and "
        "production. If the host explicitly reports that this UI cannot mount, use the separate "
        "quote_card_builder_headless fallback with ui_unavailable=true; it is the only approved "
        "path for a model-accessible SVG without the editor. The editor does not save, publish, "
        "or modify external data."
    ),
    annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False),
    meta={
        "openai/toolInvocation/invoking": "Opening Quote Card Builder…",
        "openai/toolInvocation/invoked": "Quote Card Builder ready.",
    },
    structured_output=True,
)
def quote_card_builder_open_editor(
    text: str = Field(
        min_length=1,
        max_length=600,
        title="Quote",
        description="Quote selected by the user or, for a clear proceed request from a readable source, selected by the model from that source. Preserve exact wording for VERBATIM.",
    ),
    lines: Annotated[list[str] | None, Field(
        title="Line breaks (optional)",
        description=(
            "Optional authored line breaks. For initial medium/long quotes, prefer 6–9 short semantic rows, usually 12–20 characters and generally no more than 22 as a soft guide; never strand a function word or verb. Preserve user-authored rows unless asked to change them, and do not force short quotes into extra rows. "
            "Rows must preserve the exact words and punctuation in text. The canonical editor text is exactly '\\n'.join(lines)."
        ),
    )] = None,
    styles: Annotated[list[StyleRange] | None, Field(
        max_length=64,
        title="Inline emphasis (optional)",
        description=(
            "Optional ranges on canonical text exactly as '\\n'.join(lines). If lines is omitted, use text; when text has newlines, "
            "canonicalize rows with splitlines() and join them with '\\n' before calculating offsets. "
            "Offsets are zero-based Unicode code-point indexes; start is inclusive and end exclusive. Use a few brief ranges, "
            "usually only bold, italic, and/or highlight; preserve user-specified styles. An empty list explicitly means no styles."
        ),
    )] = None,
    attribution: str = Field(
        max_length=160,
        title="Visible attribution",
        description="Use a supplied or source-verified name; otherwise leave blank (none). Do not ask for confirmation. An explicit user choice requiring a name but left blank remains incomplete.",
        default="",
    ),
    profile_mode: Literal["neutral", "custom"] = Field(
        default="neutral",
        title="Palette profile",
        description="Defaults to the neutral palette. Use custom only when the user supplied or explicitly chose custom colors.",
    ),
    style: Annotated[Literal["blocks", "cutouts", "constellations", "gradient", "ribbons", "urban"], Field(
        title="Style preselection (optional)",
        description=(
            "Optional preselection volunteered by the user. The user can choose Blocks, Cutouts, "
            "Constellations, Gradient, Nastri (ribbons), or Urban (urban) in the editor; Urban defaults to Xerox/lime unless an explicit geometric composition is provided. Defaults to Blocks."
        ),
    )] = "blocks",
    format: Annotated[Literal["4x5", "1x1", "9x16"], Field(title="Initial format", description="Optional initial format: 4x5, 1x1, or 9x16.")] = "4x5",
    palette: Annotated[PaletteInput | None, Field(title="Custom palette colors", description="Required only when a custom palette was supplied or explicitly chosen.")] = None,
    transformation: Literal["VERBATIM", "EDITED", "PARAPHRASE", "AI_GENERATED"] = Field(default="VERBATIM", description="How the card text relates to its source."),
    evidence_status: Literal["VERIFIED", "USER_SUPPLIED", "UNVERIFIED", "CONFLICT"] = Field(default="USER_SUPPLIED", description="Use VERIFIED only when exact wording is checked against an accessible source."),
    visual_grammar: Literal["ribbons", "urban"] | None = None,
    composition: Annotated[dict[str, object] | None, Field(description=GrammarFields.model_fields["composition"].description)] = None,
    composition_candidates: Annotated[list[dict[str, object]] | None, Field(max_length=3, description=GrammarFields.model_fields["composition_candidates"].description)] = None,
    proposal_source: Literal["model", "demo"] | None = None,
    quote_font_size: Annotated[float | None, Field(ge=8, le=720)] = None,
    author_font_size: Annotated[float | None, Field(ge=8, le=720)] = None,
    presentation: dict[str, object] | None = None,
    reuse_composition: dict[str, object] | None = None,
    brand_kit: dict[str, object] | None = None,
    logo_mode: Literal["auto", "hidden"] = "auto",
) -> PreviewQuoteCardOutput:
    """Render the initial snapshot once; the widget handles later data calls."""
    if brand_kit is not None and palette is None:
        from portable_brand import normalize_brand_kit
        kit = normalize_brand_kit(brand_kit)
        palette = PaletteInput(name=kit["name"], colors=kit["colors"])
        profile_mode = "custom"
    if profile_mode == "custom" and palette is None:
        raise ValueError(
            "A custom palette requires a name and primary, accent, background, and text colors."
        )
    if lines is not None:
        if not lines or canonical_renderer.normalize_spaces(" ".join(lines)) != canonical_renderer.normalize_spaces(text):
            raise ValueError("Line breaks must preserve the quote's exact words and punctuation; only whitespace may differ.")
        text = "\n".join(lines)
    elif "\n" in text or "\r" in text:
        lines = text.splitlines()
        text = "\n".join(lines)
    style_map = {
        "blocks": ("editorial", "cover"),
        "cutouts": ("editorial", "cutouts"),
        "constellations": ("contextual", "constellations"),
        "gradient": ("editorial", "gradient"),
        "ribbons": ("editorial", "default"),
        "urban": ("editorial", "default"),
    }
    direction, graphic_variant = style_map[style]
    request = PreviewQuoteCardInput(
        text=text,
        format=format,
        attribution=attribution,
        transformation=transformation,
        evidence_status=evidence_status,
        direction=direction,
        graphic_mode="auto",
        graphic_variant=graphic_variant,
        text_scale=1.0,
        vertical_position="center",
        palette=palette.model_dump(mode="json") if profile_mode == "custom" and palette else None,
        lines=lines,
        styles=styles,
        alt_text="",
        output_image=False,
        visual_grammar=style if style in {"ribbons", "urban"} else visual_grammar,
        composition=composition,
        composition_candidates=composition_candidates or [],
        proposal_source=proposal_source,
        quote_font_size=quote_font_size,
        author_font_size=author_font_size,
        presentation=presentation,
        reuse_composition=reuse_composition,
        brand_kit=brand_kit,
        logo_mode=logo_mode,
    )
    result = _render_request(request, profile_mode)
    # Keep legacy styles readable by cached clients. Native Nastri SVGs embed
    # fonts and belong only in UI metadata, alongside their gallery proofs.
    structured = _wire_payload(_compact_output(result), legacy_svg=result.visual_grammar not in {"ribbons", "urban"})
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(_summary(result), ensure_ascii=False, indent=2))],
        structuredContent=structured,
        _meta=_svg_meta(result),
        isError=not result.valid or not result.rendered,
    )


class EditorPatch(GrammarFields):
    text: str | None = Field(default=None, min_length=1, max_length=600)
    attribution: str | None = Field(default=None, max_length=160)
    transformation: Literal["VERBATIM", "EDITED", "PARAPHRASE", "AI_GENERATED"] | None = None
    evidence_status: Literal["VERIFIED", "USER_SUPPLIED", "UNVERIFIED", "CONFLICT"] | None = None
    format: Literal["4x5", "1x1", "9x16"] | None = None
    profile_mode: Literal["neutral", "custom"] | None = None
    palette: PaletteInput | None = None
    direction: Literal["editorial", "statement", "contextual"] | None = None
    graphic_mode: Literal["auto", "hidden"] | None = None
    graphic_variant: str | None = None
    graphic_seed: int | None = Field(default=None, ge=0, le=999999)
    text_scale: float | None = Field(default=None, ge=0.8, le=1.0)
    vertical_position: Literal["upper", "center", "lower"] | None = None
    lines: list[str] | None = None
    styles: list[StyleRange] | None = Field(default=None, max_length=64)
    alt_text: str | None = Field(default=None, max_length=400)
    presentation: dict[str, object] | None = None
    reuse_composition: dict[str, object] | None = None


@apps.tool(
    resource_uri=QUOTE_CARD_PREVIEW_RESOURCE,
    visibility=["app", "model"],
    name="quote_card_builder_update_editor",
    title="Update Quote Card Builder",
    description=(
        "Use only when the user clearly asks in chat to change the already-open card. "
        "Include the complete current editor snapshot from model context as base_snapshot, echo editor_revision as base_revision, and include only explicitly requested changed fields in patch. "
        "The server validates the merged draft; when the current brand assets stay in the editor, the editor renders it after applying the patch. The widget applies the patch only when its current revision and base snapshot match; stale updates are rejected. A newly mounted widget can initialize from the returned merged editor state. "
        "Never reopen or reset the editor for a follow-up change. Unspecified attribution, evidence status, palette, style, format, and other choices remain untouched. Include palette/style/format fields only when explicitly requested. When text changes, default transformation to EDITED and evidence status to UNVERIFIED unless the new wording has been checked and those fields are explicitly supplied."
    ),
    annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False),
    meta={
        "openai/toolInvocation/invoking": "Updating quote card…",
        "openai/toolInvocation/invoked": "Quote card update received.",
    },
    structured_output=True,
)
def quote_card_builder_update_editor(
    base_revision: int = Field(ge=0, description="Current editor_revision from the mounted widget's model context."),
    base_snapshot: EditorState = Field(description="Complete current editor snapshot from model context."),
    patch: EditorPatch = Field(description="Only the fields explicitly changed by the user."),
) -> CallToolResult:
    """Merge and render a revision-checked patch, then deliver it through standard MCP Apps tool-input."""
    changes = patch.model_dump(exclude_unset=True)
    if changes.get("presentation") is not None:
        for key in GrammarFields.model_fields:
            if key in changes["presentation"] and key not in changes:
                changes[key] = changes["presentation"][key]
        changes.pop("presentation")
    if not changes:
        raise ValueError("The update patch must contain at least one changed field.")
    merged = base_snapshot.model_dump(mode="python")
    merged.update(changes)

    def remap_styles(new_text: str) -> list[dict[str, object]]:
        remapped: list[dict[str, object]] = []
        for style in base_snapshot.styles:
            selected = base_snapshot.text[style.start:style.end]
            if not selected:
                continue
            first = new_text.find(selected)
            if first >= 0 and new_text.find(selected, first + 1) < 0:
                remapped.append({**style.model_dump(), "start": first, "end": first + len(selected)})
        return remapped

    if "text" in changes and changes["text"] != base_snapshot.text:
        new_text = changes["text"]
        merged["lines"] = changes.get("lines")
        merged["styles"] = changes.get("styles", remap_styles(new_text))
        if "transformation" not in changes:
            merged["transformation"] = "EDITED"
            changes["transformation"] = "EDITED"
        if "evidence_status" not in changes:
            merged["evidence_status"] = "UNVERIFIED"
            changes["evidence_status"] = "UNVERIFIED"
    elif "lines" in changes and changes["lines"] is not None:
        # Line breaks are part of the editable quote text. Keep the canonical
        # text, editor snapshot, and renderer input in sync for line-only edits.
        new_text = "\n".join(changes["lines"])
        if " ".join(new_text.split()) != " ".join(base_snapshot.text.split()):
            raise ValueError("A lines-only update may change line breaks and whitespace, but not quote words; submit a text patch for wording changes.")
        merged["text"] = new_text
        changes["text"] = new_text
        if "styles" not in changes:
            styles = remap_styles(new_text)
            merged["styles"] = styles
            changes["styles"] = styles
    if merged.get("profile_mode") == "neutral" and "profile_mode" in changes and "palette" not in changes:
        merged["palette"] = None
        changes["palette"] = None
    if merged.get("profile_mode") == "custom" and merged.get("palette") is None:
        raise ValueError("A custom profile requires its palette colors.")
    state = EditorState.model_validate(merged)
    if base_snapshot.brand_kit_attached and state.brand_kit is None and "brand_kit" not in changes:
        # Uploaded binaries belong to the live editor, not the model context.
        # The UI checks the revision, applies this patch to its full draft and
        # renders it with its local assets. Do not render a substitute font.
        checked = PreviewQuoteCardInput.model_validate(state.model_dump())
        if checked.composition is not None:
            from visual_grammars import normalize_grammar_presentation
            normalize_grammar_presentation({key: getattr(checked, key) for key in ("visual_grammar", "composition", "quote_font_size", "author_font_size") if getattr(checked, key) is not None})
        return CallToolResult(
            content=[TextContent(type="text", text="Changes validated. The open editor applies them to its current brand assets and renders the preview.")],
            structuredContent={"valid": True, "rendered": False, "deferred_render": True, "update": True,
                               "base_revision": base_revision, "base_snapshot": base_snapshot.model_dump(mode="json", exclude={"brand_kit"}),
                               "patch": changes, "editor_state": state.model_dump(mode="json", exclude={"brand_kit"}),
                               "editor_revision": base_revision + 1},
            isError=False,
        )
    request = PreviewQuoteCardInput(
        text=state.text,
        format=state.format,
        attribution=state.attribution,
        transformation=state.transformation,
        evidence_status=state.evidence_status,
        direction=state.direction,
        graphic_mode=state.graphic_mode,
        graphic_variant=state.graphic_variant,
        graphic_seed=state.graphic_seed,
        text_scale=state.text_scale,
        vertical_position=state.vertical_position,
        palette=state.palette,
        lines=state.lines,
        styles=state.styles,
        alt_text=state.alt_text,
        **{key: getattr(state, key) for key in GrammarFields.model_fields},
        reuse_composition=changes.get("reuse_composition"),
    )
    rendered = _render_request(request, state.profile_mode)
    compact = _wire_payload(_compact_output(rendered), legacy_svg=False)
    compact.update({
        "update": True,
        "base_revision": base_revision,
        "base_snapshot": base_snapshot.model_dump(mode="json"),
        "patch": changes,
        "editor_state": rendered.editor_state.model_dump(mode="json"),
        "editor_revision": base_revision + 1,
    })
    return CallToolResult(
        content=[TextContent(type="text", text="Quote Card Builder rendered the requested editor update.")],
        structuredContent=compact,
        _meta=_svg_meta(rendered),
        isError=not rendered.valid or not rendered.rendered,
    )


mcp = MCPServer(
    name="quote-card-builder",
    title="Quote Card Builder",
    version=MCP_SERVER_VERSION,
    description="Canonical quote-card renderer with a fullscreen MCP Apps editor.",
    instructions=(
        "Use two entry paths. The global sidebar or a model call opens quote_card_builder_open_workspace with {}; "
        "when a user selects this plugin without a quote, open its fullscreen workspace immediately. "
        "The server response is empty and does not create quote content; UI v1.53 may offer an editable, clearly "
        "identified four-line demo with bold, italic, and highlighted text. In v1.54, default absent attribution to none "
        "for new workspaces, New Card, inputs without attribution, and legacy drafts with blank attribution. Preserve explicit named attribution; "
        "an intentional named choice with blank text remains incomplete and visible. Never present demo text or attribution as user-provided. "
        "Editing the demo retains none attribution; typing starts the preview. The server open call itself does not produce a card; the UI may render its editable demo as a preview. "
        "When a user clearly asks to proceed from a readable URL, use the host's browsing ability to read it, choose one strong exact quote, and call quote_card_builder_open_editor once with that quote. The server does not fetch URLs. For clear create/proceed intent, do not ask for quote, attribution, or palette confirmation: leave attribution blank unless the user supplied it or a name is verified in the source, and default to the neutral palette. Mark exact source-checked text VERIFIED; user-provided text USER_SUPPLIED. "
        "For an initial medium or long quote, compose a mobile-first poster layout: 6–9 short, semantically balanced rows for about 20–40 words, adapting count to the quote. Aim for roughly 12–20 characters per row and keep most within 22 as a soft guide. Never strand an article, conjunction, preposition, or verb alone. Let the quote occupy around 45–60% of card height without a large empty center; at a 375px viewport aim for about 30–40px quote type (roughly 115–155px on the 1440px canvas). Split a long row semantically instead of shrinking the entire quote. Use 1–3 short bold/italic/highlight ranges, normally no more than two types, to emphasize the core claim rather than every word or a whole long line. Preserve every word, punctuation mark, negation, and qualifier for VERBATIM/VERIFIED text; never shorten verified wording automatically. Respect explicit plain choices and user-authored lines/styles, and never rewrite an existing quote's layout unless asked. Pass explicit rows in lines and style ranges in styles, with offsets over exact '\\n'.join(lines) using zero-based Unicode code points, inclusive start and exclusive end. Text containing newlines without lines uses splitlines. A short quote stays on its natural concise layout without generated emphasis. Example for the supplied sentence: ‘L’IA aiuta / a chiarire i problemi / e a valutare / le opzioni; / il giudizio / e la responsabilità / restano alle persone.’ "
        "For subsequent explicit chat edits to an already-open editor, call quote_card_builder_update_editor with the complete current draft and editor_revision from widget model context, plus only the requested changed fields in patch; do not call open_workspace/open_editor first. The server merges and renders the full draft, the widget rejects stale revisions, and unspecified fields remain intact. When text changes, use EDITED and UNVERIFIED unless you checked the new wording against an accessible source and pass the corresponding evidence fields explicitly. "
        "Use quote_card_builder_headless with ui_unavailable=true only after a reported UI failure; "
        "production requires explicit approval and matching approved_preview_sha256. "
        "Ask only when the source cannot be read or the user's request remains materially ambiguous. If no attribution is supplied, use none by default rather than asking; preserve a named attribution supplied by the user or verified from the source. The neutral palette is the default unless the user supplies or explicitly chooses custom colors; preserve it or any explicit custom palette through text/attribution updates. Keep missing-choice status visible after rendering. "
        "preview_quote_card and produce_quote_card are UI-private. Use quote_card_builder_headless "
        "only for that explicit no-UI fallback. "
        "Respect explicit user choices; never force an editor the user declined or invent UI failure. "
        "For this MCP workflow, do not use image generation, code execution, or the local filesystem. "
        "Do not ask for tone, mood, or a generic style. Palette means neutral profile or custom colors. "
        "The user selects the style in the editor; accept a volunteered style as a preselection. "
        "For clear proceed intent from a readable source, select one exact quote and use the neutral palette without a confirmation step; ask only if the request or source is materially ambiguous. Generate approves the current editor preview; "
        "the headless path binds approval to its preview hash. For the remote workspace, Download PNG generates and saves "
        "the PNG in one action; there is no Send PNG to chat action. The local 1.8.3 plugin keeps its separate Generate "
        "then Download PNG flow. Local Download PNG can save the PNG in Downloads/Quote Card Builder. On a local PNG path message, embed "
        "the exact file as a Markdown image and provide its absolute path as a download link, without regenerating it. "
        "On a remote PNG URL message, show that exact HTTPS URL as a Markdown image and download link without regenerating it."
    ),
    extensions=[apps, openai_extensions],
)


def configure_http_transport_security() -> TransportSecuritySettings:
    """Apply the explicit host allowlist used by the HTTP deployment."""
    configured_hosts = [
        host.strip()
        for host in os.environ.get("MCP_ALLOWED_HOSTS", "").split(",")
        if host.strip()
    ]
    if not configured_hosts:
        configured_hosts = ["127.0.0.1:*", "localhost:*", "[::1]:*"]
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=configured_hosts,
        allowed_origins=[],
    )


@mcp.custom_route("/health", methods=["GET"], include_in_schema=False)
async def health_check(_request: Request) -> JSONResponse:
    """Expose a minimal unauthenticated health check for container platforms."""
    return JSONResponse({"status": "ok", "service": "quote-card-builder", "mcp_path": "/mcp"})


@mcp.custom_route(
    "/.well-known/openai-apps-challenge",
    methods=["GET"],
    include_in_schema=False,
)
async def openai_apps_challenge(_request: Request) -> Response:
    """Return the exact portal-issued domain challenge when it is configured."""
    token = os.environ.get("OPENAI_APPS_CHALLENGE_TOKEN", "").strip()
    if not token:
        return Response(status_code=404)
    return PlainTextResponse(token)


def _export_headers(filename: str | None = None, *, download: bool = False) -> dict[str, str]:
    headers = {
        "Cache-Control": "private, no-store, max-age=0",
        "Pragma": "no-cache",
        "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "default-src 'none'; sandbox",
        "Referrer-Policy": "no-referrer",
        "Cross-Origin-Resource-Policy": "cross-origin",
    }
    if filename:
        disposition = "attachment" if download else "inline"
        headers["Content-Disposition"] = f'{disposition}; filename="{filename}"'
    return headers


def _export_not_found() -> Response:
    return Response(status_code=404, headers=_export_headers())


@mcp.custom_route(
    "/exports/{token}.png",
    methods=["GET", "HEAD"],
    include_in_schema=False,
)
async def serve_remote_png(request: Request) -> Response:
    """Resolve one unguessable capability URL through the private bucket."""
    store = get_remote_png_store()
    if store is None:
        return _export_not_found()
    try:
        stored = await run_in_threadpool(store.fetch, request.path_params.get("token", ""))
    except RemotePngNotFound:
        return _export_not_found()
    except Exception:
        return Response(status_code=503, headers=_export_headers())

    headers = _export_headers(
        stored.filename,
        download=request.query_params.get("download") == "1",
    )
    headers["Content-Length"] = str(len(stored.data))
    return Response(
        content=stored.data if request.method == "GET" else b"",
        media_type="image/png",
        headers=headers,
    )


def _editor_state(
    request: PreviewQuoteCardInput,
    profile_mode: Literal["neutral", "custom"] | None = None,
    rendered: RenderedQuoteCard | None = None,
) -> EditorState:
    """Build the transport-level snapshot without duplicating rendering logic."""
    return EditorState(
        text=request.text,
        format=request.format,
        attribution=request.attribution,
        profile_mode=profile_mode or ("custom" if request.palette or request.brand_kit else "neutral"),
        transformation=request.transformation,
        evidence_status=request.evidence_status,
        direction=request.direction,
        graphic_mode=request.graphic_mode,
        graphic_variant=request.graphic_variant,
        graphic_seed=request.graphic_seed,
        text_scale=request.text_scale,
        vertical_position=request.vertical_position,
        palette=request.palette or (PaletteInput(name=request.brand_kit["name"], colors=request.brand_kit["colors"]) if request.brand_kit else None),
        lines=request.lines,
        styles=request.styles or [],
        alt_text=request.alt_text,
        brand_kit_attached=request.brand_kit is not None,
        **{key: getattr(rendered, key) if rendered is not None and rendered.rendered else getattr(request, key)
           for key in GrammarFields.model_fields},
    )


@mcp.tool(
    name="validate_brand_kit",
    title="Check brand assets",
    description="Validate a portable brand kit without storing it on the server.",
    annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False),
    meta={"ui": {"visibility": ["app"]}, "openai/widgetAccessible": True},
)
def validate_brand_kit(brand_kit: dict[str, object]) -> dict[str, object]:
    from portable_brand import normalize_brand_kit
    return {"brand_kit": normalize_brand_kit(brand_kit)}


def _render_request(
    request: PreviewQuoteCardInput,
    profile_mode: Literal["neutral", "custom"] | None = None,
) -> RenderedQuoteCard:
    result = RenderedQuoteCard.model_validate(
        render_preview(request.model_dump(exclude={"output_image"}, exclude_none=True))
    )
    return result.model_copy(update={"editor_state": _editor_state(request, profile_mode, result)})


def _compact_output(
    result: RenderedQuoteCard,
    output_model: type[PreviewQuoteCardOutput] = PreviewQuoteCardOutput,
) -> PreviewQuoteCardOutput:
    """Build the output model while retaining the SVG only for legacy serialization."""
    return output_model.model_validate(result.model_dump(mode="json"))


def _wire_payload(result: BaseModel, *, legacy_svg: bool = False) -> dict[str, object]:
    """Serialize output, retaining SVG only for the legacy wire mode."""
    payload = result.model_dump(mode="json")
    payload.pop("brand_kit", None)
    snapshot = payload.get("editor_state")
    if isinstance(snapshot, dict) and snapshot.get("brand_kit") is not None:
        kit = snapshot.pop("brand_kit")
        snapshot["brand_kit_attached"] = True
        snapshot["brand_summary"] = {"name": kit.get("name"), "font_family": (kit.get("font") or {}).get("family"), "logo_present": bool(kit.get("logo"))}
    if not legacy_svg:
        payload.pop("svg", None)
        payload.pop("svg_data_uri", None)
        for preview in payload.get("composition_previews", []):
            preview.pop("svg", None)
    return payload


def _svg_meta(result: RenderedQuoteCard) -> dict[str, object]:
    """Keep the UI-only SVG in the MCP result metadata envelope."""
    return {"quoteCard": {"svg": result.svg, "composition_previews": result.composition_previews,
                          "brand_kit": result.editor_state.brand_kit if result.editor_state else None}} if result.svg else {"quoteCard": {}}


def _summary(result: RenderedQuoteCard | BaseModel) -> dict[str, object]:
    structured = _wire_payload(_compact_output(result)) if isinstance(result, RenderedQuoteCard) else _wire_payload(result)
    return {
        "valid": result.valid,
        "rendered": result.rendered,
        "profile": result.profile,
        "format": result.format,
        "width": result.width,
        "height": result.height,
        "alt_text": result.alt_text,
        "warnings": structured["warnings"],
        "errors": structured["errors"],
    }


@mcp.tool(
    name="preview_quote_card",
    title="Refresh quote card preview",
    description=(
        "Validate text, attribution, direction, palette, line breaks, and formatting, then return "
        "an SVG preview produced by the canonical renderer. This data tool updates an MCP App "
        "that is already open: it does not open interfaces or save or publish data."
    ),
    annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False),
    meta={
        "ui": {"visibility": ["app"]},
        "openai/widgetAccessible": True,
        "openai/visibility": "private",
        "openai/toolInvocation/invoking": "Refreshing preview…",
        "openai/toolInvocation/invoked": "Preview updated.",
    },
    structured_output=True,
)
def preview_quote_card(
    text: str = Field(min_length=1, max_length=600, description="Quote card text."),
    format: Annotated[Literal["4x5", "1x1", "9x16"], Field(description="Card format: 4x5, 1x1, or 9x16.")] = "4x5",
    attribution: Annotated[str, Field(max_length=160, description="Optional visible attribution.")] = "",
    transformation: Literal["VERBATIM", "EDITED", "PARAPHRASE", "AI_GENERATED"] = "VERBATIM",
    evidence_status: Literal["VERIFIED", "USER_SUPPLIED", "UNVERIFIED", "CONFLICT"] = "USER_SUPPLIED",
    direction: Literal["editorial", "statement", "contextual"] = "editorial",
    graphic_mode: Literal["auto", "hidden"] = "auto",
    graphic_variant: str = "default",
    graphic_seed: Annotated[int, Field(ge=0, le=999999)] = 0,
    text_scale: Annotated[float, Field(ge=0.8, le=1.0)] = 1.0,
    vertical_position: Literal["upper", "center", "lower"] = "center",
    palette: PaletteInput | None = None,
    lines: Annotated[list[str] | None, Field(description="Explicit line breaks with no fixed limit; when omitted, use one line.")] = None,
    styles: Annotated[list[StyleRange] | None, Field(max_length=64)] = None,
    alt_text: Annotated[str, Field(max_length=400, description="Optional replacement for the automatic alt text.")] = "",
    output_image: Annotated[bool, Field(description="Compatibility option: when true, also include ImageContent in the MCP response.")] = False,
    compact_output: Annotated[bool, Field(description="Use the compact _meta SVG envelope used by the current UI; omit for legacy UI compatibility.")] = False,
    visual_grammar: Literal["ribbons", "urban"] | None = None,
    composition: dict[str, object] | None = None,
    composition_candidates: Annotated[list[dict[str, object]] | None, Field(max_length=3)] = None,
    proposal_source: Literal["model", "demo"] | None = None,
    quote_font_size: Annotated[float | None, Field(ge=8, le=720)] = None,
    author_font_size: Annotated[float | None, Field(ge=8, le=720)] = None,
    presentation: dict[str, object] | None = None,
    reuse_composition: dict[str, object] | None = None,
    brand_kit: dict[str, object] | None = None,
    logo_mode: Literal["auto", "hidden"] = "auto",
) -> PreviewQuoteCardOutput:
    request = PreviewQuoteCardInput(
        text=text,
        format=format,
        attribution=attribution,
        transformation=transformation,
        evidence_status=evidence_status,
        direction=direction,
        graphic_mode=graphic_mode,
        graphic_variant=graphic_variant,
        graphic_seed=graphic_seed,
        text_scale=text_scale,
        vertical_position=vertical_position,
        palette=palette.model_dump(mode="json") if palette else None,
        lines=lines,
        styles=styles,
        alt_text=alt_text,
        visual_grammar=visual_grammar,
        composition=composition,
        composition_candidates=composition_candidates or [],
        proposal_source=proposal_source,
        quote_font_size=quote_font_size,
        author_font_size=author_font_size,
        presentation=presentation,
        reuse_composition=reuse_composition,
        brand_kit=brand_kit,
        logo_mode=logo_mode,
    )
    result = _render_request(request)
    compact_output_flag = compact_output if isinstance(compact_output, bool) else False
    structured = _wire_payload(_compact_output(result), legacy_svg=not compact_output_flag)
    if result.rendered and result.svg:
        content = [
            TextContent(
                type="text",
                text=json.dumps(_summary(result), ensure_ascii=False, indent=2),
            ),
        ]
        if output_image:
            content.append(
                ImageContent(
                    type="image",
                    data=base64.b64encode(result.svg.encode("utf-8")).decode("ascii"),
                    mime_type="image/svg+xml",
                ),
            )
    else:
        content = [
            TextContent(
                type="text",
                text=json.dumps(structured, ensure_ascii=False, indent=2),
            )
        ]
    return CallToolResult(
        content=content,
        structuredContent=structured,
        _meta=_svg_meta(result),
        isError=False,
    )


@mcp.tool(
    name="produce_quote_card",
    title="Generate quote card",
    description=(
        "Validate the current editor state again and produce a downloadable SVG with the same "
        "canonical renderer used by the preview. This is a private MCP App tool: it does not "
        "open interfaces, publish data, or retain files on the server."
    ),
    annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False),
    meta={
        "ui": {"visibility": ["app"]},
        "openai/widgetAccessible": True,
        "openai/visibility": "private",
        "openai/toolInvocation/invoking": "Generating quote card…",
        "openai/toolInvocation/invoked": "Quote card ready.",
    },
    structured_output=True,
)
def produce_quote_card(
    text: str = Field(min_length=1, max_length=600, description="Quote card text."),
    format: Annotated[Literal["4x5", "1x1", "9x16"], Field(description="Card format: 4x5, 1x1, or 9x16.")] = "4x5",
    attribution: Annotated[str, Field(max_length=160, description="Optional visible attribution.")] = "",
    transformation: Literal["VERBATIM", "EDITED", "PARAPHRASE", "AI_GENERATED"] = "VERBATIM",
    evidence_status: Literal["VERIFIED", "USER_SUPPLIED", "UNVERIFIED", "CONFLICT"] = "USER_SUPPLIED",
    direction: Literal["editorial", "statement", "contextual"] = "editorial",
    graphic_mode: Literal["auto", "hidden"] = "auto",
    graphic_variant: str = "default",
    graphic_seed: Annotated[int, Field(ge=0, le=999999)] = 0,
    text_scale: Annotated[float, Field(ge=0.8, le=1.0)] = 1.0,
    vertical_position: Literal["upper", "center", "lower"] = "center",
    palette: PaletteInput | None = None,
    lines: Annotated[list[str] | None, Field(description="Explicit line breaks with no fixed limit.")] = None,
    styles: Annotated[list[StyleRange] | None, Field(max_length=64)] = None,
    alt_text: Annotated[str, Field(max_length=400)] = "",
    compact_output: Annotated[bool, Field(description="Use the compact _meta SVG envelope used by the current UI; omit for legacy UI compatibility.")] = False,
    visual_grammar: Literal["ribbons", "urban"] | None = None,
    composition: dict[str, object] | None = None,
    composition_candidates: Annotated[list[dict[str, object]] | None, Field(max_length=3)] = None,
    proposal_source: Literal["model", "demo"] | None = None,
    quote_font_size: Annotated[float | None, Field(ge=8, le=720)] = None,
    author_font_size: Annotated[float | None, Field(ge=8, le=720)] = None,
    presentation: dict[str, object] | None = None,
    reuse_composition: dict[str, object] | None = None,
    brand_kit: dict[str, object] | None = None,
    logo_mode: Literal["auto", "hidden"] = "auto",
) -> ProduceQuoteCardOutput:
    request = PreviewQuoteCardInput(
        text=text,
        format=format,
        attribution=attribution,
        transformation=transformation,
        evidence_status=evidence_status,
        direction=direction,
        graphic_mode=graphic_mode,
        graphic_variant=graphic_variant,
        graphic_seed=graphic_seed,
        text_scale=text_scale,
        vertical_position=vertical_position,
        palette=palette,
        lines=lines,
        styles=styles,
        alt_text=alt_text,
        output_image=False,
        visual_grammar=visual_grammar,
        composition=composition,
        composition_candidates=composition_candidates or [],
        proposal_source=proposal_source,
        quote_font_size=quote_font_size,
        author_font_size=author_font_size,
        presentation=presentation,
        reuse_composition=reuse_composition,
        brand_kit=brand_kit,
        logo_mode=logo_mode,
    )
    preview = _render_request(request)
    produced = bool(preview.valid and preview.rendered and preview.svg and preview.svg_sha256)
    result = ProduceQuoteCardOutput.model_validate(
        {
            **preview.model_dump(mode="json"),
            "svg": preview.svg,
            "produced": produced,
            "filename": f"quote-card-{preview.svg_sha256[:8]}.svg" if produced else None,
            "mime_type": "image/svg+xml",
            "local_file_delivery": LOCAL_FILE_DELIVERY,
            "remote_file_delivery": remote_delivery_configured(),
        }
    )
    compact_output_flag = compact_output if isinstance(compact_output, bool) else False
    summary = _summary(result)
    summary.update(
        {
            "produced": result.produced,
            "filename": result.filename,
            "mime_type": result.mime_type,
            "local_file_delivery": result.local_file_delivery,
            "remote_file_delivery": result.remote_file_delivery,
        }
    )
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(summary, ensure_ascii=False, indent=2))],
        structuredContent=_wire_payload(result, legacy_svg=not compact_output_flag),
        _meta=_svg_meta(preview),
        isError=False,
    )


def _validated_png(blob: str) -> bytes:
    """Accept complete canvas PNGs of the supported output sizes, within bounds."""
    if len(blob) > ((MAX_PNG_BYTES + 2) // 3) * 4:
        raise ValueError("PNG exceeds the 8 MiB limit.")
    try:
        data = base64.b64decode(blob, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("Invalid PNG base64.") from exc
    if len(data) > MAX_PNG_BYTES or not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("Invalid PNG signature or size.")
    offset = 8
    compressed = bytearray()
    expected = None
    ended = False
    while offset + 12 <= len(data):
        length = struct.unpack_from(">I", data, offset)[0]
        end = offset + length + 12
        if end > len(data):
            raise ValueError("Truncated PNG chunk.")
        kind = data[offset + 4:offset + 8]
        chunk = data[offset + 8:end - 4]
        crc = struct.unpack_from(">I", data, end - 4)[0]
        if zlib.crc32(kind + chunk) & 0xffffffff != crc:
            raise ValueError("Invalid PNG checksum.")
        if offset == 8:
            if kind != b"IHDR" or length != 13:
                raise ValueError("Missing PNG header.")
            width, height, depth, color, compression, filtering, interlace = struct.unpack(">IIBBBBB", chunk)
            if (width, height) not in ((1440, 1440), (1440, 1800), (1440, 2560)) or depth != 8 or color not in (2, 6) or (compression, filtering, interlace) != (0, 0, 0):
                raise ValueError("Unsupported PNG dimensions or encoding.")
            expected = (width * (4 if color == 6 else 3) + 1) * height
        elif kind == b"IHDR":
            raise ValueError("Duplicate PNG header.")
        if kind == b"IDAT":
            compressed.extend(chunk)
        if kind == b"IEND":
            if length or end != len(data):
                raise ValueError("Invalid PNG ending.")
            ended = True
            break
        offset = end
    if not ended or not compressed or expected is None:
        raise ValueError("Incomplete PNG.")
    try:
        decoder = zlib.decompressobj()
        pixels = decoder.decompress(compressed, expected + 1)
    except zlib.error as exc:
        raise ValueError("Invalid PNG pixels.") from exc
    if len(pixels) != expected or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
        raise ValueError("Invalid PNG pixel size.")
    return data


@mcp.tool(
    name="quote_card_builder_save_png",
    title="Save the generated PNG locally",
    description="Private editor action: save the exact generated PNG in Downloads/Quote Card Builder. Available only in the local stdio plugin after Download PNG.",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False),
    meta={"ui": {"visibility": ["app"]}, "openai/widgetAccessible": True, "openai/visibility": "private"},
    structured_output=True,
)
def quote_card_builder_save_png(
    png_base64: str = Field(min_length=1, max_length=((MAX_PNG_BYTES + 2) // 3) * 4),
) -> SavedPngOutput:
    if not LOCAL_FILE_DELIVERY:
        raise ValueError("Local PNG delivery is disabled for this server.")
    data = _validated_png(png_base64)
    digest = hashlib.sha256(data).hexdigest()
    folder = Path.home() / "Downloads" / "Quote Card Builder"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"quote-card-{digest[:16]}.png"
    # Publish complete bytes atomically without replacing an existing file.
    # Download and Send can race; neither may observe a half-written PNG.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=folder, prefix=".qcb-", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(data)
        try:
            os.link(temporary, path)
        except FileExistsError:
            if path.is_symlink() or path.read_bytes() != data:
                raise ValueError("A different file already occupies this PNG path.")
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return SavedPngOutput(path=str(path.absolute()), filename=path.name, sha256=digest)


@mcp.tool(
    name="quote_card_builder_publish_png",
    title="Send the generated PNG to chat",
    description=(
        "Private editor action: validate and upload the exact generated PNG to a bounded "
        "24-hour capability URL. Available only when remote delivery is configured."
    ),
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    ),
    meta={"ui": {"visibility": ["app"]}, "openai/widgetAccessible": True, "openai/visibility": "private"},
    structured_output=True,
)
def quote_card_builder_publish_png(
    png_base64: str = Field(min_length=1, max_length=((MAX_PNG_BYTES + 2) // 3) * 4),
) -> PublishedPngOutput:
    store = get_remote_png_store()
    if store is None:
        raise ValueError("Remote PNG delivery is disabled for this server.")
    data = _validated_png(png_base64)
    try:
        published = store.publish(data)
    except RemotePngRateLimited as exc:
        raise ValueError(
            f"Remote PNG upload limit reached. Try again in about {exc.retry_after_seconds} seconds."
        ) from exc
    except RemotePngBusy as exc:
        raise ValueError("Remote PNG delivery is busy. Try again in a moment.") from exc
    except Exception as exc:
        raise ValueError("Remote PNG delivery failed. Try again.") from exc
    return PublishedPngOutput(
        url=published.url,
        filename=published.filename,
        sha256=published.sha256,
        expires_at=published.expires_at,
    )


def _svg_resource(result: RenderedQuoteCard, uri: str) -> EmbeddedResource | None:
    """Expose a headless SVG only as an explicit MCP resource content block."""
    if not result.rendered or not result.svg:
        return None
    return EmbeddedResource(
        resource=TextResourceContents(
            uri=uri,
            mimeType="image/svg+xml",
            text=result.svg,
        )
    )


@mcp.tool(
    name="quote_card_builder_headless",
    title="Use Quote Card Builder without the editor",
    description=(
        "Explicit fallback for hosts that genuinely cannot mount the Quote Card Builder editor. "
        "Set ui_unavailable=true only after the host has reported that the UI is unavailable. "
        "Use action=preview to return a model-accessible SVG resource and validation metadata. "
        "Use action=produce only after the caller explicitly approves production and supplies "
        "approved_preview_sha256 matching the current preview; approval_received is a caller "
        "declaration, not cryptographic proof of human consent. The normal editor workflow and "
        "its Generate action remain preferred whenever the UI is available."
    ),
    annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False),
    meta={
        "openai/toolInvocation/invoking": "Preparing headless quote card…",
        "openai/toolInvocation/invoked": "Headless quote card ready.",
    },
    structured_output=True,
)
def quote_card_builder_headless(
    action: Literal["preview", "produce"] = Field(
        description="Fallback action: preview validates and returns an SVG resource; produce requires approval."
    ),
    input: PreviewQuoteCardInput = Field(
        description="Complete quote-card render input, including text, palette, direction, and formatting."
    ),
    ui_unavailable: bool = Field(
        default=False,
        description="Must be true only when the host has genuinely reported that the editor UI is unavailable.",
    ),
    approve_production: bool = Field(
        default=False,
        description="Explicit caller approval for action=produce; ignored for action=preview.",
    ),
    approved_preview_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-fA-F]{64}$",
        description="SHA-256 of the exact preview being approved for production.",
    ),
) -> HeadlessQuoteCardOutput:
    # Direct in-process tests call the decorated function without the MCP
    # argument parser, so Pydantic FieldInfo defaults can still be present.
    # Normalize those defaults exactly as the wire parser does.
    ui_unavailable_flag = ui_unavailable if isinstance(ui_unavailable, bool) else False
    approve_production_flag = approve_production if isinstance(approve_production, bool) else False
    approved_hash = approved_preview_sha256 if isinstance(approved_preview_sha256, str) else None
    if not ui_unavailable_flag:
        raise ValueError(
            "The headless fallback requires ui_unavailable=true after the host reports that the editor cannot mount."
        )

    request_input = input if isinstance(input, PreviewQuoteCardInput) else PreviewQuoteCardInput.model_validate(input)
    request = request_input.model_copy(update={"output_image": False})
    preview = _render_request(request)
    preview_hash = preview.svg_sha256 or ""
    approval_received = bool(
        action == "produce"
        and approve_production_flag
        and approved_hash
        and preview_hash
        and approved_hash.lower() == preview_hash.lower()
    )
    errors = list(preview.errors)
    approval_error: ValidationIssue | None = None
    if action == "produce" and not approval_received:
        if not approve_production_flag:
            approval_error = ValidationIssue(
                path="approve_production",
                code="approval_required",
                message="Production is withheld until the caller explicitly approves it.",
            )
        elif not approved_hash:
            approval_error = ValidationIssue(
                path="approved_preview_sha256",
                code="approval_binding_required",
                message="Production approval must include the SHA-256 of the current preview.",
            )
        else:
            approval_error = ValidationIssue(
                path="approved_preview_sha256",
                code="approval_mismatch",
                message="The approval hash does not match the current preview; production was withheld.",
            )
        errors.append(approval_error)

    produced = bool(action == "produce" and approval_received and preview.valid and preview.rendered and preview.svg)
    resource_uri = None
    filename = None
    resource = None
    if preview.rendered and preview.svg and preview_hash and (action == "preview" or produced):
        suffix = "preview" if action == "preview" else "production"
        resource_uri = f"urn:quote-card-builder:{suffix}:{preview_hash}.svg"
        resource = _svg_resource(preview, resource_uri)
    if produced:
        filename = f"quote-card-{preview_hash[:8]}.svg"
    output = HeadlessQuoteCardOutput.model_validate(
        {
            **_compact_output(preview).model_dump(mode="json"),
            "errors": [item.model_dump(mode="json") for item in errors],
            "action": action,
            "ui_unavailable": True,
            "approval_required": action == "produce",
            "approval_received": approval_received,
            "produced": produced,
            "filename": filename,
            "mime_type": "image/svg+xml",
            "resource_uri": resource_uri,
        }
    )
    summary = _summary(output)
    summary.update(
        {
            "action": output.action,
            "ui_unavailable": output.ui_unavailable,
            "approval_required": output.approval_required,
            "approval_received": output.approval_received,
            "produced": output.produced,
            "filename": output.filename,
            "resource_uri": output.resource_uri,
        }
    )
    content: list[TextContent | EmbeddedResource] = [
        TextContent(type="text", text=json.dumps(summary, ensure_ascii=False, indent=2))
    ]
    if resource is not None and (action == "preview" or produced):
        content.append(resource)
    return CallToolResult(
        content=content,
        structuredContent=output.model_dump(mode="json"),
        isError=bool(action == "produce" and not approval_received),
    )


def main() -> int:
    global LOCAL_FILE_DELIVERY
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--local-file-delivery", action="store_true", help="Allow explicit editor actions to save PNGs in Downloads; local stdio only.")
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        default="stdio",
        help="MCP transport. The plugin package uses stdio; Streamable HTTP supports testing and the remote runtime.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host for local Streamable HTTP.")
    parser.add_argument(
        "--port",
        type=int,
        default=os.environ.get("PORT", "8000"),
        help="Port for Streamable HTTP; Cloud Run provides PORT (8080 by default).",
    )
    args = parser.parse_args()
    if args.local_file_delivery and args.transport != "stdio":
        parser.error("--local-file-delivery requires the local stdio transport")
    LOCAL_FILE_DELIVERY = args.local_file_delivery

    transport_security = None
    if args.transport == "streamable-http":
        # MCPServer receives the HTTP binding and protection policy when the
        # transport starts; unlike FastMCP they are not mutable server settings.
        transport_security = configure_http_transport_security()
        mcp.run(
            transport="streamable-http",
            host=args.host,
            port=args.port,
            stateless_http=True,
            json_response=True,
            max_request_body_size=MCP_HTTP_MAX_REQUEST_BYTES,
            transport_security=transport_security,
        )
    else:
        mcp.run(transport="stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
