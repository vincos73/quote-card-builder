#!/usr/bin/env python3
"""MCP server for Quote Card Builder's preview and SVG production slice."""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from pathlib import Path
from typing import Literal

try:
    from mcp.server.fastmcp import FastMCP
    from mcp.types import CallToolResult, ImageContent, TextContent, ToolAnnotations
    from mcp.server.transport_security import TransportSecuritySettings
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
    QUOTE_CARD_LEGACY_PREVIEW_RESOURCES,
    QUOTE_CARD_PREVIEW_MIME_TYPE,
    QUOTE_CARD_PREVIEW_DOMAIN,
    QUOTE_CARD_PREVIEW_RESOURCE,
    quote_card_preview_html,
)


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
    text_scale: float = Field(default=1.0, ge=0.8, le=1.0, description="Text scale relative to the available maximum.")
    vertical_position: Literal["upper", "center", "lower"] = Field(default="center", description="Vertical position of the text block.")
    palette: PaletteInput | None = Field(
        default=None,
        description="Palette explicitly selected by the user; when omitted, use the neutral profile.",
    )
    lines: list[str] | None = Field(default=None, description="Explicit line breaks with no fixed limit; when omitted, use one line.")
    styles: list[StyleRange] | None = Field(default=None, max_length=64)
    alt_text: str = Field(default="", max_length=400, description="Optional replacement for the automatic alt text.")
    output_image: bool = Field(default=True, description="When true, also include ImageContent in the MCP response.")


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


class PreviewQuoteCardOutput(BaseModel):
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


class ProduceQuoteCardOutput(PreviewQuoteCardOutput):
    produced: bool
    filename: str | None
    mime_type: Literal["image/svg+xml"] = "image/svg+xml"


mcp = FastMCP(
    "quote-card-builder",
    instructions=(
        "Quote Card Builder is a remote MCP app with an inline editor. When the user selects "
        "this app or asks to create, test, or open a quote card, use only this workflow. Do not "
        "use image generation, code execution, the local filesystem, standalone SVG, PNG, HTML, "
        "or files, and do not look for a local editor. If information is missing, ask exactly: "
        "1. Quote; 2. Visible attribution or 'none'; 3. Palette: 'neutral profile' or 'custom'; "
        "4. Direction: Editorial, Poster, or Frame. Do not ask for tone, mood, minimal, or a "
        "generic style. Do not choose defaults for the user. Once all four answers are known, "
        "call quote_card_builder_open_editor exactly once to show the inline editor. Do not call "
        "preview_quote_card or produce_quote_card: they are private tools used by the interface "
        "to refresh the same preview and produce the SVG after an explicit click on Generate. "
        "The server does not publish or retain outputs and uses the canonical Python renderer."
    ),
)


@mcp.resource(
    QUOTE_CARD_PREVIEW_RESOURCE,
    name="quote_card_preview_ui",
    title="Quote Card Builder preview",
    description="Optional UI for viewing and updating a validated quote card.",
    mime_type=QUOTE_CARD_PREVIEW_MIME_TYPE,
    meta={
        "ui": {
            "prefersBorder": True,
            "domain": QUOTE_CARD_PREVIEW_DOMAIN,
            "csp": {
                "connectDomains": [],
                "resourceDomains": [],
                "frameDomains": [],
            },
        },
        "openai/widgetCSP": {
            "connect_domains": [],
            "resource_domains": [],
            "redirect_domains": [
                "https://oaisdmntpritalynorth.blob.core.windows.net",
            ],
        },
    },
)
def quote_card_preview_ui() -> str:
    """Return the portable MCP Apps component for the preview tool."""
    return quote_card_preview_html()


