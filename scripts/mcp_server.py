#!/usr/bin/env python3
"""MCP server for Quote Card Builder's preview and SVG production slice."""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import tomllib
from pathlib import Path
from typing import Annotated, Literal

try:
    from mcp.server import MCPServer
    from mcp.server.apps import Apps, ResourceCsp, TextResource
    from mcp.server.transport_security import TransportSecuritySettings
    from mcp_types import (
        CallToolResult,
        EmbeddedResource,
        ImageContent,
        TextContent,
        TextResourceContents,
        ToolAnnotations,
    )
    from pydantic import BaseModel, Field
    from starlette.requests import Request
    from starlette.responses import JSONResponse, PlainTextResponse, Response
except ImportError as exc:  # pragma: no cover - exercised by the launcher, not the core tests
    raise SystemExit(
        "MCP SDK missing: create a virtual environment and install requirements-mcp.txt before starting the server."
    ) from exc

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from mcp_quote_card import preview_quote_card as render_preview
from mcp_app import (
    QUOTE_CARD_DOWNLOAD_REDIRECT_DOMAINS,
    QUOTE_CARD_LEGACY_PREVIEW_RESOURCES,
    QUOTE_CARD_PREVIEW_MIME_TYPE,
    QUOTE_CARD_PREVIEW_DOMAIN,
    QUOTE_CARD_PREVIEW_RESOURCE,
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


class StyleRange(BaseModel):
    start: int = Field(ge=0, description="Starting Unicode offset, inclusive.")
    end: int = Field(gt=0, description="Ending Unicode offset, exclusive.")
    type: Literal["bold", "italic", "underline", "highlight", "accent", "outline"]


class PaletteColors(BaseModel):
    primary: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$", description="Primary color #RRGGBB.")
    accent: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$", description="Accent color #RRGGBB.")
    background: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$", description="Background color #RRGGBB.")
    text: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$", description="Text and metadata color #RRGGBB.")


class PaletteInput(BaseModel):
    name: str = Field(min_length=1, max_length=80, description="User-provided palette name.")
    colors: PaletteColors


class PreviewQuoteCardInput(BaseModel):
    text: str = Field(min_length=1, max_length=600, description="Quote card text.")
    format: Literal["4x5", "1x1"] = Field(default="4x5", description="Card format: 4x5 portrait or 1x1 square.")
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


class EditorState(BaseModel):
    """Authoritative editor snapshot echoed by every render tool result."""

    text: str
    format: Literal["4x5", "1x1"] = "4x5"
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


class ValidationIssue(BaseModel):
    path: str
    code: str
    message: str


class RenderedQuoteCard(BaseModel):
    """Internal result from the canonical renderer, including SVG bytes."""

    valid: bool
    rendered: bool
    profile: str
    direction: Literal["editorial", "statement", "contextual"]
    graphic_mode: Literal["auto", "hidden"] = "auto"
    graphic_variant: str = "default"
    text_scale: float = 1.0
    vertical_position: Literal["upper", "center", "lower"] = "center"
    format: Literal["4x5", "1x1"]
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


class CompactQuoteCardOutput(BaseModel):
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
    format: Literal["4x5", "1x1"]
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


class PreviewQuoteCardOutput(CompactQuoteCardOutput):
    """Preview output with an optional legacy structured SVG field."""

    svg: str | None = None
    svg_data_uri: str | None = None


class ProduceQuoteCardOutput(PreviewQuoteCardOutput):
    produced: bool
    filename: str | None
    mime_type: Literal["image/svg+xml"] = "image/svg+xml"


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


apps = Apps()
_EDITOR_CSP = ResourceCsp(
    connect_domains=[],
    resource_domains=[],
    frame_domains=[],
    base_uri_domains=[],
)


def _add_preview_resource(uri: str, *, legacy: bool = False) -> None:
    """Register the current editor under its canonical or cached Apps URI."""
    ui_meta = {
        "csp": _EDITOR_CSP.model_dump(by_alias=True, exclude_none=True),
        "domain": QUOTE_CARD_PREVIEW_DOMAIN,
        "prefersBorder": True,
    }
    apps.add_resource(
        TextResource(
            uri=uri,
            text=quote_card_preview_html(),
            name=("quote-card-preview-compatibility" if legacy else "quote-card-preview-ui"),
            title=(
                "Quote Card Builder preview (compatibility alias)"
                if legacy
                else "Quote Card Builder preview"
            ),
            description=(
                "Compatibility alias that serves the current editor version."
                if legacy
                else "Inline editor for viewing and updating a validated quote card."
            ),
            mime_type=QUOTE_CARD_PREVIEW_MIME_TYPE,
            meta={
                "ui": ui_meta,
                "openai/widgetCSP": {
                    "connect_domains": [],
                    "resource_domains": [],
                    "redirect_domains": list(QUOTE_CARD_DOWNLOAD_REDIRECT_DOMAINS),
                },
            },
        )
    )


_add_preview_resource(QUOTE_CARD_PREVIEW_RESOURCE)
for _legacy_preview_uri in QUOTE_CARD_LEGACY_PREVIEW_RESOURCES:
    _add_preview_resource(_legacy_preview_uri, legacy=True)


@apps.tool(
    resource_uri=QUOTE_CARD_PREVIEW_RESOURCE,
    visibility=["model"],
    name="quote_card_builder_open_editor",
    title="Open Quote Card Builder",
    description=(
        "Use this when the user selects Quote Card Builder or asks to create, test, or open a "
        "quote card. This is the workflow's primary public tool and opens the interactive inline "
        "editor. If Quote, Attribution, and Palette are known, call it once. If a "
        "choice is missing, ask for it with these exact labels: 1. Quote; 2. Visible attribution "
        "or none; 3. Palette, neutral profile or custom. The third item is the palette, never tone or mood. "
        "The user chooses style in the editor; use Blocks, Cutouts, Constellations, or Gradient only as an "
        "optional preselection volunteered by the user. Do not use image generation or a local "
        "filesystem. Do not choose values for the user. Call this tool exactly once and do not "
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
        title="1. Quote",
        description="First answer: the quote explicitly chosen by the user.",
    ),
    attribution: str = Field(
        max_length=160,
        title="2. Visible attribution",
        description="Second answer: visible attribution; use an empty string only after the user chooses none.",
    ),
    profile_mode: Literal["neutral", "custom"] = Field(
        title="3. Palette",
        description=(
            "Third explicit user choice: neutral for the neutral profile/palette, custom for a "
            "provided custom palette. This does not represent tone, mood, or style."
        ),
    ),
    style: Annotated[Literal["blocks", "cutouts", "constellations", "gradient"], Field(
        title="Style preselection (optional)",
        description=(
            "Optional preselection volunteered by the user. The user can choose Blocks, Cutouts, "
            "Constellations, or Gradient in the editor; defaults to Blocks. Do not accept a generic style label."
        ),
    )] = "blocks",
    format: Annotated[Literal["4x5", "1x1"], Field(title="Initial format", description="Optional initial format: 4x5 portrait or 1x1 square.")] = "4x5",
    palette: Annotated[PaletteInput | None, Field(title="Custom palette colors", description="Required only when 3. Palette is custom; includes a name and four colors.")] = None,
) -> PreviewQuoteCardOutput:
    """Render the initial snapshot once; the widget handles later data calls."""
    if profile_mode == "custom" and palette is None:
        raise ValueError(
            "A custom palette requires a name and primary, accent, background, and text colors."
        )
    style_map = {
        "blocks": ("editorial", "cover"),
        "cutouts": ("editorial", "cutouts"),
        "constellations": ("contextual", "constellations"),
        "gradient": ("editorial", "gradient"),
    }
    direction, graphic_variant = style_map[style]
    request = PreviewQuoteCardInput(
        text=text,
        format=format,
        attribution=attribution,
        transformation="VERBATIM",
        evidence_status="USER_SUPPLIED",
        direction=direction,
        graphic_mode="auto",
        graphic_variant=graphic_variant,
        text_scale=1.0,
        vertical_position="center",
        palette=palette.model_dump(mode="json") if profile_mode == "custom" and palette else None,
        lines=None,
        styles=None,
        alt_text="",
        output_image=False,
    )
    result = _render_request(request, profile_mode)
    # Keep the initial envelope readable by older cached editor instances.
    # Subsequent v1.40 data calls opt into compact_output=True.
    structured = _wire_payload(_compact_output(result), legacy_svg=True)
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(_summary(result), ensure_ascii=False, indent=2))],
        structuredContent=structured,
        _meta=_svg_meta(result),
        isError=False,
    )