def _register_legacy_preview_resources() -> None:
    """Keep cached ChatGPT descriptors able to fetch the current editor HTML."""
    for uri in QUOTE_CARD_LEGACY_PREVIEW_RESOURCES:
        version = uri.rsplit("/", 1)[-1].removesuffix(".html").replace(".", "")

        def legacy_preview_ui() -> str:
            return quote_card_preview_html()

        legacy_preview_ui.__name__ = f"quote_card_preview_ui_{version}"
        mcp.resource(
            uri,
            name=legacy_preview_ui.__name__,
            title="Quote Card Builder preview (compatibility alias)",
            description="Compatibility alias that serves the current editor version.",
            mime_type=QUOTE_CARD_PREVIEW_MIME_TYPE,
            meta={
                "ui": {
                    "prefersBorder": True,
                    "domain": QUOTE_CARD_PREVIEW_DOMAIN,
                    "csp": {
                        "connectDomains": [],
                        "resourceDomains": [],
                        "frameDomains": [],
                    },
                },
                "openai/widgetCSP": {
                    "connect_domains": [],
                    "resource_domains": [],
                    "redirect_domains": [],
                },
            },
        )(legacy_preview_ui)


_register_legacy_preview_resources()


def configure_http_transport_security() -> None:
    """Apply the explicit host allowlist used by the HTTP deployment."""
    configured_hosts = [
        host.strip()
        for host in os.environ.get("MCP_ALLOWED_HOSTS", "").split(",")
        if host.strip()
    ]
    if not configured_hosts:
        configured_hosts = ["127.0.0.1:*", "localhost:*", "[::1]:*"]
    mcp.settings.transport_security = TransportSecuritySettings(
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
) -> PreviewQuoteCardOutput:
    result = PreviewQuoteCardOutput.model_validate(
        render_preview(request.model_dump(exclude={"output_image"}, exclude_none=True))
    )
    return result.model_copy(update={"editor_state": _editor_state(request, profile_mode)})


def _summary(result: PreviewQuoteCardOutput) -> dict[str, object]:
    structured = result.model_dump(mode="json")
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
    format: Literal["4x5", "1x1"] = Field(default="4x5", description="Card format: 4x5 portrait or 1x1 square."),
    attribution: str = Field(default="", max_length=160, description="Optional visible attribution."),
    transformation: Literal["VERBATIM", "EDITED", "PARAPHRASE", "AI_GENERATED"] = "VERBATIM",
    evidence_status: Literal["VERIFIED", "USER_SUPPLIED", "UNVERIFIED", "CONFLICT"] = "USER_SUPPLIED",
    direction: Literal["editorial", "statement", "contextual"] = "editorial",
    graphic_mode: Literal["auto", "hidden"] = "auto",
    graphic_variant: str = "default",
    text_scale: float = Field(default=1.0, ge=0.8, le=1.0),
    vertical_position: Literal["upper", "center", "lower"] = "center",
    palette: PaletteInput | None = None,
    lines: list[str] | None = Field(default=None, description="Explicit line breaks with no fixed limit; when omitted, use one line."),
    styles: list[StyleRange] | None = Field(default=None, max_length=64),
    alt_text: str = Field(default="", max_length=400, description="Optional replacement for the automatic alt text."),
    output_image: bool = Field(default=True, description="When true, also include ImageContent in the MCP response."),
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
        text_scale=text_scale,
        vertical_position=vertical_position,
        palette=palette.model_dump(mode="json") if palette else None,
        lines=lines,
        styles=styles,
        alt_text=alt_text,
    )
    result = _render_request(request)
    structured = result.model_dump(mode="json")
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
                mimeType="image/svg+xml",
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
    format: Literal["4x5", "1x1"] = Field(default="4x5", description="Card format: 4x5 portrait or 1x1 square."),
    attribution: str = Field(default="", max_length=160, description="Optional visible attribution."),
    transformation: Literal["VERBATIM", "EDITED", "PARAPHRASE", "AI_GENERATED"] = "VERBATIM",
    evidence_status: Literal["VERIFIED", "USER_SUPPLIED", "UNVERIFIED", "CONFLICT"] = "USER_SUPPLIED",
    direction: Literal["editorial", "statement", "contextual"] = "editorial",
    graphic_mode: Literal["auto", "hidden"] = "auto",
    graphic_variant: str = "default",
    text_scale: float = Field(default=1.0, ge=0.8, le=1.0),
    vertical_position: Literal["upper", "center", "lower"] = "center",
    palette: PaletteInput | None = None,
    lines: list[str] | None = Field(default=None, description="Explicit line breaks with no fixed limit."),
    styles: list[StyleRange] | None = Field(default=None, max_length=64),
    alt_text: str = Field(default="", max_length=400),
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
            "produced": produced,
            "filename": f"quote-card-{preview.svg_sha256[:8]}.svg" if produced else None,
            "mime_type": "image/svg+xml",
        }
    )
    summary = _summary(result)
    summary.update({"produced": result.produced, "filename": result.filename, "mime_type": result.mime_type})
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(summary, ensure_ascii=False, indent=2))],
        structuredContent=result.model_dump(mode="json"),
        isError=False,
    )