mcp = MCPServer(
    name="quote-card-builder",
    title="Quote Card Builder",
    version=MCP_SERVER_VERSION,
    description="Canonical quote-card renderer with an inline MCP Apps editor.",
    instructions=(
        "With the user's quote, attribution (or none), and chosen palette, call "
        "quote_card_builder_open_editor once. Ask only for missing choices: 1. Quote; "
        "2. Visible attribution; 3. Palette. preview_quote_card and produce_quote_card are "
        "UI-private. Use quote_card_builder_headless with ui_unavailable=true only after the "
        "host reports unavailable UI; production requires explicit approval and matching "
        "approved_preview_sha256. "
        "Respect explicit user choices; never force an editor the user declined or invent UI failure. "
        "For this MCP workflow, do not use image generation, code execution, or the local filesystem. "
        "Do not ask for tone, mood, or a generic style. Palette means neutral profile or custom colors. "
        "The user selects the style in the editor; accept a volunteered style as a preselection. "
        "Do not choose missing values for the user. Generate approves the current editor preview; "
        "the headless path binds approval to its preview hash. The server renders in memory "
        "without publishing or retaining outputs."
    ),
    extensions=[apps],
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


def _editor_state(
    request: PreviewQuoteCardInput,
    profile_mode: Literal["neutral", "custom"] | None = None,
) -> EditorState:
    """Build the transport-level snapshot without duplicating rendering logic."""
    return EditorState(
        text=request.text,
        format=request.format,
        attribution=request.attribution,
        profile_mode=profile_mode or ("custom" if request.palette else "neutral"),
        transformation=request.transformation,
        evidence_status=request.evidence_status,
        direction=request.direction,
        graphic_mode=request.graphic_mode,
        graphic_variant=request.graphic_variant,
        graphic_seed=request.graphic_seed,
        text_scale=request.text_scale,
        vertical_position=request.vertical_position,
        palette=request.palette,
        lines=request.lines,
        styles=request.styles or [],
        alt_text=request.alt_text,
    )


def _render_request(
    request: PreviewQuoteCardInput,
    profile_mode: Literal["neutral", "custom"] | None = None,
) -> RenderedQuoteCard:
    result = RenderedQuoteCard.model_validate(
        render_preview(request.model_dump(exclude={"output_image"}, exclude_none=True))
    )
    return result.model_copy(update={"editor_state": _editor_state(request, profile_mode)})


def _compact_output(
    result: RenderedQuoteCard,
    output_model: type[PreviewQuoteCardOutput] = PreviewQuoteCardOutput,
) -> PreviewQuoteCardOutput:
    """Build the output model while retaining the SVG only for legacy serialization."""
    return output_model.model_validate(result.model_dump(mode="json"))


def _wire_payload(result: BaseModel, *, legacy_svg: bool = False) -> dict[str, object]:
    """Serialize output, retaining SVG only for the legacy wire mode."""
    payload = result.model_dump(mode="json")
    if not legacy_svg:
        payload.pop("svg", None)
        payload.pop("svg_data_uri", None)
    return payload


def _svg_meta(result: RenderedQuoteCard) -> dict[str, object]:
    """Keep the UI-only SVG in the MCP result metadata envelope."""
    return {"quoteCard": {"svg": result.svg}} if result.svg else {"quoteCard": {}}


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
    format: Annotated[Literal["4x5", "1x1"], Field(description="Card format: 4x5 portrait or 1x1 square.")] = "4x5",
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
    format: Annotated[Literal["4x5", "1x1"], Field(description="Card format: 4x5 portrait or 1x1 square.")] = "4x5",
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
        }
    )
    compact_output_flag = compact_output if isinstance(compact_output, bool) else False
    summary = _summary(result)
    summary.update({"produced": result.produced, "filename": result.filename, "mime_type": result.mime_type})
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(summary, ensure_ascii=False, indent=2))],
        structuredContent=_wire_payload(result, legacy_svg=not compact_output_flag),
        _meta=_svg_meta(preview),
        isError=False,
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
    parser = argparse.ArgumentParser(description=__doc__)
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

    transport_security = None
    if args.transport == "streamable-http":
        # MCPServer receives the HTTP binding and protection policy when the
        # transport starts; unlike FastMCP they are not mutable server settings.
        transport_security = configure_http_transport_security()
        mcp.run(
            transport="streamable-http",
            host=args.host,
            port=args.port,
            transport_security=transport_security,
        )
    else:
        mcp.run(transport="stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