@mcp.tool(
    name="quote_card_builder_open_editor",
    title="Open Quote Card Builder",
    description=(
        "Use this when the user selects Quote Card Builder or asks to create, test, or open a "
        "quote card. This is the workflow's only public tool and opens the interactive inline "
        "editor. If Quote, Attribution, Palette, and Direction are known, call it once. If a "
        "choice is missing, ask for it with these exact labels: 1. Quote; 2. Visible attribution "
        "or none; 3. Palette, neutral profile or custom; 4. Direction, Editorial, Poster, or "
        "Frame. The third item is the palette, never tone or mood. Do not use image generation, "
        "do not create SVG, PNG, HTML, or files directly in chat, do not look for a local editor, "
        "and do not say the plugin is unavailable. Do not choose values for the user. Call this "
        "tool exactly once and do not call preview_quote_card or produce_quote_card first: the UI "
        "handles later updates and production. It does not save, publish, or modify external data."
    ),
    annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False),
    meta={
        "ui": {"resourceUri": QUOTE_CARD_PREVIEW_RESOURCE, "visibility": ["model"]},
        "openai/outputTemplate": QUOTE_CARD_PREVIEW_RESOURCE,
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
    direction: Literal["editorial", "statement", "contextual"] = Field(
        title="4. Direction",
        description=(
            "Fourth explicit user choice: editorial for Editorial, statement for Poster, and "
            "contextual for Frame. Do not accept minimal or generic labels."
        ),
    ),
    format: Literal["4x5", "1x1"] = Field(
        default="4x5",
        title="Initial format",
        description="Optional initial format: 4x5 portrait or 1x1 square.",
    ),
    palette: PaletteInput | None = Field(
        default=None,
        title="Custom palette colors",
        description="Required only when 3. Palette is custom; includes a name and four colors.",
    ),
) -> PreviewQuoteCardOutput:
    """Render the initial snapshot once; the widget handles later data calls."""
    if profile_mode == "custom" and palette is None:
        raise ValueError(
            "A custom palette requires a name and primary, accent, background, and text colors."
        )
    request = PreviewQuoteCardInput(
        text=text,
        format=format,
        attribution=attribution,
        transformation="VERBATIM",
        evidence_status="USER_SUPPLIED",
        direction=direction,
        graphic_mode="auto",
        graphic_variant="default",
        text_scale=1.0,
        vertical_position="center",
        palette=palette.model_dump(mode="json") if profile_mode == "custom" and palette else None,
        lines=None,
        styles=None,
        alt_text="",
        output_image=False,
    )
    result = _render_request(request, profile_mode)
    structured = result.model_dump(mode="json")
    return CallToolResult(
        content=[
            TextContent(
                type="text",
                text=json.dumps(_summary(result), ensure_ascii=False, indent=2),
            )
        ],
        structuredContent=structured,
        isError=False,
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

    mcp.settings.host = args.host
    mcp.settings.port = args.port
    if args.transport == "streamable-http":
        # FastMCP enables DNS rebinding protection while the module is
        # constructed with its local default host. Reconfigure it explicitly
        # for the deployed HTTP origin instead of inheriting localhost-only
        # values. Cloud Run injects the service hostname at deploy time.
        configure_http_transport_security()
    mcp.run(transport=args.transport)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
