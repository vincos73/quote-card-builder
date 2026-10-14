"""Portable MCP Apps UI for the Quote Card Builder preview tool."""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from urllib.parse import urlsplit


QUOTE_CARD_APP_VERSION = "v1.58"
QUOTE_CARD_PREVIEW_RESOURCE = "ui://quote-card-builder/preview/v1.58.html"
QUOTE_CARD_WORKSPACE_RESOURCE = "ui://quote-card-builder/workspace/v1.58.html"
QUOTE_CARD_LEGACY_PREVIEW_RESOURCES = (
    "ui://quote-card-builder/preview/v1.57.html",
    "ui://quote-card-builder/preview/v1.56.html",
    "ui://quote-card-builder/preview/v1.55.html",
    "ui://quote-card-builder/preview/v1.26.html",
    "ui://quote-card-builder/preview/v1.27.html",
    "ui://quote-card-builder/preview/v1.28.html",
    "ui://quote-card-builder/preview/v1.29.html",
    "ui://quote-card-builder/preview/v1.30.html",
    "ui://quote-card-builder/preview/v1.31.html",
    "ui://quote-card-builder/preview/v1.32.html",
    "ui://quote-card-builder/preview/v1.33.html",
    "ui://quote-card-builder/preview/v1.34.html",
    "ui://quote-card-builder/preview/v1.35.html",
    "ui://quote-card-builder/preview/v1.36.html",
    "ui://quote-card-builder/preview/v1.37.html",
    "ui://quote-card-builder/preview/v1.38.html",
    "ui://quote-card-builder/preview/v1.39.html",
    "ui://quote-card-builder/preview/v1.40.html",
    "ui://quote-card-builder/preview/v1.41.html",
    "ui://quote-card-builder/preview/v1.42.html",
    "ui://quote-card-builder/preview/v1.43.html",
    "ui://quote-card-builder/preview/v1.44.html",
    "ui://quote-card-builder/preview/v1.45.html",
    "ui://quote-card-builder/preview/v1.46.html",
    "ui://quote-card-builder/preview/v1.47.html",
    "ui://quote-card-builder/preview/v1.48.html",
    "ui://quote-card-builder/preview/v1.49.html",
    "ui://quote-card-builder/preview/v1.50.html",
    "ui://quote-card-builder/preview/v1.51.html",
    "ui://quote-card-builder/preview/v1.52.html",
    "ui://quote-card-builder/preview/v1.53.html",
    "ui://quote-card-builder/preview/v1.54.html",
)
QUOTE_CARD_PREVIEW_MIME_TYPE = "text/html;profile=mcp-app"
QUOTE_CARD_PREVIEW_DOMAIN = "https://quote-card-builder-mcp-960066178304.europe-west8.run.app"
QUOTE_CARD_DOWNLOAD_REDIRECT_DOMAINS = (
    "https://oaisdmntpritalynorth.blob.core.windows.net",
    "https://oaisdmntprnortheu.blob.core.windows.net",
    "https://oaisdmntprpolandcentral.blob.core.windows.net",
)
ASSET_DIR = Path(__file__).resolve().parents[1] / "assets" / "mcp-editor"
BRAND_ASSET_DIR = Path(__file__).resolve().parents[1] / "assets" / "card-editor"


def _brand_data_uri(filename: str, mime_type: str) -> str:
    """Return one approved brand asset as a self-contained data URI."""
    payload = (BRAND_ASSET_DIR / filename).read_bytes()
    return f"data:{mime_type};base64," + base64.b64encode(payload).decode("ascii")


def _embedded_font_faces() -> str:
    """Embed the canonical Quote Card Builder interface typography."""
    return "\n".join(
        (
            f'@font-face{{font-family:"QCB Barlow";src:url("{_brand_data_uri("fonts/Barlow-Regular-latin.woff2", "font/woff2")}") format("woff2");font-style:normal;font-weight:400;font-display:swap}}',
            f'@font-face{{font-family:"QCB Barlow";src:url("{_brand_data_uri("fonts/Barlow-Bold-latin.woff2", "font/woff2")}") format("woff2");font-style:normal;font-weight:700;font-display:swap}}',
        )
    )


def _remote_export_origin() -> str:
    """Return the configured public origin as a validated HTTPS origin."""
    value = os.environ.get("QCB_PUBLIC_ORIGIN", QUOTE_CARD_PREVIEW_DOMAIN).rstrip("/")
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
        raise ValueError("QCB_PUBLIC_ORIGIN must be a plain HTTPS origin")
    return value


def quote_card_preview_html(*, workspace: bool = False) -> str:
    """Return the self-contained editor component used by compatible hosts."""
    html = r'''<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Quote Card Builder</title>
    <style>
      __QCB_FONT_FACES__
      * { box-sizing:border-box; }
      html { min-width:320px; background:var(--deep); scrollbar-color:var(--lavender) var(--deep); }
      body { min-width:320px; margin:0; padding:0; background:var(--deep); color:var(--lavender-light); font-size:14px; line-height:1.4; }
      button, input, select, textarea { font:inherit; }
      button { cursor:pointer; }
      .shell { display:grid; gap:0; border:1px solid var(--seam-strong); background:var(--chrome); }
      .app-header { display:flex; align-items:center; justify-content:space-between; gap:16px; min-height:68px; padding:14px 18px; border-bottom:1px solid var(--seam); background:var(--deep); }
      .product-heading { min-width:0; }
      .product-title { display:block; width:min(390px,70vw); height:auto; }
      .product-byline { display:flex; align-items:center; gap:6px; margin-top:7px; color:var(--lavender); font-family:var(--ui); font-size:10px; font-weight:400; letter-spacing:.08em; }
      .product-byline img { display:block; width:92px; height:auto; }
      .version-badge { align-self:flex-start; margin-top:2px; color:var(--signal); font-family:var(--mono); font-size:9px; letter-spacing:.05em; text-transform:uppercase; white-space:nowrap; }
      .form { display:grid; gap:0; }
      fieldset { display:grid; gap:10px; margin:0; padding:14px; border:0; border-bottom:1px solid var(--seam); background:var(--chrome); }
      legend { float:left; width:100%; margin:0 0 2px; padding:0; color:var(--lavender); font-family:var(--mono); font-size:10px; font-weight:500; letter-spacing:.045em; text-transform:uppercase; }
      fieldset > legend + * { clear:both; }
      label { display:grid; gap:6px; color:var(--lavender-light); font-family:var(--mono); font-size:10px; font-weight:500; letter-spacing:.02em; text-transform:uppercase; }
      input, select, textarea, .editor { width:100%; min-height:38px; padding:9px 10px; border:1px solid var(--seam-strong); border-radius:0; background:var(--deep); color:var(--lavender-light); }
      textarea { resize:vertical; }
      input::placeholder, .editor:empty::before { color:var(--lavender); opacity:.88; }
      .editor { min-height:104px; outline:none; overflow:visible; overflow-wrap:anywhere; white-space:pre-wrap; font-family:var(--ui); font-size:16px; line-height:1.45; caret-color:var(--signal); text-transform:none; }
      .editor-line { display:block; min-height:1.45em; }
      .editor:empty::before { content:attr(data-placeholder); pointer-events:none; }
      .editor .style-bold { font-weight:700; }
      .editor .style-italic { font-style:italic; }
      .editor .style-underline { text-decoration:underline; text-decoration-thickness:2px; text-underline-offset:3px; }
      .editor .style-accent { color:var(--signal); }
      .editor .style-highlight { background:var(--signal); color:var(--ink); }
      .editor .style-outline { color:transparent; -webkit-text-stroke:.6px var(--lavender-light); }
      input:focus, select:focus, textarea:focus, .editor:focus, button:focus-visible { border-color:var(--signal); outline:2px solid var(--signal); outline-offset:2px; }
      .grid-2 { display:grid; gap:10px; grid-template-columns:repeat(2,minmax(0,1fr)); }
      .palette { display:grid; gap:8px; }
      .palette-row { display:grid; grid-template-columns:minmax(84px,.7fr) 52px minmax(92px,1fr); align-items:center; gap:8px; padding:7px 8px; border:1px solid var(--seam); background:var(--deep); }
      .palette-row > span { color:var(--lavender-light); font-family:var(--mono); font-size:9px; text-transform:uppercase; }
      .palette-row input[type=color] { width:52px; height:34px; padding:3px; }
      .palette-row input[type=text] { min-height:34px; padding:7px 8px; font-family:var(--mono); font-size:11px; text-transform:uppercase; }
      .palette-actions { display:grid; grid-template-columns:minmax(0,1fr) auto; align-items:end; gap:8px; }
      .palette-actions button, .variation button { min-height:38px; padding:8px 10px; border:1px solid var(--seam-strong); border-radius:0; background:var(--deep); color:var(--lavender-light); font-family:var(--mono); font-size:9px; font-weight:700; text-transform:uppercase; }
      .palette-actions button:hover, .variation button:hover { border-color:var(--signal); color:var(--signal); }
      .palette-help { margin:0; color:var(--lavender); font-size:11px; line-height:1.35; }
      .toolbar { display:flex; align-items:center; min-height:36px; border:1px solid var(--seam-strong); border-bottom:0; background:var(--deep); }
      .toolbar button { min-width:38px; height:35px; padding:0 10px; border:0; border-right:1px solid var(--seam); border-radius:0; background:transparent; color:var(--lavender-light); }
      .toolbar button:hover { background:var(--raised); color:var(--lavender-light); }
      .toolbar button[aria-pressed=true] { background:var(--raised); color:var(--signal); }
      .toolbar-status { margin-left:auto; padding:0 9px; color:var(--lavender); font-family:var(--mono); font-size:9px; text-align:right; text-transform:uppercase; }
      .editor-label { display:flex; align-items:center; justify-content:space-between; }
      .editor-label button { padding:2px 0; border:0; background:none; color:var(--signal); font-family:var(--mono); font-size:9px; text-transform:uppercase; }
      .style-picker { display:grid; gap:6px; grid-template-columns:repeat(2,minmax(0,1fr)); }
      .style-picker button { min-height:48px; padding:8px 7px; border:1px solid var(--seam-strong); border-radius:0; background:var(--deep); color:var(--lavender-light); font-family:var(--mono); font-size:9px; font-weight:700; text-transform:uppercase; }
      .style-picker button:hover { background:var(--raised); }
      .style-picker button[aria-pressed=true] { border-color:var(--signal); background:var(--raised); color:var(--signal); }
      .style-picker .plain-style { grid-column:1 / -1; min-height:38px; color:var(--lavender); }
      .variation { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)) auto; align-items:center; gap:6px; }
      .variation[hidden] { display:none; }
      .variation output { min-width:62px; text-align:right; }
      .range-row { display:flex; align-items:center; justify-content:space-between; }
      output { color:var(--signal); font-family:var(--mono); font-size:10px; font-variant-numeric:tabular-nums; }
      input[type=range] { min-height:auto; margin:4px 0; padding:0; border:0; accent-color:var(--signal); }
      .actions { display:grid; grid-template-columns:minmax(140px,.72fr) minmax(190px,1fr); gap:8px; padding:10px 14px; border-bottom:1px solid var(--seam); background:var(--deep); }
      .actions button { display:grid; align-content:center; gap:2px; min-height:52px; padding:8px 12px; border-radius:0; text-align:left; }
      .action-title { font-family:var(--ui); font-size:15px; font-weight:700; line-height:1.1; }
      .action-detail { font-family:var(--mono); font-size:10px; font-weight:400; letter-spacing:.025em; line-height:1.2; }
      button.secondary { border:1px solid var(--seam-strong); background:transparent; color:var(--lavender-light); }
      button.secondary .action-detail { color:var(--lavender); }
      button.secondary:hover { border-color:var(--lavender); background:var(--raised); }
      button.primary { border:1px solid var(--signal); background:var(--signal); color:var(--ink); }
      button.primary:hover .action-title { text-decoration:underline; text-decoration-thickness:1px; text-underline-offset:3px; }
      button:disabled { cursor:wait; opacity:.58; }
      .status { min-height:38px; padding:11px 14px; border-bottom:1px solid var(--seam); background:var(--deep); color:var(--lavender); font-family:var(--mono); font-size:10px; }
      .preview { display:grid; gap:10px; justify-items:center; min-height:190px; padding:18px; background:var(--concrete); color:var(--paper); }
      .preview .svg-preview { display:block; width:100%; max-width:min(100%,420px); max-height:620px; overflow:hidden; border:1px solid var(--line); border-radius:0; background:#fff; }
      .preview .svg-preview[hidden] { display:none; }
      .preview .svg-preview svg { display:block; width:100%; height:auto; max-height:618px; }
      .qcb-preview-caption { color:var(--paper); font-family:var(--mono); font-size:9px; text-align:center; text-transform:uppercase; }
      .errors { padding:10px 14px; border-top:1px solid var(--danger); background:var(--deep); color:var(--danger); font-size:12px; }
      .errors[hidden] { display:none; }
      .delivery { display:grid; grid-template-columns:1fr auto; align-items:center; gap:12px; padding:13px 14px; border-bottom:1px solid var(--seam); background:var(--deep); }
      .delivery[hidden] { display:none; }
      .delivery strong { color:var(--signal); font-family:var(--mono); font-size:10px; font-weight:500; text-transform:uppercase; }
      .delivery-actions { display:flex; align-items:center; justify-content:flex-end; gap:8px; flex-wrap:wrap; }
      .direct-download { min-height:38px; padding:9px 12px; border:1px solid var(--seam-strong); background:transparent; color:var(--lavender-light); font-family:var(--mono); font-size:9px; text-decoration:underline; text-underline-offset:3px; }
      .direct-download[hidden] { display:none; }
      .hint { margin:0; color:var(--lavender); font-size:11px; line-height:1.35; }
      .ribbon-proposals { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:6px; }
      .ribbon-proposal { min-width:0; padding:5px; border:1px solid var(--seam-strong); background:var(--deep); color:var(--lavender-light); text-align:left; }
      .ribbon-proposal[aria-pressed=true] { border-color:var(--signal); }
      .ribbon-thumb { display:grid; place-items:center; aspect-ratio:4/5; overflow:hidden; }
      .ribbon-thumb img { display:block; width:100%; height:100%; object-fit:contain; }
      .ribbon-proposal > span:last-child { display:block; margin-top:5px; font-family:var(--mono); font-size:10px; overflow-wrap:anywhere; }
      .ribbon-actions { display:flex; flex-wrap:wrap; gap:6px; }
      .ribbon-actions button { min-height:38px; padding:7px 10px; border:1px solid var(--seam-strong); background:var(--deep); color:var(--lavender-light); font-family:var(--mono); font-size:10px; }
      .selection-size { display:grid; grid-template-columns:minmax(0,1fr) 90px auto; align-items:end; gap:8px; }
      .size-field { display:grid; grid-template-columns:minmax(0,1fr) auto; align-items:end; gap:6px; }
      .card-library { padding:14px; border-bottom:1px solid var(--seam); }
      .card-library summary { cursor:pointer; color:var(--lavender); font-family:var(--mono); font-size:10px; text-transform:uppercase; }
      .library-content { display:grid; gap:10px; padding-top:12px; }
      .saved-base { display:grid; gap:6px; padding:9px; border:1px solid var(--seam-strong); }
      .saved-base strong { font-family:var(--mono); font-size:11px; }
      .reuse-form { display:grid; gap:10px; }
      .warnings-panel { padding:12px 14px; border-top:1px solid var(--seam); background:var(--deep); }
      .warnings-panel h2 { margin:0; color:var(--lavender-light); font-family:var(--mono); font-size:11px; font-weight:500; }
      .warnings-panel ul { margin:8px 0 0; padding-left:18px; color:var(--lavender); font-size:11px; }
      .warnings-panel li { margin:4px 0; }
      .ribbon-controls[hidden], .ribbon-proposals[hidden], .selection-size[hidden], .reuse-form[hidden], .warnings-panel[hidden], .legacy-composition[hidden], .ribbon-actions[hidden], #projectJsonLabel[hidden] { display:none; }
      ::selection { background:var(--signal); color:var(--ink); }
      @media (max-width:560px) {
        .app-header { align-items:flex-start; gap:10px; min-height:0; }
        .grid-2 { grid-template-columns:1fr; }
        .palette-row { grid-template-columns:minmax(76px,.65fr) 48px minmax(86px,1fr); }
        .toolbar-status { max-width:46%; }
        .style-picker button { min-height:48px; }
        .actions { grid-template-columns:1fr; }
      }
      @media (max-width:420px) {
        .product-title { width:min(300px,70vw); }
        .version-badge { font-size:8px; }
      }
      __QCB_HOST_THEME__
    </style>
  </head>
  <body data-qcb-workspace="__QCB_WORKSPACE_MODE__">
    <main class="shell" aria-labelledby="title" data-version="__QCB_APP_VERSION__" data-workspace="__QCB_WORKSPACE_MODE__">
      <header class="app-header">
        <div class="product-heading"><img class="product-title" id="title" src="__QCB_PRODUCT_WORDMARK__" alt="Quote Card Builder"><div class="product-byline"><span>by</span><img src="__QCB_VINCOS_LOCKUP__" alt="Vincos"></div></div>
        <div class="version-badge" aria-label="Quote Card Builder version __QCB_APP_VERSION__">__QCB_APP_VERSION__</div>
      </header>
      <section class="workspace-bar" data-workspace-only aria-label="Workspace draft status">
        <div><strong>Quote card workspace</strong><span id="workspaceStatus" role="status">Draft recovery is starting…</span></div>
        <button id="newCard" type="button">New card</button>
      </section>
      <form class="form" id="form">
        <fieldset>
          <legend>Content &amp; formatting</legend>
          <div class="editor-label"><span id="quote-label">Quote</span><button id="rebalance" type="button">Rebalance line breaks</button></div>
          <div>
            <div class="toolbar" id="toolbar" role="toolbar" aria-label="Selected text formatting">
              <button type="button" data-style="bold" aria-label="Bold" title="Bold"><strong>B</strong></button>
              <button type="button" data-style="italic" aria-label="Italic" title="Italic"><em>I</em></button>
              <button type="button" data-style="underline" aria-label="Underline" title="Underline"><u>U</u></button>
              <button type="button" data-style="accent" aria-label="Accent" title="Accent">A</button>
              <button type="button" data-style="outline" aria-label="Outline" title="Outline">O</button>
              <button type="button" data-style="highlight" aria-label="Highlight" title="Highlight">H</button>
              <span class="toolbar-status" id="toolbarStatus">Select part of the quote</span>
            </div>
            <div id="text" class="editor" contenteditable="true" role="textbox" aria-labelledby="quote-label" aria-multiline="true" data-placeholder="Write the quote to display"></div>
          </div>
          <div id="selectionSizeControl" class="selection-size ribbon-actions" hidden>
            <span class="hint">Selected words · relative size</span>
            <label>Percent <input id="selectionSize" type="number" min="50" max="250" step="5" value="100"></label>
            <button id="selectionSizeApply" type="button">Apply</button>
          </div>
          <p class="hint" id="demoHelper" data-demo-only hidden>È un esempio: sostituiscilo con la tua frase.</p>
          <label data-workspace-only>Attribution choice <select id="attributionDecision"><option value="">Choose…</option><option value="named">Name or source</option><option id="demoNoneOption" value="none" selected>No attribution</option></select></label>
          <label>Attribution <textarea id="attribution" maxlength="160" rows="2" placeholder="Name or leave blank"></textarea></label>
          <p class="hint">Select words in the quote and use B, I, U, A, O, or H. The canonical renderer preserves the selected ranges.</p>
        </fieldset>

        <fieldset>
          <legend>Style</legend>
          <div class="style-picker" id="stylePicker" role="group" aria-label="Choose a visual style">
            <button type="button" data-style-choice="blocks" aria-pressed="true">Blocks</button>
            <button type="button" data-style-choice="cutouts" aria-pressed="false">Cutouts</button>
            <button type="button" data-style-choice="constellations" aria-pressed="false">Constellations</button>
            <button type="button" data-style-choice="gradient" aria-pressed="false">Gradient</button>
            <button type="button" data-style-choice="ribbons" aria-pressed="false">Nastri</button>
            <button class="plain-style" type="button" data-style-choice="plain" aria-pressed="false">Hide pattern</button>
          </div>
          <p class="hint" id="styleHint">Blocks selected. Vary the pattern to explore another deterministic composition.</p>
          <div class="variation" id="patternVariation">
            <button type="button" id="patternPrevious">Previous</button>
            <button type="button" id="patternNext">Vary pattern</button>
            <output id="patternSeed" aria-live="polite">Seed 0</output>
          </div>
        </fieldset>

        <fieldset id="ribbonCompositions" class="ribbon-controls" hidden>
          <legend>Nastri compositions</legend>
          <p class="hint" id="ribbonSource"></p>
          <div id="ribbonProposals" class="ribbon-proposals" aria-label="Choose a Nastri composition"></div>
          <div class="ribbon-actions"><button id="ribbonVariations" type="button">New demo variations</button></div>
        </fieldset>

        <fieldset>
          <legend>Composition</legend>
          <label for="format">Format <select id="format"><option value="4x5" selected>4:5 portrait</option><option value="1x1">1:1 square</option><option value="9x16">9:16 story</option></select></label>
          <div id="legacyScale" class="legacy-composition"><div class="range-row"><label for="scale">Scale from maximum</label><output id="scaleValue" for="scale">100%</output></div>
          <input id="scale" type="range" min="80" max="100" value="100" step="1"></div>
          <div id="legacyPosition" class="range-row legacy-composition"><label for="position">Vertical position</label><select id="position"><option value="upper">Upper</option><option value="center" selected>Center</option><option value="lower">Lower</option></select></div>
          <div id="ribbonSizes" class="grid-2 ribbon-controls ribbon-actions" hidden>
            <div class="size-field"><label>Quote size · card px <input id="quoteFontSize" type="number" min="8" max="720" step="1" placeholder="Auto"></label><button id="quoteSizeAuto" type="button">Auto</button></div>
            <div class="size-field"><label>Author size · card px <input id="authorFontSize" type="number" min="8" max="720" step="1" placeholder="Auto"></label><button id="authorSizeAuto" type="button">Auto</button></div>
          </div>
          <p id="ribbonSizeNote" class="hint ribbon-controls" hidden></p>
        </fieldset>
        <details class="card-library" id="cardLibrary">
          <summary>Saved bases &amp; project JSON</summary>
          <div class="library-content">
            <p class="hint">Bases stay on this device when storage is available. Export a project JSON to reuse it in another browser; there is no account sync.</p>
            <label>Base name <input id="baseName" maxlength="80" placeholder="e.g. My Nastri cards"></label>
            <div class="ribbon-actions"><button id="saveBase" type="button">Save Nastri base</button><button id="exportProject" type="button">Export project JSON</button><button id="importProject" type="button">Import project JSON</button></div>
            <input id="projectFile" type="file" accept="application/json,.json" hidden>
            <label id="projectJsonLabel" hidden>Project JSON <textarea id="projectJson" rows="6" spellcheck="false"></textarea></label>
            <div id="projectJsonActions" class="ribbon-actions" hidden><button id="copyProjectJson" type="button">Copy JSON</button><a id="projectDownload" class="direct-download" download="quote-card-project.json" hidden>Download JSON</a></div>
            <p class="hint" id="baseFeedback" role="status"></p>
            <div id="savedBases"></div>
            <div id="reuseForm" class="reuse-form" hidden>
              <strong id="reuseTitle"></strong>
              <label>Quote <textarea id="reuseText" maxlength="600" rows="4"></textarea></label>
              <label>Author · optional <textarea id="reuseAuthor" maxlength="160" rows="2"></textarea></label>
              <div class="ribbon-actions"><button id="reuseConfirm" type="button">Use base</button><button id="reuseCancel" type="button">Cancel</button></div>
            </div>
          </div>
        </details>

        <fieldset>
          <legend>Card palette</legend>
          <label data-workspace-only>Palette choice <select id="paletteDecision"><option id="demoNeutralOption" value="neutral" selected>Neutral palette</option><option value="custom">Custom palette</option></select></label>
          <label>Palette name <input id="paletteName" maxlength="80" value="Initial palette" placeholder="e.g. Personal brand"></label>
          <div class="palette-actions" aria-label="Palette actions">
            <label>Ready palette <select id="palettePreset"><option value="initial">Initial</option><option value="forest">Bosco</option><option value="paper">Carta</option><option value="warm">Calda</option><option value="custom" disabled>Custom</option></select></label>
            <button id="paletteReset" type="button">Reset initial</button>
          </div>
          <div class="palette" id="palette" role="group" aria-label="Card colors">
            <label class="palette-row"><span>Primary</span><input id="primary" type="color" value="#072743" aria-label="Choose primary color"><input id="primaryHex" type="text" value="#072743" maxlength="7" spellcheck="false" aria-label="Primary hexadecimal color"></label>
            <label class="palette-row"><span>Accent</span><input id="accent" type="color" value="#E3F4FF" aria-label="Choose accent color"><input id="accentHex" type="text" value="#E3F4FF" maxlength="7" spellcheck="false" aria-label="Accent hexadecimal color"></label>
            <label class="palette-row"><span>Background</span><input id="background" type="color" value="#FEFDFB" aria-label="Choose background color"><input id="backgroundHex" type="text" value="#FEFDFB" maxlength="7" spellcheck="false" aria-label="Background hexadecimal color"></label>
            <label class="palette-row"><span>Text</span><input id="textColor" type="color" value="#323232" aria-label="Choose text color"><input id="textHex" type="text" value="#323232" maxlength="7" spellcheck="false" aria-label="Text hexadecimal color"></label>
          </div>
          <p class="palette-help" id="paletteHelp">Edit all four card colors. Reset restores the palette received when this editor opened.</p>
        </fieldset>
        <div class="actions" aria-label="Preview and export actions">
          <button class="secondary" id="submit" type="submit"><span class="action-title">Update preview</span><span class="action-detail">Check current changes</span></button>
          <button class="primary" id="produce" type="button"><span class="action-title">Download PNG</span><span class="action-detail">Create and save image</span></button>
        </div>
      </form>
      <div class="status" id="status" role="status" aria-live="polite">Waiting for a quote card.</div>
      <div class="delivery" id="delivery" hidden><strong id="deliveryName">PNG ready</strong><div class="delivery-actions"><a class="direct-download" id="remoteLink" href="#" target="_blank" rel="noopener" hidden>Open PNG download link</a></div></div>
      <section class="preview" aria-label="Quote card preview"><div id="image" class="svg-preview" role="img" aria-label="" hidden></div><div class="qcb-preview-caption" id="meta"></div></section>
      <div class="errors" id="errors" role="alert" hidden></div>
      <section id="warningsPanel" class="warnings-panel" aria-labelledby="warningsTitle" aria-live="polite" hidden><h2 id="warningsTitle">Avvisi · <span id="warningsCount">0</span></h2><ul id="warningsList"></ul></section>
    </main>
    <script>__QCB_HOST_CONTEXT__</script>
    <script>__QCB_TOOL_RESULTS__</script>
    <script>
      const workspaceMode = __QCB_WORKSPACE_MODE__;
      const remoteExportOrigin = __QCB_REMOTE_EXPORT_ORIGIN__;
      let hostState = null;
      const pending = new Map(); let nextId = 1; let hasRendered = false;
      const $ = (id) => document.getElementById(id);
      const form = $("form"), text = $("text"), attribution = $("attribution"), attributionDecision = $("attributionDecision"), paletteDecision = $("paletteDecision");
      const direction = { value: "editorial" }, paletteName = $("paletteName"), palette = $("palette"), palettePreset = $("palettePreset");
      const format = $("format"), scale = $("scale"), scaleValue = $("scaleValue"), position = $("position");
      const quoteFontSize = $("quoteFontSize"), authorFontSize = $("authorFontSize"), selectionSize = $("selectionSize");
      let ribbonComposition = null, ribbonCandidates = [], ribbonProposalSource = null, ribbonPreviews = [], ribbonLayout = null;
      let pendingReuseComposition = null, savedSelection = null, reuseBaseId = null, reuseMode = "card";
      let projectDownloadUrl = "";
      const submit = $("submit"), produce = $("produce"), status = $("status"), image = $("image"), meta = $("meta"), errors = $("errors"), toolbarStatus = $("toolbarStatus");
      const delivery = $("delivery"), deliveryName = $("deliveryName"), remoteLink = $("remoteLink");
      const allowedDownloadOrigins = new Set(__QCB_REDIRECT_ORIGINS__);
      let styles = []; let lastTextValue = ""; let resizeFrame = 0; let deliveryUrl = ""; let deliveryFileId = ""; let deliveryFilename = ""; let deliveryFile = null; let preparedSignature = ""; let hostCapabilities = {}; let previewTimer = 0; let previewSequence = 0; let graphicSeed = 0; let editRevision = 0; let actionSequence = 0; let demoChoices = false; let demoAttributionChoice = false; let demoPaletteChoice = false; let initialContentObserved = false; let hostInitialized = false; let initialAliasGracePassed = false; let draftTransformation = "VERBATIM"; let draftEvidenceStatus = "USER_SUPPLIED"; let draftAltText = ""; let draftUpdateStatus = ""; let appliedUpdateFingerprints = []; let lastAliasInputSignature = null; let lastAliasResultSignature = null;
      const canonicalNeutralPalette = { name:"Initial palette", colors:{ primary:"#072743", accent:"#E3F4FF", background:"#FEFDFB", text:"#323232" } };
      let paletteInitial = { name:canonicalNeutralPalette.name, colors:{ ...canonicalNeutralPalette.colors } };
      const styleOptions = {
        blocks:{ direction:"editorial", variant:"cover", label:"Blocks" },
        cutouts:{ direction:"editorial", variant:"cutouts", label:"Cutouts" },
        constellations:{ direction:"contextual", variant:"constellations", label:"Constellations" },
        gradient:{ direction:"editorial", variant:"gradient", label:"Gradient" },
        ribbons:{ direction:"editorial", variant:"default", grammar:"ribbons", label:"Nastri" },
        plain:{ direction:"editorial", variant:"default", hidden:true, label:"Hide pattern" },
      };
      const palettePresets = {
        forest:{ name:"Bosco", colors:{ primary:"#173D35", accent:"#C8E0CC", background:"#F6F8F0", text:"#173D35" } },
        paper:{ name:"Carta", colors:{ primary:"#072743", accent:"#E3F4FF", background:"#FEFDFB", text:"#323232" } },
        warm:{ name:"Calda", colors:{ primary:"#5A2C2A", accent:"#E8B4A8", background:"#FFF8F2", text:"#332423" } },
      };
      const paletteFields = { primary:["primary","primaryHex"], accent:["accent","accentHex"], background:["background","backgroundHex"], text:["textColor","textHex"] };
      const demoHelper = $("demoHelper"), demoNoneOption = $("demoNoneOption"), demoNeutralOption = $("demoNeutralOption");
      const demoQuote = "Le idee migliori meritano di essere condivise.";
      const demoQuoteLayout = "Le idee migliori\nmeritano\ndi essere\ncondivise.";
      function demoQuoteStyles() {
        const firstBreak = demoQuoteLayout.indexOf("\n");
        const meritanoStart = demoQuoteLayout.indexOf("meritano");
        const diStart = demoQuoteLayout.indexOf("di essere");
        const condiviseStart = demoQuoteLayout.indexOf("condivise");
        return [
          {start:0, end:firstBreak, type:"bold"},
          {start:meritanoStart, end:meritanoStart + "meritano".length, type:"italic"},
          {start:diStart, end:diStart + "di essere".length, type:"italic"},
          {start:condiviseStart, end:demoQuoteLayout.length, type:"highlight"},
        ];
      }
      const hexPattern = /^#[0-9a-f]{6}$/i;
      function pointLength(value) { return Array.from(String(value || "")).length; }
      function cpOffset(value, utf16Index) { return pointLength(String(value || "").slice(0, utf16Index)); }
      function normalizeStyles(value) { const grouped = new Map(); (Array.isArray(value) ? value : []).forEach((item) => { if (!item || !["bold","italic","underline","highlight","accent","outline","size"].includes(item.type) || !Number.isInteger(item.start) || !Number.isInteger(item.end) || item.start >= item.end) return; if (item.type === "size" && (!Number.isFinite(item.scale) || item.scale < .5 || item.scale > 2.5)) return; const key = item.type === "size" ? `size:${item.scale}` : item.type; if (!grouped.has(key)) grouped.set(key, []); grouped.get(key).push({ start:item.start, end:item.end, type:item.type, ...(item.type === "size" ? {scale:item.scale} : {}) }); }); const merged = []; grouped.forEach((ranges) => { ranges.sort((first, second) => first.start - second.start || first.end - second.end); ranges.forEach((range) => { const previous = merged.at(-1); if (previous?.type === range.type && previous.scale === range.scale && range.start <= previous.end) previous.end = Math.max(previous.end, range.end); else merged.push({ ...range }); }); }); return merged.sort((first, second) => first.start - second.start || first.end - second.end || first.type.localeCompare(second.type)); }
      const blockTags = new Set(["DIV", "P", "LI", "BLOCKQUOTE", "PRE"]);
      function isPlaceholderBreak(parent, child) { return parent?.nodeType === Node.ELEMENT_NODE && blockTags.has(parent.tagName) && parent.childNodes.length === 1 && child?.nodeType === Node.ELEMENT_NODE && child.tagName === "BR"; }
      function blockSeparatorBefore(parent, index) { if (index <= 0) return ""; const child = parent.childNodes[index], previous = parent.childNodes[index - 1]; if (child?.nodeType !== Node.ELEMENT_NODE || !blockTags.has(child.tagName)) return ""; return previous?.nodeType === Node.ELEMENT_NODE && previous.tagName === "BR" ? "" : "\n"; }
      function serializeEditorNode(node, boundaryNode, boundaryOffset) {
        if (node === boundaryNode) {
          if (node.nodeType === Node.TEXT_NODE) return { value: node.data.slice(0, boundaryOffset), hit: true };
          let value = "";
          for (let index = 0; index < Math.min(boundaryOffset, node.childNodes.length); index += 1) {
            const child = node.childNodes[index];
            value += blockSeparatorBefore(node, index);
            if (!isPlaceholderBreak(node, child)) value += serializeEditorNode(child, null, 0).value;
          }
          value += blockSeparatorBefore(node, Math.min(boundaryOffset, node.childNodes.length));
          return { value, hit: true };
        }
        if (node.nodeType === Node.TEXT_NODE) return { value: node.data, hit: false };
        if (node.nodeType === Node.ELEMENT_NODE && node.tagName === "BR") return { value: "\n", hit: false };
        let value = "";
        for (let index = 0; index < node.childNodes.length; index += 1) {
          const child = node.childNodes[index];
          // Browsers encode the first Enter as a block after a text node
          // (<div>second line</div>). The newline belongs before that block;
          // adding it after the block drops the first line break entirely.
          value += blockSeparatorBefore(node, index);
          if (isPlaceholderBreak(node, child)) continue;
          const result = serializeEditorNode(child, boundaryNode, boundaryOffset);
          value += result.value;
          if (result.hit) return { value, hit: true };
        }
        return { value, hit: false };
      }
      function textValue() {
        // innerText/Range.toString() disagree about newlines inside contenteditable
        // blocks. Use one canonical DOM walk for both the payload and selections,
        // otherwise a selection on line 3 can be serialized as an earlier word.
        // Keep terminal newlines: pressing Enter at the end creates the next
        // authored row even before the user types its first character.
        const value = serializeEditorNode(text, null, 0).value;
        return String(value || "").replace(/\r\n?/g, "\n").replace(/\u00a0/g, " ");
      }
      function editorOffset(container, offset) { if (!container || !text.contains(container.nodeType === 3 ? container.parentNode : container)) return null; return pointLength(serializeEditorNode(text, container, offset).value); }
      function selectionRange() {
        const current = window.getSelection();
        if (!current || !current.rangeCount) return null;
        const start = editorOffset(current.anchorNode, current.anchorOffset);
        const end = editorOffset(current.focusNode, current.focusOffset);
        if (start === null || end === null) return null;
        return start <= end ? { start, end } : { start:end, end:start };
      }
      function selection() {
        const range = selectionRange();
        return range && range.start < range.end ? range : null;
      }
      function utf16Offset(value, codePointOffset) { return Array.from(String(value || "")).slice(0, codePointOffset).join("").length; }
      function editorPoint(offset) {
        // Map the canonical editor offset back onto the block-based DOM. A
        // newline is part of the text model but is not a text node, so a
        // plain TreeWalker would shift every selection after the first row.
        const target = Math.max(0, pointLength(textValue()) > offset ? offset : pointLength(textValue()));
        let cursor = 0, lastText = null;
        const findIn = (node) => {
          if (node.nodeType === Node.TEXT_NODE) {
            lastText = node;
            const length = pointLength(node.data);
            if (target <= cursor + length) return { node, offset:utf16Offset(node.data, target - cursor) };
            cursor += length;
            return null;
          }
          if (node.nodeType !== Node.ELEMENT_NODE) return null;
          if (node.tagName === "BR") return null;
          for (const child of node.childNodes) {
            const result = findIn(child);
            if (result) return result;
          }
          return null;
        };
        const children = Array.from(text.childNodes);
        for (let index = 0; index < children.length; index += 1) {
          const child = children[index];
          const separator = blockSeparatorBefore(text, index);
          if (separator) {
            cursor += 1;
            if (target === cursor) {
              const walker = document.createTreeWalker(child, NodeFilter.SHOW_TEXT);
              const firstText = walker.nextNode();
              return firstText ? { node:firstText, offset:0 } : { node:child, offset:0 };
            }
          }
          const result = findIn(child);
          if (result) return result;
        }
        if (lastText) return { node:lastText, offset:lastText.data.length };
        return null;
      }
      function restoreSelection(range) { if (!range) return; const start = editorPoint(range.start), end = editorPoint(range.end); if (!start || !end) return; const next = document.createRange(); next.setStart(start.node, start.offset); next.setEnd(end.node, end.offset); const current = window.getSelection(); current.removeAllRanges(); current.addRange(next); }
      function renderEditor(selectedRange) {
        const value = textValue();
        const lines = value.split("\n");
        const chars = Array.from(value);
        const fragment = document.createDocumentFragment();
        let globalOffset = 0;
        lines.forEach((line, lineIndex) => {
          const lineLength = pointLength(line);
          const block = document.createElement("div");
          block.className = "editor-line";
          if (!line) {
            block.appendChild(document.createElement("br"));
          } else {
            let runStart = 0;
            let previous = "";
            const appendRun = (end, signature) => {
              if (end <= runStart) return;
              const content = chars.slice(globalOffset + runStart, globalOffset + end).join("");
              if (!signature) block.appendChild(document.createTextNode(content));
              else {
                const span = document.createElement("span");
                span.className = signature.split(" ").filter((kind) => !kind.startsWith("size:")).map((kind) => `style-${kind}`).join(" ");
                const size = signature.split(" ").find((kind) => kind.startsWith("size:"));
                if (size) span.style.fontSize = `${Number(size.slice(5))}em`;
                span.textContent = content;
                block.appendChild(span);
              }
            };
            for (let index = 0; index < lineLength; index += 1) {
              const signature = styles.filter((item) => item.start <= globalOffset + index && item.end > globalOffset + index).map((item) => item.type === "size" ? `size:${item.scale}` : item.type).sort().join(" ");
              if (signature !== previous) { appendRun(index, previous); runStart = index; previous = signature; }
            }
            appendRun(lineLength, previous);
          }
          fragment.appendChild(block);
          globalOffset += lineLength + (lineIndex < lines.length - 1 ? 1 : 0);
        });
        text.replaceChildren(fragment);
        restoreSelection(selectedRange);
      }
      function setTextValue(value, selectedRange) { text.textContent = String(value || ""); renderEditor(selectedRange); lastTextValue = textValue(); }
      function scheduleResize() {
        if (resizeFrame) cancelAnimationFrame(resizeFrame);
        resizeFrame = requestAnimationFrame(() => {
          const root = document.documentElement;
          const height = Math.ceil(Math.max(root.scrollHeight, root.getBoundingClientRect().height));
          const width = Math.ceil(Math.max(document.body.scrollWidth, root.clientWidth));
          // Keep the portable MCP Apps notification and also notify ChatGPT's
          // host bridge. Desktop clients use the latter to keep dynamically
          // revealed controls inside the iframe's interactive hit area.
          const bridge = window.openai;
          if (typeof bridge?.notifyIntrinsicHeight === "function") {
            try {
              const notification = bridge.notifyIntrinsicHeight(height);
              if (notification?.catch) notification.catch(() => {});
            } catch (_) {}
          }
          window.parent.postMessage({ jsonrpc:"2.0", method:"ui/notifications/size-changed", params:{ width, height } }, "*");
        });
      }
      function overlap(a, b) { return a.start < b.end && a.end > b.start; }
      function remapStylesAcrossWhitespace(oldValue, newValue, currentStyles) {
        const oldChars = Array.from(oldValue), newChars = Array.from(newValue);
        const oldVisible = oldChars.map((char, index) => ({ char, index })).filter((item) => !/\s/.test(item.char));
        const newVisible = newChars.map((char, index) => ({ char, index })).filter((item) => !/\s/.test(item.char));
        if (oldVisible.map((item) => item.char).join("") !== newVisible.map((item) => item.char).join("")) return null;
        return normalizeStyles((currentStyles || []).flatMap((item) => {
          const covered = oldVisible.map((entry, ordinal) => ({ ...entry, ordinal })).filter((entry) => entry.index >= item.start && entry.index < item.end);
          if (!covered.length) return [];
          const first = newVisible[covered[0].ordinal], last = newVisible[covered.at(-1).ordinal];
          return first && last ? [{ ...item, start:first.index, end:last.index + 1 }] : [];
        }));
      }
      function remapStylesAfterEdit(oldValue, newValue, currentStyles) {
        if (oldValue === newValue) return normalizeStyles(currentStyles);
        const whitespaceMapped = remapStylesAcrossWhitespace(oldValue, newValue, currentStyles);
        if (whitespaceMapped) return whitespaceMapped;
        const oldChars = Array.from(oldValue), newChars = Array.from(newValue);
        let prefix = 0;
        while (prefix < oldChars.length && prefix < newChars.length && oldChars[prefix] === newChars[prefix]) prefix += 1;
        let suffix = 0;
        while (suffix < oldChars.length - prefix && suffix < newChars.length - prefix && oldChars[oldChars.length - 1 - suffix] === newChars[newChars.length - 1 - suffix]) suffix += 1;
        const oldEnd = oldChars.length - suffix, newEnd = newChars.length - suffix, delta = newEnd - oldEnd;
        return normalizeStyles((currentStyles || []).flatMap((item) => {
          if (item.end <= prefix) return [item];
          if (item.start >= oldEnd) return [{ ...item, start:item.start + delta, end:item.end + delta }];
          const start = item.start < prefix ? item.start : prefix;
          const end = item.end > oldEnd ? item.end + delta : newEnd;
          return start < end ? [{ ...item, start, end }] : [];
        }));
      }
      function insertAuthoredNewline(value, range) {
        const chars = Array.from(String(value || ""));
        let start = Math.max(0, Math.min(range?.start ?? chars.length, chars.length));
        let end = Math.max(start, Math.min(range?.end ?? start, chars.length));
        // Pressing Enter between words replaces the horizontal separator. If
        // the browser keeps that space beside the new block, editor offsets
        // differ from the whitespace-normalized renderer offsets and the
        // first glyph of the next row inherits the previous row's style.
        if (start === end) {
          while (start > 0 && chars[start - 1] !== "\n" && /\s/.test(chars[start - 1])) start -= 1;
          while (end < chars.length && chars[end] !== "\n" && /\s/.test(chars[end])) end += 1;
        }
        const next = chars.slice(0, start).concat(["\n"], chars.slice(end)).join("");
        return { value:next, range:{ start:start + 1, end:start + 1 } };
      }
      function trimRangeWhitespace(range) { if (!range) return null; const chars = Array.from(textValue()); let start = range.start, end = range.end; while (start < end && /\s/.test(chars[start])) start += 1; while (end > start && /\s/.test(chars[end - 1])) end -= 1; return start < end ? { start, end } : null; }
      function rangeCovered(kind, range) { let cursor = range.start; normalizeStyles(styles).filter((item) => item.type === kind).forEach((item) => { if (item.end <= cursor || item.start > cursor) return; cursor = Math.max(cursor, item.end); }); return cursor >= range.end; }
      function subtractRange(item, range) { if (!overlap(item, range)) return [item]; const next = []; if (item.start < range.start) next.push({ ...item, end:range.start }); if (item.end > range.end) next.push({ ...item, start:range.end }); return next; }
      function applySelectionSize() {
        const range = trimRangeWhitespace(selection() || savedSelection);
        if (!range || !isRibbonStyle()) { toolbarStatus.textContent = "Select words before changing their size"; return; }
        const relative = Number(selectionSize.value) / 100;
        if (!Number.isFinite(relative) || relative < .5 || relative > 2.5) { toolbarStatus.textContent = "Selected text size uses 50–250%"; return; }
        if (!quoteFontSize.value) {
          const fitted = Number(ribbonLayout?.font_size);
          if (!Number.isFinite(fitted) || fitted < 8 || fitted > 720) { toolbarStatus.textContent = "The quote size is not available yet"; return; }
          quoteFontSize.value = String(Number(fitted.toFixed(2)));
        }
        styles = normalizeStyles(styles.flatMap((item) => item.type === "size" ? subtractRange(item, range) : [item]));
        if (relative !== 1) styles = normalizeStyles([...styles, {...range, type:"size", scale:relative}]);
        savedSelection = range; renderEditor(range); clearProduction();
        toolbarStatus.textContent = "Selection size updated; other formatting preserved";
        scheduleResize(); schedulePreview();
      }
      function applyStyle(kind) {
        const range = trimRangeWhitespace(selection());
        if (!range) {
          toolbarStatus.textContent = "Select words before applying formatting";
          return;
        }

        const fillStyles = new Set(["accent", "highlight", "outline"]);
        const isFill = fillStyles.has(kind);

        const existing = rangeCovered(kind, range);
        styles = styles.flatMap((item) => {
          const shouldSubtract = isFill ? fillStyles.has(item.type) : item.type === kind;
          return shouldSubtract ? subtractRange(item, range) : [item];
        });
        if (!existing) styles.push({ ...range, type: kind });

        styles = normalizeStyles(styles);
        renderEditor(range);
        clearProduction();
        toolbarStatus.textContent = `${kind} ${existing ? "removed from" : "applied to"} the selection`;
        scheduleResize();
        schedulePreview();
      }
      function readLines() { const value = textValue(); return value.includes("\n") ? value.split("\n") : null; }
      function normalizeHex(value) { const normalized = String(value || "").trim().toUpperCase(); return hexPattern.test(normalized) ? normalized : null; }
      function readPalette() { return { name:paletteName.value.trim() || "Custom palette", colors:Object.fromEntries(Object.entries(paletteFields).map(([key, ids]) => [key, normalizeHex($(ids[1]).value) || $(ids[0]).value.toUpperCase()])) }; }
      function writePalette(value, rememberInitial = false) { if (!value?.colors) return; const colors = {}; Object.entries(paletteFields).forEach(([key, ids]) => { const color = normalizeHex(value.colors[key]); if (!color) return; colors[key] = color; $(ids[0]).value = color; $(ids[1]).value = color; }); if (Object.keys(colors).length !== 4) return; paletteName.value = String(value.name || "Custom palette"); if (rememberInitial) paletteInitial = { name:paletteName.value, colors:{ ...colors } }; syncPalettePreset(); }
      function samePalette(first, second) { return Object.keys(paletteFields).every((key) => normalizeHex(first?.colors?.[key]) === normalizeHex(second?.colors?.[key])); }
      function syncPalettePreset() { const current = readPalette(); if (samePalette(current, paletteInitial)) palettePreset.value = "initial"; else { const match = Object.entries(palettePresets).find(([, value]) => samePalette(current, value)); palettePreset.value = match?.[0] || "custom"; } }
      function currentArguments() { const value = textValue(), style = selectedStyle(), ribbons = style.grammar === "ribbons"; return { text:value, format:format.value, attribution:attribution.value, styles:styles.length ? styles.filter((item) => ribbons || item.type !== "size") : [], lines:readLines(), direction:style.direction, graphic_mode:style.hidden ? "hidden" : "auto", graphic_variant:style.variant, graphic_seed:graphicSeed, text_scale:Number(scale.value) / 100, vertical_position:position.value, palette:readPalette(), transformation:draftTransformation, evidence_status:draftEvidenceStatus, alt_text:draftAltText, visual_grammar:ribbons ? "ribbons" : null, composition:ribbons ? ribbonComposition : null, composition_candidates:ribbons ? ribbonCandidates : [], proposal_source:ribbons ? ribbonProposalSource : null, quote_font_size:ribbons && quoteFontSize.value ? Number(quoteFontSize.value) : null, author_font_size:ribbons && authorFontSize.value ? Number(authorFontSize.value) : null, ...(ribbons && pendingReuseComposition ? {reuse_composition:pendingReuseComposition} : {}) }; }
      function currentDraft() { const {reuse_composition, ...draft} = currentArguments(); return { ...draft, profile_mode:paletteDecision.value === "custom" ? "custom" : "neutral", transformation:draftTransformation, evidence_status:draftEvidenceStatus, alt_text:draftAltText, _editor_revision:editRevision, _editor_update_status:draftUpdateStatus, _applied_editor_updates:appliedUpdateFingerprints.slice(-20), _workspace:{ attributionDecision:attributionDecision.value, paletteDecision:paletteDecision.value, demoExample:demoChoices, demoAttributionChoice, demoPaletteChoice } }; }
      function resetDemoLabels() { demoNoneOption.textContent = demoAttributionChoice ? "Scelta demo: nessuna attribuzione" : "No attribution"; demoNeutralOption.textContent = demoPaletteChoice ? "Palette neutra demo" : "Neutral palette"; }
      function clearDemoChoicesOnEdit() {
        if (!demoChoices || textValue().replace(/\s+/gu, " ").trim() === demoQuote) return;
        demoChoices = false;
        demoHelper.hidden = true;
        if (demoAttributionChoice) { attributionDecision.value = "none"; attribution.value = ""; attribution.disabled = true; }
        demoAttributionChoice = false; demoPaletteChoice = false;
        resetDemoLabels();
        syncWorkspaceReadiness();
      }
      function initializeDemoWorkspace() {
        if (!workspaceMode || hostState?.hasRestoredDraft() || initialContentObserved || hasRendered || editRevision !== 0) return false;
        demoChoices = true;
        demoAttributionChoice = true; demoPaletteChoice = true;
        setTextValue(demoQuoteLayout);
        styles = demoQuoteStyles();
        renderEditor();
        demoHelper.hidden = false;
        resetDemoLabels();
        attribution.value = "";
        attributionDecision.value = "none";
        attribution.disabled = true;
        paletteDecision.value = "neutral";
        writePalette(canonicalNeutralPalette);
        errors.textContent = "";
        errors.hidden = true;
        status.textContent = "Example preview is loading…";
        syncWorkspaceReadiness();
        schedulePreview(0);
        return true;
      }
      function customPaletteIsValid() { return Object.values(paletteFields).every((ids) => Boolean(normalizeHex($(ids[1]).value))); }
      function workspaceReadiness() {
        if (!textValue().trim()) return { ready:false, message:"Write the quote to continue." };
        if (!customPaletteIsValid()) return { ready:false, message:"Enter a valid six-digit hex value for every palette color." };
        return { ready:true, message:"Ready to preview." };
      }
      function syncWorkspaceReadiness(options = {}) {
        const readiness = workspaceReadiness();
        if (workspaceMode && !submit.dataset.busy) submit.disabled = !readiness.ready;
        if (workspaceMode && !produce.dataset.busy) produce.disabled = !readiness.ready;
        if (workspaceMode && options.announce && (!hasRendered || !readiness.ready) && !submit.dataset.busy) status.textContent = readiness.message;
        return readiness;
      }
      function currentSignature() { return JSON.stringify(currentArguments()); }
      function clearProduction(invalidate = true) { if (invalidate) { editRevision += 1; if (hostState) { hostState.setDraft(currentDraft()); hostState.setImageIds([]); hostState.setPrivateContent({}); } actionSequence += 1; delete submit.dataset.busy; delete produce.dataset.busy; submit.disabled = false; produce.disabled = false; } if (deliveryUrl && deliveryUrl.startsWith("blob:")) URL.revokeObjectURL(deliveryUrl); deliveryUrl = ""; deliveryFileId = ""; deliveryFilename = ""; deliveryFile = null; preparedSignature = ""; remoteLink.hidden = true; remoteLink.removeAttribute("href"); delivery.hidden = true; syncWorkspaceReadiness({announce:invalidate}); }
      function selectedStyleKey() { return document.querySelector('[data-style-choice][aria-pressed="true"]')?.dataset.styleChoice || "blocks"; }
      function selectedStyle() { return styleOptions[selectedStyleKey()] || styleOptions.blocks; }
      function styleKeyFromInput(input) { if (input?.visual_grammar === "ribbons" || input?.presentation?.visual_grammar === "ribbons" || input?.style === "ribbons") return "ribbons"; if (input?.graphic_mode === "hidden") return "plain"; if (styleOptions[input?.style] && !styleOptions[input.style].hidden) return input.style; const match = Object.entries(styleOptions).find(([, option]) => !option.hidden && !option.grammar && option.direction === input?.direction && option.variant === input?.graphic_variant); return match?.[0] || "blocks"; }
      function updateStyleState() { const selected = selectedStyle(); direction.value = selected.direction; $("styleHint").textContent = selected.grammar === "ribbons" ? "Nastri uses the selected numeric composition; words, author and palette remain editable." : selected.hidden ? "Pattern hidden. Choose a style to restore it." : `${selected.label} selected. Vary the pattern to explore another deterministic composition.`; $("patternVariation").hidden = Boolean(selected.hidden || selected.grammar); $("patternSeed").textContent = `Seed ${graphicSeed}`; $("patternPrevious").disabled = graphicSeed === 0; const ribbons = selected.grammar === "ribbons"; ["ribbonCompositions","ribbonSizes","ribbonSizeNote","selectionSizeControl"].forEach((id) => { $(id).hidden = !ribbons; }); $("legacyScale").hidden = ribbons; $("legacyPosition").hidden = ribbons; $("saveBase").disabled = !ribbons || !ribbonComposition; }
      function setStyleChoice(key) { if (!styleOptions[key]) key = "blocks"; document.querySelectorAll("[data-style-choice]").forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.styleChoice === key))); updateStyleState(); }
      function isRibbonStyle() { return selectedStyle().grammar === "ribbons"; }
      function applyRibbonInput(input) {
        const source = input.presentation && typeof input.presentation === "object" ? {...input.presentation, ...input} : input;
        if (Object.prototype.hasOwnProperty.call(source, "composition")) ribbonComposition = source.composition && typeof source.composition === "object" ? structuredClone(source.composition) : null;
        if (Array.isArray(source.composition_candidates)) ribbonCandidates = structuredClone(source.composition_candidates);
        if (Object.prototype.hasOwnProperty.call(source, "proposal_source")) ribbonProposalSource = ["model","demo"].includes(source.proposal_source) ? source.proposal_source : null;
        ["quote_font_size","author_font_size"].forEach((key) => { if (Object.prototype.hasOwnProperty.call(source, key)) (key === "quote_font_size" ? quoteFontSize : authorFontSize).value = Number.isFinite(source[key]) ? String(source[key]) : ""; });
        if (ribbonComposition && isRibbonStyle()) pendingReuseComposition = null;
        renderRibbonProposals(); updateStyleState();
      }
      function renderRibbonProposals() {
        const container = $("ribbonProposals"); container.replaceChildren();
        $("ribbonSource").textContent = ribbonProposalSource === "model" ? "Compositions designed by the model. Each choice keeps its exact geometry." : "Demo proposals: numeric examples, generated without calling a model from this editor.";
        ribbonCandidates.forEach((composition) => {
          const button = document.createElement("button"); button.type = "button"; button.className = "ribbon-proposal"; button.dataset.compositionId = composition.id;
          button.setAttribute("aria-pressed", String(composition.id === ribbonComposition?.id));
          const thumb = document.createElement("span"); thumb.className = "ribbon-thumb"; thumb.setAttribute("aria-hidden", "true");
          const preview = ribbonPreviews.find((item) => item.id === composition.id);
          if (typeof preview?.svg === "string") { const image = document.createElement("img"); image.alt = ""; image.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(preview.svg)}`; thumb.append(image); }
          else thumb.textContent = "Preview…";
          const label = document.createElement("span"); label.textContent = composition.name || composition.id;
          button.append(thumb, label); container.append(button);
        });
        if (!ribbonCandidates.length && ribbonComposition) { const note = document.createElement("p"); note.className = "hint"; note.textContent = `Current composition: ${ribbonComposition.name || ribbonComposition.id}.`; container.append(note); }
      }
      function renderRibbonState(result) {
        ribbonLayout = result.ribbon_layout || null;
        if (Array.isArray(result.composition_previews)) ribbonPreviews = result.composition_previews;
        renderRibbonProposals();
        if (isRibbonStyle()) $("ribbonSizeNote").textContent = `Quote: ${Number(ribbonLayout?.font_size || 0).toFixed(1)}px · Author: ${Number(ribbonLayout?.author_font_size || 0).toFixed(1)}px. Manual sizes stay fixed; layout observations appear under Avvisi.`;
      }
      function renderWarnings(items) {
        const warnings = Array.isArray(items) ? [...items] : [];
        if (workspaceMode && attributionDecision.value === "named" && !attribution.value.trim()) warnings.push({message:"The author field is blank; the card has no visible attribution."});
        $("warningsPanel").hidden = !warnings.length; $("warningsCount").textContent = warnings.length;
        const list = $("warningsList"); list.replaceChildren();
        warnings.forEach((warning) => { const item = document.createElement("li"); item.textContent = typeof warning === "string" ? warning : String(warning.message || "Avviso sulla card."); list.append(item); });
      }
      function renderSavedBases() {
        const container = $("savedBases"); container.replaceChildren();
        (hostState?.listBases() || []).forEach((base) => {
          const item = document.createElement("div"); item.className = "saved-base";
          const name = document.createElement("strong"); name.textContent = base.name;
          const actions = document.createElement("div"); actions.className = "ribbon-actions";
          [["card","Reuse this card"],["style","Create in this style · demo"]].forEach(([mode,label]) => { const button = document.createElement("button"); button.type = "button"; button.dataset.baseId = base.id; button.dataset.reuseMode = mode; button.textContent = label; actions.append(button); });
          item.append(name, actions); container.append(item);
        });
      }
      function beginBaseReuse(id, mode) {
        const base = hostState?.listBases().find((item) => item.id === id); if (!base) return;
        reuseBaseId = id; reuseMode = mode;
        $("reuseTitle").textContent = `${mode === "style" ? "Create in this style · demo" : "Reuse this card"} · ${base.name}`;
        $("reuseText").value = textValue() || base.draft.text || ""; $("reuseAuthor").value = attribution.value;
        $("reuseForm").hidden = false; $("reuseText").focus(); scheduleResize();
      }
      function acceptProjectDraft(draft, reuseComposition = null) {
        pendingReuseComposition = reuseComposition;
        const next = {...draft, _editor_revision:editRevision, _workspace:{attributionDecision:draft.attribution?.trim() ? "named" : "none", paletteDecision:draft.profile_mode === "neutral" ? "neutral" : "custom", demoExample:false}};
        appliedUpdateFingerprints = []; draftUpdateStatus = ""; savedSelection = null; ribbonPreviews = []; ribbonLayout = null;
        applyInput(next); initialContentObserved = true; demoChoices = false; demoAttributionChoice = false; demoPaletteChoice = false; resetDemoLabels(); demoHelper.hidden = true;
        clearProduction(); schedulePreview(0); scheduleResize();
      }
      const REQUEST_TIMEOUT_MS = 30000;
      function responseErrorMessage(value, fallback = "The host returned an error.") { const visited = new Set(); function visit(item) { if (item instanceof Error && item.message) return item.message; if (typeof item === "string" && item.trim()) return item.trim(); if (!item || typeof item !== "object" || visited.has(item)) return null; visited.add(item); if (item.message) { const message = visit(item.message); if (message) return message; } if (item.error) { const message = visit(item.error); if (message) return message; } if (item.data) { const message = visit(item.data); if (message) return message; } for (const key of ["call_tool_result", "mcp_tool_result", "result", "params"]) { const message = visit(item[key]); if (message) return message; } if (Array.isArray(item.content)) { for (const part of item.content) { if (part?.text) { const message = visit(part.text); if (message) return message; } } } return null; } return visit(value) || fallback; }
      function hasErrorEnvelope(value) { const visited = new Set(); function visit(item) { if (!item || typeof item !== "object" || visited.has(item)) return false; visited.add(item); if (item.isError === true || item.error) return true; return [item.result, item.params, item.toolResult, item.tool_result, item.output, item.call_tool_result, item.mcp_tool_result].some(visit); } return visit(value); }
      function request(method, params, timeoutMs = REQUEST_TIMEOUT_MS) { const id = nextId++; return new Promise((resolve, reject) => { let settled = false; const finish = (callback, value) => { if (settled) return; settled = true; pending.delete(id); clearTimeout(timeoutId); callback(value); }; const timeoutId = setTimeout(() => finish(reject, new Error(`The host did not respond to ${method}.`)), timeoutMs); pending.set(id, { resolve:(value) => finish(resolve, value), reject:(error) => finish(reject, error instanceof Error ? error : new Error(responseErrorMessage(error))) }); try { window.parent.postMessage({ jsonrpc:"2.0", id, method, params }, "*"); } catch (error) { finish(reject, error); } }); }
      function schedulePreview(delay = 160) { window.clearTimeout(previewTimer); if (!workspaceReadiness().ready) return; previewTimer = window.setTimeout(() => updatePreview(), delay); }
      function showErrors(items) { const messages = (items || []).map((item) => item.message || String(item)); errors.textContent = messages.join(" "); errors.hidden = messages.length === 0; }
      function extractStructuredContent(message, metadata) {
        const result = QcbToolResults.read(message, metadata);
        if (hasErrorEnvelope(message) || hasErrorEnvelope(metadata)) return result || { valid:false, rendered:false, errors:[{ message:responseErrorMessage(metadata || message, "The host returned an error while running the tool.") }] };
        return result;
      }
      function safeInlineSvg(svgText) { if (typeof svgText !== "string" || !svgText.trim()) return null; const parsed = new DOMParser().parseFromString(svgText, "image/svg+xml"); const root = parsed.documentElement; if (!root || root.nodeName.toLowerCase() !== "svg" || parsed.querySelector("parsererror")) return null; root.querySelectorAll("script, foreignObject").forEach((node) => node.remove()); root.querySelectorAll("*").forEach((node) => [...node.attributes].forEach((attribute) => { const name = attribute.name.toLowerCase(); const value = attribute.value.trim().toLowerCase(); if (name.startsWith("on") || ((name === "href" || name === "xlink:href") && !value.startsWith("#"))) node.removeAttribute(attribute.name); })); return document.importNode(root, true); }
      function isWorkspaceOpeningResult(result) { return workspaceMode && result?.mode === "workspace" && result?.workspace_state === "empty" && result?.rendered === false; }
      function render(result) { if (isWorkspaceOpeningResult(result)) { status.textContent = "Start with a quote."; syncWorkspaceReadiness(); scheduleResize(); return; } if (!result || typeof result.valid !== "boolean" || typeof result.rendered !== "boolean") { errors.textContent = "The preview response was incomplete. Select Update preview to retry."; errors.hidden = false; status.textContent = "Preview response unavailable."; scheduleResize(); return; } if (result.editor_state) { const editorHadFocus = document.activeElement === text || text.contains(document.activeElement); const editorRange = editorHadFocus ? selectionRange() : null; const editorText = textValue(), editorSignature = currentSignature(); const editorState = { ...result.editor_state }; if (workspaceMode) { const suppliedWorkspace = editorState._workspace || {}; const preserveWorkspaceChoices = hasRendered || demoChoices || initialContentObserved || hostState?.hasRestoredDraft(); const suppliedPaletteDecision = editorState.profile_mode === "neutral" ? "neutral" : (editorState.profile_mode === "custom" ? "custom" : (editorState.palette?.colors || result.palette ? "custom" : "neutral")); editorState._workspace = { ...suppliedWorkspace, attributionDecision:preserveWorkspaceChoices ? attributionDecision.value : (suppliedWorkspace.attributionDecision || (typeof editorState.attribution === "string" && editorState.attribution.trim() ? "named" : "none")), paletteDecision:preserveWorkspaceChoices ? paletteDecision.value : (suppliedWorkspace.paletteDecision || suppliedPaletteDecision), demoExample:preserveWorkspaceChoices ? demoChoices : suppliedWorkspace.demoExample === true, demoAttributionChoice:preserveWorkspaceChoices ? demoAttributionChoice : suppliedWorkspace.demoAttributionChoice === true, demoPaletteChoice:preserveWorkspaceChoices ? demoPaletteChoice : suppliedWorkspace.demoPaletteChoice === true }; } if (hasRendered || hostState?.hasRestoredDraft()) { editorState.transformation = draftTransformation; editorState.evidence_status = draftEvidenceStatus; editorState.alt_text = draftAltText; } if (!editorState.palette && result.palette) editorState.palette = { name:result.profile || "Initial palette", colors:result.palette }; applyInput(editorState); if (editorHadFocus && editorRange && editorText === textValue() && editorSignature === currentSignature()) { text.focus({preventScroll:true}); restoreSelection(editorRange); } } hasRendered = true; if (hostState) { hostState.receiveToolResult(result); hostState.acceptToolInput(currentDraft()); } showErrors(result.errors); if (typeof renderWarnings === "function") renderWarnings(result.warnings || []); if (typeof renderRibbonState === "function") renderRibbonState(result); const svgNode = result.rendered && !result.errors?.length ? safeInlineSvg(result.svg) : null; if (!svgNode) { image.replaceChildren(); image.hidden = true; meta.textContent = "The preview is unavailable."; status.textContent = "Review the errors and try again."; syncWorkspaceReadiness({announce:true}); scheduleResize(); return; } if (result.format) format.value = result.format; image.replaceChildren(svgNode); image.setAttribute("aria-label", result.alt_text || "Quote card preview"); image.hidden = false; meta.textContent = `${result.profile} · ${selectedStyle().label} · ${result.format} · ${Math.round((result.text_scale || Number(scale.value) / 100) * 100)}% · ${result.vertical_position || position.value}`; status.textContent = result.produced ? "Quote card generated by the canonical renderer." : "Preview ready."; syncWorkspaceReadiness({announce:true}); scheduleResize(); }
      function applyInput(params) { const input = params?.arguments || params; if (!input) return; if (["VERBATIM","EDITED","PARAPHRASE","AI_GENERATED"].includes(input.transformation)) draftTransformation = input.transformation; if (["VERIFIED","USER_SUPPLIED","UNVERIFIED","CONFLICT"].includes(input.evidence_status)) draftEvidenceStatus = input.evidence_status; if (typeof input.alt_text === "string") draftAltText = input.alt_text; if (typeof input._editor_update_status === "string") draftUpdateStatus = input._editor_update_status; if (Array.isArray(input._applied_editor_updates)) appliedUpdateFingerprints = input._applied_editor_updates.filter((item) => typeof item === "string").slice(-20); if (Number.isSafeInteger(input._editor_revision) && input._editor_revision >= 0) editRevision = input._editor_revision; if (workspaceMode) { demoChoices = input._workspace?.demoExample === true; demoAttributionChoice = demoChoices && (typeof input._workspace.demoAttributionChoice === "boolean" ? input._workspace.demoAttributionChoice : true); demoPaletteChoice = demoChoices && (typeof input._workspace.demoPaletteChoice === "boolean" ? input._workspace.demoPaletteChoice : true); demoHelper.hidden = !demoChoices; resetDemoLabels(); } if (Array.isArray(input.styles)) styles = normalizeStyles(input.styles); else if (input.styles === null) styles = []; if (typeof input.text === "string") setTextValue(input.text); else renderEditor(); if (["4x5", "1x1", "9x16"].includes(input.format)) format.value = input.format; if (typeof input.attribution === "string") attribution.value = input.attribution; if (workspaceMode && input._workspace) { const storedAttributionDecision = input._workspace.attributionDecision; attributionDecision.value = ["named","none"].includes(storedAttributionDecision) ? storedAttributionDecision : (typeof input.attribution === "string" && input.attribution.trim() ? "named" : "none"); paletteDecision.value = input._workspace.paletteDecision === "custom" ? "custom" : "neutral"; } else if (workspaceMode) { attributionDecision.value = typeof input.attribution === "string" && input.attribution.trim() ? "named" : "none"; paletteDecision.value = input.profile_mode === "neutral" ? "neutral" : input.palette?.colors ? "custom" : "neutral"; } else { attributionDecision.value = attribution.value.trim() ? "named" : "none"; paletteDecision.value = input.profile_mode === "neutral" ? "neutral" : "custom"; } if (workspaceMode && attributionDecision.value === "none") attribution.value = ""; setStyleChoice(styleKeyFromInput(input)); if (Number.isInteger(input.graphic_seed) && input.graphic_seed >= 0 && input.graphic_seed <= 999999) graphicSeed = input.graphic_seed; if (input.palette?.colors) writePalette(input.palette, !hasRendered && !workspaceMode); else if (!hasRendered) writePalette(paletteInitial, true); if (workspaceMode && paletteDecision.value === "neutral") writePalette(canonicalNeutralPalette); if (typeof input.text_scale === "number") { scale.value = String(Math.round(input.text_scale * 100)); scaleValue.textContent = `${scale.value}%`; } if (typeof input.vertical_position === "string") position.value = input.vertical_position; attribution.disabled = workspaceMode && attributionDecision.value !== "named"; if (typeof applyRibbonInput === "function") applyRibbonInput(input); updateStyleState(); syncWorkspaceReadiness(); scheduleResize(); }
      async function svgToPngFile(svgText, filename) {
        const parsed = new DOMParser().parseFromString(svgText, "image/svg+xml");
        const root = parsed.documentElement;
        if (!root || root.nodeName.toLowerCase() !== "svg" || parsed.querySelector("parsererror")) throw new Error("Invalid SVG");
        const viewBox = (root.getAttribute("viewBox") || "").trim().split(/[ ,]+/).map(Number);
        const width = Number(root.getAttribute("width")) || viewBox[2] || 1440;
        const height = Number(root.getAttribute("height")) || viewBox[3] || 1800;
        if (!Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0) throw new Error("Invalid SVG dimensions");
        const imageSource = new Image();
        const blobUrl = URL.createObjectURL(new Blob([svgText], { type:"image/svg+xml;charset=utf-8" }));
        try {
          // Web clients differ in how they decode SVG data URLs inside an
          // iframe. Try the portable data URL first, then a same-origin Blob
          // URL before reporting that PNG conversion is unavailable.
          const sources = [
            `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svgText)}`,
            blobUrl,
          ];
          let loaded = false;
          for (const source of sources) {
            try {
              await new Promise((resolve, reject) => {
                imageSource.onload = resolve;
                imageSource.onerror = () => reject(new Error("Unable to rasterize the preview"));
                imageSource.src = source;
              });
              loaded = true;
              break;
            } catch (_) { /* try the alternate local source */ }
          }
          if (!loaded) throw new Error("Unable to rasterize the preview");
          const canvas = document.createElement("canvas");
          canvas.width = Math.round(width); canvas.height = Math.round(height);
          const context = canvas.getContext("2d");
          if (!context) throw new Error("Canvas is unavailable");
          context.drawImage(imageSource, 0, 0, canvas.width, canvas.height);
          const png = await new Promise((resolve, reject) => canvas.toBlob((blob) => blob ? resolve(blob) : reject(new Error("PNG is unavailable")), "image/png"));
          return new File([png], filename.replace(/\.svg$/i, ".png"), { type:"image/png" });
        } finally { imageSource.src = ""; URL.revokeObjectURL(blobUrl); }
      }
      function validatedDownloadUrl(value) {
        let parsed;
        try { parsed = new URL(value); }
        catch (_) { throw new Error("ChatGPT returned an invalid PNG URL."); }
        if (parsed.protocol !== "https:") throw new Error("ChatGPT returned a non-HTTPS PNG URL.");
        if (!allowedDownloadOrigins.has(parsed.origin)) throw new Error(`ChatGPT returned an unauthorized PNG host: ${parsed.origin}`);
        return parsed.href;
      }
      function validatedRemoteExport(value) {
        let parsed;
        try { parsed = new URL(value); }
        catch (_) { throw new Error("The server returned an invalid PNG URL."); }
        if (parsed.protocol !== "https:" || parsed.origin !== remoteExportOrigin || parsed.username || parsed.password || parsed.search || parsed.hash || !/^\/exports\/[A-Za-z0-9_-]{32}\.png$/.test(parsed.pathname)) {
          throw new Error("The server returned an unauthorized PNG URL.");
        }
        return parsed.href;
      }
      function withTimeout(promise, timeoutMs, message) {
        return new Promise((resolve, reject) => {
          const timeoutId = setTimeout(() => reject(new Error(message)), timeoutMs);
          Promise.resolve(promise).then(
            (value) => { clearTimeout(timeoutId); resolve(value); },
            (error) => { clearTimeout(timeoutId); reject(error); },
          );
        });
      }
      function currentDeliverySnapshot() { return { file:deliveryFile, fileId:deliveryFileId, filename:deliveryFilename, url:deliveryUrl, revision:typeof editRevision === "number" ? editRevision : null, sequence:typeof actionSequence === "number" ? actionSequence : null }; }
      function isCurrentDelivery(snapshot) { return isCurrentAction(snapshot?.sequence, snapshot?.revision) && deliveryFile === snapshot?.file && deliveryFileId === snapshot?.fileId && deliveryFilename === snapshot?.filename && deliveryUrl === snapshot?.url; }
      function canSaveLocally(snapshot = currentDeliverySnapshot()) { return Boolean(snapshot?.file?.qcbLocalDelivery); }
      function canHostDownload(snapshot = currentDeliverySnapshot()) { return Boolean(snapshot?.file && hostCapabilities?.downloadFile); }
      async function fileToBase64(file) {
        const bytes = new Uint8Array(await file.arrayBuffer());
        let binary = "";
        for (let offset = 0; offset < bytes.length; offset += 32768) {
          binary += String.fromCharCode(...bytes.subarray(offset, offset + 32768));
        }
        return btoa(binary);
      }
      async function savePreparedPng(snapshot = currentDeliverySnapshot()) {
        if (!canSaveLocally(snapshot)) throw new Error("Local PNG saving is unavailable.");
        if (!isCurrentDelivery(snapshot)) return null;
        if (snapshot.file.qcbSavedPath) return snapshot.file.qcbSavedPath;
        status.textContent = "Saving PNG to Downloads/Quote Card Builder…";
        const blob = await fileToBase64(snapshot.file);
        if (!isCurrentDelivery(snapshot)) return null;
        const result = await request("tools/call", { name:"quote_card_builder_save_png", arguments:{png_base64:blob} });
        if (!isCurrentDelivery(snapshot)) return null;
        const saved = extractStructuredContent(result);
        if (!saved?.path?.startsWith("/") || !saved.path.endsWith(".png") || result?.isError) throw new Error("The server did not confirm a saved PNG file.");
        snapshot.file.qcbSavedPath = saved.path;
        status.textContent = "PNG saved: " + saved.path;
        scheduleResize();
        return saved.path;
      }
      async function prepareRemotePng(snapshot = currentDeliverySnapshot()) {
        if (!snapshot?.file?.qcbRemoteDelivery) throw new Error("Remote PNG delivery is unavailable.");
        if (!isCurrentDelivery(snapshot)) return null;
        if (snapshot.file.qcbRemoteExport) {
          if (Date.parse(snapshot.file.qcbRemoteExport.expiresAt) > Date.now()) return snapshot.file.qcbRemoteExport;
          delete snapshot.file.qcbRemoteExport;
        }
        if (snapshot.file.qcbRemoteExportPromise) return snapshot.file.qcbRemoteExportPromise;
        const file = snapshot.file;
        const operation = (async () => {
          status.textContent = "Preparing the PNG link…";
          const bytes = new Uint8Array(await file.arrayBuffer());
          if (!isCurrentDelivery(snapshot)) return null;
          const digest = await crypto.subtle.digest("SHA-256", bytes);
          const expectedHash = Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
          let binary = "";
          for (let offset = 0; offset < bytes.length; offset += 32768) binary += String.fromCharCode(...bytes.subarray(offset, offset + 32768));
          const response = await request("tools/call", { name:"quote_card_builder_publish_png", arguments:{png_base64:btoa(binary)} });
          if (!isCurrentDelivery(snapshot)) return null;
          const published = extractStructuredContent(response);
          if (response?.isError || !published) throw new Error("The server did not confirm a published PNG.");
          const url = validatedRemoteExport(published.url || "");
          const expiry = Date.parse(published.expires_at || "");
          const expectedFilename = "quote-card-" + expectedHash.slice(0, 16) + ".png";
          if (published.filename !== expectedFilename || published.mime_type !== "image/png" || typeof published.sha256 !== "string" || published.sha256.toLowerCase() !== expectedHash || !Number.isFinite(expiry) || expiry <= Date.now()) {
            throw new Error("The server returned incomplete or mismatched PNG metadata.");
          }
          const cached = {url, filename:published.filename, mimeType:published.mime_type, sha256:expectedHash, expiresAt:published.expires_at};
          file.qcbRemoteExport = cached;
          if (isCurrentDelivery(snapshot)) deliveryName.textContent = published.filename;
          return cached;
        })();
        file.qcbRemoteExportPromise = operation;
        try { return await operation; }
        finally { if (file.qcbRemoteExportPromise === operation) delete file.qcbRemoteExportPromise; }
      }
      function remoteDownloadUrl(published) {
        const parsed = new URL(published.url);
        parsed.searchParams.set("download", "1");
        return parsed.href;
      }
      async function downloadRemotePng(snapshot = currentDeliverySnapshot()) {
        const published = await prepareRemotePng(snapshot);
        if (!published || !isCurrentDelivery(snapshot)) return false;
        if (canHostDownload(snapshot)) {
          try { return await requestNativeDownload(snapshot, published.filename); }
          catch (_) { if (!isCurrentDelivery(snapshot)) return false; }
        }
        const href = remoteDownloadUrl(published);
        try {
          const result = await withTimeout(request("ui/open-link", {url:href}), 5000, "The host did not respond to the PNG link request.");
          if (result?.isError) throw new Error("The host did not accept the PNG link request.");
          if (!isCurrentDelivery(snapshot)) return false;
          remoteLink.hidden = true;
          status.textContent = "The host accepted the PNG link request.";
          return true;
        } catch (_) { if (!isCurrentDelivery(snapshot)) return false; }
        const bridge = window.openai;
        let opened = false;
        if (bridge?.openExternal) {
          try { await withTimeout(bridge.openExternal({href, redirectUrl:false}), 5000, "The host did not respond to the PNG download request."); opened = true; }
          catch (_) { if (!isCurrentDelivery(snapshot)) return false; }
        }
        if (!isCurrentDelivery(snapshot)) return false;
        if (opened) {
          remoteLink.hidden = true;
          status.textContent = "The host accepted the PNG link request.";
          return true;
        }
        remoteLink.href = href;
        remoteLink.download = published.filename || "quote-card.png";
        remoteLink.hidden = false;
        status.textContent = "The host could not open the PNG. Use the direct download link.";
        scheduleResize();
        return false;
      }
      async function requestNativeDownload(snapshot = currentDeliverySnapshot(), filenameOverride = "") {
        if (!canHostDownload(snapshot)) throw new Error("This host does not advertise native file downloads.");
        status.textContent = "Opening the save dialog…";
        scheduleResize();
        const filename = filenameOverride || snapshot.filename || "quote-card.png";
        const blob = await fileToBase64(snapshot.file);
        const result = await withTimeout(
          request("ui/download-file", {
            contents:[{
              type:"resource",
              resource:{
                uri:"file:///" + encodeURIComponent(filename),
                mimeType:"image/png",
                blob,
              },
            }],
          }),
          30000,
          "The host did not respond to the native download request.",
        );
        if (result?.isError) throw new Error("The PNG download was cancelled or denied by the host.");
        if (!isCurrentDelivery(snapshot)) return false;
        status.textContent = "PNG download accepted by the host.";
        return true;
      }
      function isCurrentAction(sequence, revision) { return typeof actionSequence !== "number" || typeof editRevision !== "number" || (sequence === actionSequence && revision === editRevision); }
      async function prepareDownload(result, revision = null, sequence = null) {
        if (typeof editRevision === "number" && typeof actionSequence === "number") { if (revision === null) revision = editRevision; if (sequence === null) sequence = actionSequence; }
        if (!isCurrentAction(sequence, revision)) return false;
        clearProduction(false);
        if (!result?.produced || !result.svg || !result.filename) return;
        let file; let downloadableName;
        try { file = await withTimeout(svgToPngFile(result.svg, result.filename), 30000, "PNG conversion did not complete."); downloadableName = file.name; }
        catch (error) { if (!isCurrentAction(sequence, revision)) return false; errors.textContent = error?.message || "Unable to prepare the PNG."; errors.hidden = false; status.textContent = "PNG unavailable: try again."; scheduleResize(); return false; }
        if (!isCurrentAction(sequence, revision)) return false;
        file.qcbLocalDelivery = result.local_file_delivery === true;
        file.qcbRemoteDelivery = result.remote_file_delivery === true;
        deliveryFile = file;
        deliveryFilename = downloadableName;
        const bridge = window.openai;
        if (!file.qcbRemoteDelivery && !canSaveLocally() && !canHostDownload() && bridge?.uploadFile && bridge?.getFileDownloadUrl) {
          try {
            status.textContent = "Preparing the PNG…";
            const uploaded = await withTimeout(bridge.uploadFile(file, { library:false }), 30000, "ChatGPT did not finish preparing the PNG.");
            if (!isCurrentAction(sequence, revision)) return false;
            deliveryFileId = uploaded?.fileId || "";
            if (!deliveryFileId) throw new Error("ChatGPT did not return a file identifier.");
            const resolved = await withTimeout(bridge.getFileDownloadUrl({ fileId:deliveryFileId }), 30000, "ChatGPT did not return a PNG download URL.");
            if (!isCurrentAction(sequence, revision)) return false;
            deliveryUrl = validatedDownloadUrl(resolved?.downloadUrl || "");
          } catch (error) {
            if (!isCurrentAction(sequence, revision)) return false;
            deliveryFileId = "";
            deliveryUrl = URL.createObjectURL(file);
          }
        } else if (!file.qcbRemoteDelivery && !canSaveLocally() && !canHostDownload()) {
          deliveryUrl = URL.createObjectURL(file);
        }
        if (!file.qcbRemoteDelivery && !canSaveLocally() && !canHostDownload() && !deliveryFileId && !deliveryUrl) deliveryUrl = URL.createObjectURL(file);
        if (!isCurrentAction(sequence, revision)) return false;
        preparedSignature = currentSignature();
        deliveryName.textContent = downloadableName;
        delivery.hidden = false;
        status.textContent = "PNG ready. Starting download…";
        scheduleResize();
        return true;
      }
      async function openPreparedDownload() {
        const snapshot = currentDeliverySnapshot();
        if (!snapshot.file && !snapshot.url && !snapshot.fileId) return;
        if (snapshot.file?.qcbRemoteDelivery) {
          try { await downloadRemotePng(snapshot); }
          catch (error) { if (!isCurrentDelivery(snapshot)) return; errors.textContent = error?.message || "Unable to download the PNG."; errors.hidden = false; status.textContent = "PNG unavailable: try again."; }
          return;
        }
        status.textContent = canSaveLocally(snapshot) ? "Saving PNG to Downloads/Quote Card Builder…" : canHostDownload(snapshot) ? "Opening the save dialog…" : "Starting the PNG download…";
        scheduleResize();
        try {
          const bridge = window.openai;
          if (canSaveLocally(snapshot)) {
            const path = await savePreparedPng(snapshot);
            if (path && hostCapabilities?.experimental?.["openai/files"]) {
              try { await request("openai/files/open", {path}); }
              catch (_) { if (isCurrentDelivery(snapshot)) status.textContent = "PNG saved: " + path + ". Open it from Downloads/Quote Card Builder."; }
            }
          } else if (canHostDownload(snapshot)) {
            await requestNativeDownload(snapshot);
          } else if (snapshot.fileId && bridge?.openExternal) {
            await withTimeout(
              bridge.openExternal({ href:snapshot.url, redirectUrl:false }),
              5000,
              "ChatGPT did not respond to the open request.",
            );
            if (!isCurrentDelivery(snapshot)) return;
            status.textContent = "PNG download opened.";
          } else if (snapshot.url.startsWith("blob:")) {
            const link = document.createElement("a");
            link.href = snapshot.url; link.download = snapshot.filename || "quote-card.png";
            link.style.display = "none"; document.body.append(link); link.click(); link.remove();
            if (!isCurrentDelivery(snapshot)) return;
            status.textContent = "PNG download started.";
          } else if (snapshot.url.startsWith("https:")) {
            remoteLink.href = snapshot.url;
            remoteLink.download = snapshot.filename || "quote-card.png";
            remoteLink.hidden = false;
            status.textContent = "The host could not start the download. Use the direct HTTPS link.";
          } else {
            throw new Error("This host cannot open the PNG download.");
          }
        } catch (error) {
          if (!isCurrentDelivery(snapshot)) return;
          const fallbackUrl = snapshot.url.startsWith("https:") ? snapshot.url : snapshot.file ? URL.createObjectURL(snapshot.file) : "";
          if (fallbackUrl) {
            if (deliveryUrl.startsWith("blob:") && deliveryUrl !== fallbackUrl) URL.revokeObjectURL(deliveryUrl);
            deliveryUrl = fallbackUrl;
            remoteLink.href = fallbackUrl;
            remoteLink.download = snapshot.filename || "quote-card.png";
            remoteLink.hidden = false;
            status.textContent = fallbackUrl.startsWith("https:") ? "The host could not start the download. Use the direct HTTPS link." : "The host could not save the PNG. Use the direct download link.";
          } else {
            errors.textContent = error?.message || "Unable to open the PNG.";
            errors.hidden = false;
            status.textContent = "PNG unavailable: try again.";
          }
        } finally { if (isCurrentDelivery(snapshot)) scheduleResize(); }
      }
      function clearUntouchedDemoForIncomingContent() {
        if (!demoChoices || initialContentObserved || editRevision !== 0 || hostState?.hasRestoredDraft()) return false;
        window.clearTimeout(previewTimer);
        demoChoices = false; demoAttributionChoice = false; demoPaletteChoice = false; demoHelper.hidden = true; resetDemoLabels(); hasRendered = false;
        setTextValue(""); attribution.value = ""; attributionDecision.value = "none"; attribution.disabled = true; paletteDecision.value = "neutral"; writePalette(canonicalNeutralPalette);
        image.replaceChildren(); image.hidden = true; meta.textContent = "";
        actionSequence += 1; delete submit.dataset.busy; delete produce.dataset.busy; submit.disabled = false; produce.disabled = false;
        clearProduction(false);
        return true;
      }
      const editorStateFields = ["text", "format", "attribution", "profile_mode", "transformation", "evidence_status", "direction", "graphic_mode", "graphic_variant", "graphic_seed", "text_scale", "vertical_position", "palette", "lines", "styles", "alt_text", "visual_grammar", "composition", "composition_candidates", "proposal_source", "quote_font_size", "author_font_size"];
      function stableJson(value) { if (Array.isArray(value)) return `[${value.map(stableJson).join(",")}]`; if (value && typeof value === "object") return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stableJson(value[key])}`).join(",")}}`; return JSON.stringify(value); }
      function editorSnapshot(value) { const source = value && typeof value === "object" && !Array.isArray(value) ? value : {}; return Object.fromEntries(editorStateFields.map((key) => [key, Object.prototype.hasOwnProperty.call(source, key) ? source[key] : null])); }
      function editorUpdateFingerprint(result) { return stableJson({ base_revision:result.base_revision, base_snapshot:editorSnapshot(result.base_snapshot), patch:result.patch }); }
      function isEditorUpdateInput(value) { const input = value?.arguments || value; return Boolean(input && typeof input === "object" && Number.isSafeInteger(input.base_revision) && input.base_snapshot && input.patch && typeof input.patch === "object"); }
      function setEditorUpdateStatus(message, announce = false) { draftUpdateStatus = String(message || ""); if (announce) { errors.textContent = draftUpdateStatus; errors.hidden = false; status.textContent = "The chat edit was not applied."; } hostState?.setDraft(currentDraft()); }
      function rejectEditorUpdate(message) { setEditorUpdateStatus(message, true); return true; }
      function applyEditorUpdateResult(result) {
        if (!result?.update) return false;
        if (result.isError || result.valid !== true || result.rendered !== true || !result.editor_state || !Number.isSafeInteger(result.base_revision) || !Number.isSafeInteger(result.editor_revision)) return rejectEditorUpdate("The chat edit could not be validated. Your current draft was kept.");
        const fingerprint = editorUpdateFingerprint(result);
        if (appliedUpdateFingerprints.includes(fingerprint)) return true;
        const baseRevision = result.base_revision, current = currentDraft(), currentRevision = editRevision;
        if (currentRevision < baseRevision) return rejectEditorUpdate("This chat edit refers to a newer draft than the one open here. Your current draft was kept.");
        const base = editorSnapshot(result.base_snapshot), now = editorSnapshot(current), patch = result.patch && typeof result.patch === "object" && !Array.isArray(result.patch) ? result.patch : {};
        const allowedPatchKeys = new Set(editorStateFields);
        const patchKeys = Object.keys(patch);
        if (!patchKeys.length || patchKeys.some((key) => !allowedPatchKeys.has(key))) return rejectEditorUpdate("The chat edit did not contain supported fields. Your current draft was kept.");
        if (currentRevision === baseRevision && stableJson(now) !== stableJson(base)) return rejectEditorUpdate("The open draft changed after this chat edit was prepared. Your current draft was kept.");
        if (currentRevision > baseRevision && patchKeys.some((key) => stableJson(now[key]) !== stableJson(base[key]) && stableJson(now[key]) !== stableJson(patch[key]))) return rejectEditorUpdate("A field requested by this chat edit changed in the open draft. Your current draft was kept.");
        const merged = { ...current };
        if (Array.isArray(patch.lines) && !Object.prototype.hasOwnProperty.call(patch, "text")) merged.text = patch.lines.join("\n");
        if (typeof patch.text === "string" && patch.text !== textValue() && !Object.prototype.hasOwnProperty.call(patch, "styles")) merged.styles = remapStylesAfterEdit(textValue(), patch.text, styles);
        if (typeof patch.text === "string" && !Object.prototype.hasOwnProperty.call(patch, "transformation")) merged.transformation = result.editor_state.transformation;
        if (typeof patch.text === "string" && !Object.prototype.hasOwnProperty.call(patch, "evidence_status")) merged.evidence_status = result.editor_state.evidence_status;
        patchKeys.forEach((key) => { merged[key] = patch[key]; });
        if (Object.prototype.hasOwnProperty.call(patch, "profile_mode")) merged._workspace = { ...(merged._workspace || {}), paletteDecision:patch.profile_mode };
        if (Object.prototype.hasOwnProperty.call(patch, "attribution")) merged._workspace = { ...(merged._workspace || {}), attributionDecision:patch.attribution.trim() ? "named" : "none" };
        if (patch.profile_mode === "neutral" && !Object.prototype.hasOwnProperty.call(patch, "palette")) merged.palette = canonicalNeutralPalette;
        if (patch.palette === null && merged.profile_mode === "neutral") merged.palette = canonicalNeutralPalette;
        const nextRevision = currentRevision + 1;
        merged._editor_revision = nextRevision;
        merged._editor_update_status = `Accepted chat edit at editor revision ${nextRevision}.`;
        appliedUpdateFingerprints = [...appliedUpdateFingerprints, fingerprint].slice(-20);
        merged._applied_editor_updates = appliedUpdateFingerprints;
        applyInput(merged);
        editRevision = nextRevision;
        draftUpdateStatus = merged._editor_update_status;
        initialContentObserved = true; demoChoices = false; demoAttributionChoice = false; demoPaletteChoice = false; resetDemoLabels(); demoHelper.hidden = true;
        clearProduction(false); hostState?.setDraft(currentDraft()); errors.hidden = true; status.textContent = "Chat edit applied to the current draft."; schedulePreview(0); scheduleResize();
        return true;
      }
      function receiveInitialInput(input) { const candidate = input?.arguments || input; if (isEditorUpdateInput(input)) return; const emptyWorkspace = candidate?.mode === "workspace" && Object.keys(candidate).every((key) => key === "mode"); if (workspaceMode && (!candidate || Object.keys(candidate).length === 0 || emptyWorkspace)) return; const replacedDemo = clearUntouchedDemoForIncomingContent(); initialContentObserved = true; if (replacedDemo || (!hasRendered && editRevision === 0 && !hostState?.hasRestoredDraft())) { applyInput(input); if (replacedDemo) hostState?.setDraft(currentDraft()); } }
      function receiveInitialResult(result) { if (!result || isWorkspaceOpeningResult(result)) return; if (result.update && !hasRendered && !hostState?.hasRestoredDraft()) { if (result.isError || result.valid !== true || result.rendered !== true || !result.editor_state || !Number.isSafeInteger(result.base_revision) || !Number.isSafeInteger(result.editor_revision) || result.editor_revision !== result.base_revision + 1) { rejectEditorUpdate("The chat edit could not be validated. Your current draft was kept."); return; } const fingerprint = editorUpdateFingerprint(result); appliedUpdateFingerprints = [...appliedUpdateFingerprints, fingerprint].slice(-20); draftUpdateStatus = `Accepted chat edit at editor revision ${result.editor_revision}.`; const seeded = { ...result, editor_state:{ ...result.editor_state, _editor_revision:result.editor_revision, _editor_update_status:draftUpdateStatus, _applied_editor_updates:appliedUpdateFingerprints } }; render(seeded); return; } if (applyEditorUpdateResult(result)) return; const replacedDemo = clearUntouchedDemoForIncomingContent(); initialContentObserved = true; if (replacedDemo || (!hasRendered && editRevision === 0 && !hostState?.hasRestoredDraft())) { render(result); if (replacedDemo) hostState?.setDraft(currentDraft()); } }
      function syncFromOpenAiAliases() {
        const bridge = window.openai;
        if (!bridge) return;
        const input = bridge.toolInput;
        const result = bridge.toolOutput || bridge.toolResponseMetadata ? extractStructuredContent(bridge.toolOutput, bridge.toolResponseMetadata) : null;
        const inputSignature = stableJson(input ?? null), resultSignature = stableJson(result ?? null);
        const inputChanged = inputSignature !== lastAliasInputSignature, resultChanged = resultSignature !== lastAliasResultSignature;
        lastAliasInputSignature = inputSignature; lastAliasResultSignature = resultSignature;
        if (isEditorUpdateInput(input)) { if (resultChanged && result?.update) receiveInitialResult(result); return; }
        if (hasRendered || editRevision > 0 || hostState?.hasRestoredDraft()) { if (resultChanged && result?.update) receiveInitialResult(result); return; }
        if (inputChanged) receiveInitialInput(input);
        if (resultChanged && result) receiveInitialResult(result);
      }
      document.querySelectorAll("[data-style]").forEach((button) => { button.addEventListener("mousedown", (event) => event.preventDefault()); button.addEventListener("click", () => applyStyle(button.dataset.style)); });
      document.querySelectorAll("[data-style-choice]").forEach((button) => button.addEventListener("click", () => { setStyleChoice(button.dataset.styleChoice); if (!isRibbonStyle()) { styles = styles.filter((item) => item.type !== "size"); savedSelection = null; pendingReuseComposition = null; renderEditor(); } else renderRibbonProposals(); clearProduction(); schedulePreview(0); }));
      $("selectionSizeApply").addEventListener("mousedown", (event) => event.preventDefault());
      $("selectionSizeApply").addEventListener("click", applySelectionSize);
      [quoteFontSize, authorFontSize].forEach((control) => control.addEventListener("input", () => { clearProduction(); schedulePreview(); }));
      [["quoteSizeAuto",quoteFontSize],["authorSizeAuto",authorFontSize]].forEach(([id,control]) => $(id).addEventListener("click", () => { control.value = ""; clearProduction(); schedulePreview(0); }));
      $("ribbonProposals").addEventListener("click", (event) => { const button = event.target.closest("[data-composition-id]"); const selected = ribbonCandidates.find((item) => item.id === button?.dataset.compositionId); if (!selected) return; ribbonComposition = structuredClone(selected); pendingReuseComposition = null; ribbonLayout = null; renderRibbonProposals(); clearProduction(); schedulePreview(0); });
      $("ribbonVariations").addEventListener("click", () => { pendingReuseComposition = ribbonComposition ? structuredClone(ribbonComposition) : null; ribbonComposition = null; ribbonCandidates = []; ribbonPreviews = []; ribbonLayout = null; ribbonProposalSource = "demo"; graphicSeed = (graphicSeed + 1) % 1000000; renderRibbonProposals(); clearProduction(); schedulePreview(0); });
      $("saveBase").addEventListener("click", () => { try { const base = hostState.saveBase($("baseName").value, currentDraft()); $("baseFeedback").textContent = `Base “${base.name}” saved on this device.`; renderSavedBases(); } catch (error) { $("baseFeedback").textContent = error.message; } scheduleResize(); });
      $("savedBases").addEventListener("click", (event) => { const button = event.target.closest("[data-base-id]"); if (button) beginBaseReuse(button.dataset.baseId, button.dataset.reuseMode); });
      $("reuseCancel").addEventListener("click", () => { $("reuseForm").hidden = true; scheduleResize(); });
      $("reuseConfirm").addEventListener("click", () => { const base = hostState?.listBases().find((item) => item.id === reuseBaseId); if (!base || !$("reuseText").value.trim()) { $("baseFeedback").textContent = "A quote is required for reuse."; return; } const reused = QcbHostContext.reuseBase(base.draft, $("reuseText").value, $("reuseAuthor").value, reuseMode); acceptProjectDraft(reused.draft, reused.reuse_composition); $("reuseForm").hidden = true; $("baseFeedback").textContent = reuseMode === "style" ? "Demo variations in the saved style are loading; palette roles and ribbon widths are retained." : "Saved composition restored; a new quote starts with automatic size and fresh formatting."; });
      $("exportProject").addEventListener("click", () => { const project = QcbHostContext.projectFromDraft(currentDraft(), $("baseName").value || "Quote card"); const serialized = JSON.stringify(project, null, 2); $("projectJson").value = serialized; $("projectJsonLabel").hidden = false; $("projectJsonActions").hidden = false; if (projectDownloadUrl) URL.revokeObjectURL(projectDownloadUrl); projectDownloadUrl = URL.createObjectURL(new Blob([serialized + "\n"], {type:"application/json"})); $("projectDownload").href = projectDownloadUrl; $("projectDownload").hidden = false; $("baseFeedback").textContent = "Project JSON ready to copy or download. It contains the card choices and exact numeric composition."; scheduleResize(); });
      $("copyProjectJson").addEventListener("click", async () => { try { if (!navigator.clipboard?.writeText) throw new Error("Clipboard unavailable"); await navigator.clipboard.writeText($("projectJson").value); $("baseFeedback").textContent = "Project JSON copied."; } catch (_) { $("projectJson").focus(); $("projectJson").select(); $("baseFeedback").textContent = "Project JSON selected; it can be copied with the keyboard."; } });
      $("importProject").addEventListener("click", () => $("projectFile").click());
      $("projectFile").addEventListener("change", async () => { const file = $("projectFile").files?.[0]; if (!file) return; const revision = editRevision; try { if (file.size > 2 * 1024 * 1024) throw new Error("The project exceeds 2 MB."); const draft = QcbHostContext.draftFromProject(JSON.parse(await file.text())); const {profile_mode, ...arguments_} = draft; const result = extractStructuredContent(await request("tools/call", {name:"preview_quote_card", arguments:{...arguments_, output_image:false, compact_output:true}})); if (!result?.rendered || result.errors?.length) throw new Error(result?.errors?.[0]?.message || "The project is not valid."); if (revision !== editRevision) throw new Error("The open draft changed during import; it was kept."); acceptProjectDraft({...draft, ...result.editor_state, profile_mode:draft.profile_mode}); render(result); $("baseFeedback").textContent = "Project restored with palette, formatting and exact composition."; } catch (error) { $("baseFeedback").textContent = `Project not loaded: ${error.message}`; } finally { $("projectFile").value = ""; scheduleResize(); } });
      attributionDecision.addEventListener("change", () => { demoAttributionChoice = false; resetDemoLabels(); if (attributionDecision.value === "none") attribution.value = ""; attribution.disabled = workspaceMode && attributionDecision.value !== "named"; if (attributionDecision.value === "named") attribution.focus(); clearProduction(); schedulePreview(0); });
      paletteDecision.addEventListener("change", () => { demoPaletteChoice = false; resetDemoLabels(); if (paletteDecision.value === "neutral") writePalette(canonicalNeutralPalette); clearProduction(); schedulePreview(0); });
      $("patternPrevious").addEventListener("click", () => { graphicSeed = (graphicSeed + 999999) % 1000000; updateStyleState(); clearProduction(); schedulePreview(0); });
      $("patternNext").addEventListener("click", () => { graphicSeed = (graphicSeed + 1) % 1000000; updateStyleState(); clearProduction(); schedulePreview(0); });
      palettePreset.addEventListener("change", () => { demoPaletteChoice = false; resetDemoLabels(); const chosen = palettePreset.value === "initial" ? (workspaceMode ? canonicalNeutralPalette : paletteInitial) : palettePresets[palettePreset.value]; if (chosen) writePalette(chosen); if (workspaceMode) paletteDecision.value = palettePreset.value === "initial" ? "neutral" : "custom"; clearProduction(); schedulePreview(0); });
      $("paletteReset").addEventListener("click", () => { demoPaletteChoice = false; resetDemoLabels(); writePalette(workspaceMode ? canonicalNeutralPalette : paletteInitial); if (workspaceMode) paletteDecision.value = "neutral"; clearProduction(); schedulePreview(0); });
      format.addEventListener("change", () => { ribbonLayout = null; clearProduction(); scheduleResize(); schedulePreview(0); }); scale.addEventListener("input", () => { scaleValue.textContent = `${scale.value}%`; clearProduction(); scheduleResize(); schedulePreview(); }); position.addEventListener("change", () => { clearProduction(); schedulePreview(0); });
      paletteName.addEventListener("input", () => { demoPaletteChoice = false; resetDemoLabels(); if (workspaceMode) paletteDecision.value = "custom"; clearProduction(); schedulePreview(); });
      Object.entries(paletteFields).forEach(([, ids]) => { const picker = $(ids[0]), hex = $(ids[1]); picker.addEventListener("input", () => { demoPaletteChoice = false; resetDemoLabels(); hex.value = picker.value.toUpperCase(); if (workspaceMode) paletteDecision.value = "custom"; syncPalettePreset(); clearProduction(); schedulePreview(); }); hex.addEventListener("input", () => { demoPaletteChoice = false; resetDemoLabels(); const value = normalizeHex(hex.value); hex.setAttribute("aria-invalid", String(!value)); if (value) picker.value = value; if (workspaceMode) paletteDecision.value = "custom"; syncPalettePreset(); clearProduction(); if (value) schedulePreview(); }); hex.addEventListener("blur", () => { const value = normalizeHex(hex.value); hex.value = value || picker.value.toUpperCase(); hex.removeAttribute("aria-invalid"); }); });
      $("rebalance").addEventListener("click", () => { const previous = textValue(); const words = previous.trim().split(/\s+/).filter(Boolean); if (words.length < 4) return; const target = Math.max(2, Math.ceil(words.length / 2)); const next = [words.slice(0, target).join(" "), words.slice(target).join(" ")].filter(Boolean).join("\n"); styles = remapStylesAfterEdit(previous, next, styles); setTextValue(next); clearDemoChoicesOnEdit(); clearProduction(); toolbarStatus.textContent = "Line breaks rebalanced: formatting preserved"; scheduleResize(); schedulePreview(); });
      text.addEventListener("beforeinput", (event) => {
        if (!['insertParagraph', 'insertLineBreak'].includes(event.inputType)) return;
        const range = selectionRange();
        if (!range) return;
        event.preventDefault();
        const previous = textValue();
        const inserted = insertAuthoredNewline(previous, range);
        styles = remapStylesAfterEdit(previous, inserted.value, styles);
        setTextValue(inserted.value, inserted.range);
        clearDemoChoicesOnEdit();
        clearProduction();
        toolbarStatus.textContent = "Line break inserted: formatting preserved";
        scheduleResize();
        schedulePreview();
      });
      text.addEventListener("input", () => { const current = textValue(); const caret = selectionRange(); const bounded = pointLength(current) > 600 ? Array.from(current).slice(0, 600).join("") : current; styles = remapStylesAfterEdit(lastTextValue, bounded, styles); if (bounded !== current) text.textContent = bounded; // Ordinary typing keeps the native DOM intact; only over-limit text is rebuilt. Authored newlines are handled canonically in beforeinput.
        if (bounded !== current) renderEditor(caret); lastTextValue = bounded; clearDemoChoicesOnEdit(); clearProduction(); toolbarStatus.textContent = "Text updated: formatting preserved"; scheduleResize(); schedulePreview(); });
      form.addEventListener("input", (event) => { if (event.target.closest(".card-library") || [text, scale, quoteFontSize, authorFontSize, selectionSize].includes(event.target)) return; clearProduction(); });
      form.addEventListener("change", (event) => { if (!event.target.closest(".card-library") && event.target !== selectionSize) clearProduction(); });
      document.addEventListener("selectionchange", () => { if (document.activeElement === text || text.contains(document.activeElement)) { const range = selection(); savedSelection = range; toolbarStatus.textContent = range ? "Selection ready for formatting" : "Select part of the quote"; if (range && isRibbonStyle()) { const sizes = styles.filter((item) => item.type === "size" && overlap(item, range)); const first = sizes[0]; selectionSize.value = first && sizes.every((item) => item.scale === first.scale) && rangeCovered("size", range) ? String(Math.round(first.scale * 100)) : sizes.length ? "" : "100"; } } });
      async function updatePreview() { const readiness = workspaceReadiness(); if (!readiness.ready) { errors.textContent = readiness.message; errors.hidden = false; status.textContent = readiness.message; syncWorkspaceReadiness(); return; } const arguments_ = currentArguments(), signature = currentSignature(), sequence = ++previewSequence, action = ++actionSequence, revision = editRevision; if (!arguments_.text.trim()) { errors.textContent = "Write or choose a quote before refreshing the preview."; errors.hidden = false; return; } submit.dataset.busy = "true"; produce.dataset.busy = "true"; submit.disabled = true; produce.disabled = true; errors.hidden = true; status.textContent = "Validating…"; try { const result = await request("tools/call", { name:"preview_quote_card", arguments:{ ...arguments_, output_image:false, compact_output:true } }); if (!isCurrentAction(action, revision) || signature !== currentSignature()) return; const structured = extractStructuredContent(result); if (!structured) throw new Error("The preview response was incomplete. Select Update preview to retry."); render(structured); } catch (error) { if (!isCurrentAction(action, revision)) return; errors.textContent = error?.message || "The preview was not refreshed. Try again."; errors.hidden = false; status.textContent = "The preview was not refreshed."; scheduleResize(); } finally { if (isCurrentAction(action, revision)) { delete submit.dataset.busy; delete produce.dataset.busy; submit.disabled = false; produce.disabled = false; syncWorkspaceReadiness(); scheduleResize(); } } }
      form.addEventListener("submit", (event) => { event.preventDefault(); window.clearTimeout(previewTimer); updatePreview(); });
      async function downloadLatestPng() {
        const readiness = workspaceReadiness();
        if (!readiness.ready) { errors.textContent = readiness.message; errors.hidden = false; status.textContent = readiness.message; syncWorkspaceReadiness(); return; }
        const signature = currentSignature();
        if (!textValue().trim()) { errors.textContent = "Write or choose a quote before downloading the card."; errors.hidden = false; return; }
        window.clearTimeout(previewTimer);
        const action = ++actionSequence, revision = editRevision;
        submit.dataset.busy = "true"; produce.dataset.busy = "true";
        submit.disabled = true; produce.disabled = true;
        errors.hidden = true;
        remoteLink.hidden = true;
        try {
          if (deliveryFile && preparedSignature === signature) {
            status.textContent = "Starting the PNG download…";
            await openPreparedDownload();
            return;
          }
          clearProduction(false);
          status.textContent = "Preparing PNG…";
          const result = extractStructuredContent(await request("tools/call", { name:"produce_quote_card", arguments:{ ...currentArguments(), compact_output:true } }));
          if (!isCurrentAction(action, revision) || signature !== currentSignature()) return;
          if (!result) throw new Error("The generation response was incomplete. Select Download PNG to retry.");
          render(result);
          if (!result.produced) { errors.textContent = "The card was not generated. Review the errors and try again."; errors.hidden = false; status.textContent = "Generation did not complete."; return; }
          const prepared = await prepareDownload(result, revision, action);
          if (prepared && isCurrentAction(action, revision) && preparedSignature === currentSignature()) await openPreparedDownload();
        } catch (error) {
          if (!isCurrentAction(action, revision)) return;
          errors.textContent = error?.message || "Unable to generate the PNG.";
          errors.hidden = false;
          status.textContent = "PNG unavailable: try again.";
          scheduleResize();
        } finally {
          if (isCurrentAction(action, revision)) {
            delete submit.dataset.busy; delete produce.dataset.busy;
            submit.disabled = false; produce.disabled = false;
            syncWorkspaceReadiness(); scheduleResize();
          }
        }
      }
      produce.addEventListener("click", downloadLatestPng);
      function startNewWorkspaceCard() {
        if (!workspaceMode) return;
        window.clearTimeout(previewTimer);
        actionSequence += 1; editRevision += 1; draftTransformation = "VERBATIM"; draftEvidenceStatus = "USER_SUPPLIED"; draftAltText = ""; draftUpdateStatus = ""; hasRendered = false; initialContentObserved = true; demoChoices = false; demoAttributionChoice = false; demoPaletteChoice = false; resetDemoLabels(); demoHelper.hidden = true;
        styles = []; graphicSeed = 0; setTextValue(""); attribution.value = ""; attributionDecision.value = "none"; attribution.disabled = true; paletteDecision.value = "neutral";
        ribbonComposition = null; ribbonCandidates = []; ribbonProposalSource = null; ribbonPreviews = []; ribbonLayout = null; pendingReuseComposition = null; savedSelection = null; quoteFontSize.value = ""; authorFontSize.value = ""; renderWarnings([]);
        format.value = "4x5"; scale.value = "100"; scaleValue.textContent = "100%"; position.value = "center"; setStyleChoice("blocks"); writePalette(canonicalNeutralPalette);
        clearProduction(false); image.replaceChildren(); image.hidden = true; meta.textContent = ""; errors.textContent = ""; errors.hidden = true;
        hostState?.clearDraft(); hostState?.setDraft(currentDraft());
        status.textContent = "New card. Write a quote to preview.";
        syncWorkspaceReadiness(); scheduleResize(); text.focus();
      }
      $("newCard").addEventListener("click", startNewWorkspaceCard);
      window.addEventListener("message", (event) => { if (event.source !== window.parent) return; const message = event.data; if (!message || message.jsonrpc !== "2.0") return; if (message.id !== undefined && pending.has(message.id)) { const current = pending.get(message.id); if (message.error) current.reject(new Error(responseErrorMessage(message.error))); else if (hasErrorEnvelope(message.result)) current.reject(new Error(responseErrorMessage(message.result))); else current.resolve(message.result); return; } if (message.method === "ui/notifications/tool-input") receiveInitialInput(message.params); if (["ui/notifications/tool-result","ui/tool-result","tool-result","mcp/tool-result"].includes(message.method)) receiveInitialResult(extractStructuredContent(message.params || message.result)); if (["ui/notifications/tool-call-result","tool-calls/result"].includes(message.method)) receiveInitialResult(extractStructuredContent(message)); });
      if (typeof ResizeObserver === "function") { const observer = new ResizeObserver(scheduleResize); observer.observe(document.documentElement); observer.observe(document.body); }
      setStyleChoice("blocks"); writePalette(paletteInitial, true);
      attribution.disabled = workspaceMode;
      hostState = new QcbHostContext({ workspace:workspaceMode, openai:window.openai, request, document, onRestore:(draft) => { applyInput(draft); editRevision += 1; hostState?.setDraft(currentDraft()); }, onPersistenceStatus:(detail) => { if (!workspaceMode) return; $("workspaceStatus").textContent = detail.message; $("workspaceStatus").dataset.available = String(detail.available); } });
      hostState.initialize({hostContext:{theme:window.openai?.theme}});
      renderSavedBases();
      const aliasPollTimer = window.setInterval(syncFromOpenAiAliases, 250);
      window.addEventListener("pagehide", () => { window.clearInterval(aliasPollTimer); hostState.flush(); hostState.destroy(); });
      syncFromOpenAiAliases(); renderEditor(); syncWorkspaceReadiness({announce:true}); scheduleResize(); let aliasChecks = 0; const aliasTimer = window.setInterval(() => { aliasChecks += 1; syncFromOpenAiAliases(); if (hasRendered) window.clearInterval(aliasTimer); else if (aliasChecks >= 20) { initialAliasGracePassed = true; if (hostInitialized) initializeDemoWorkspace(); window.clearInterval(aliasTimer); } }, 100);
      request("ui/initialize", {
        protocolVersion:"2026-01-26",
        appCapabilities:{ availableDisplayModes:["fullscreen"] },
        appInfo:{ name:"quote-card-builder-ui", version:"__QCB_APP_INFO_VERSION__" },
      }).then((result) => {
        hostCapabilities = result?.hostCapabilities || {};
        hostState.applyHostContext(result?.hostContext || {});
        hostInitialized = true;
        window.parent.postMessage({ jsonrpc:"2.0", method:"ui/notifications/initialized", params:{} }, "*");
        syncFromOpenAiAliases();
        if (hostState.hasRestoredDraft() && workspaceReadiness().ready) schedulePreview(0);
        else if (initialAliasGracePassed) initializeDemoWorkspace();
      }).catch((error) => {
        hostInitialized = true;
        syncFromOpenAiAliases();
        if (initialAliasGracePassed) initializeDemoWorkspace();
        if (!hasRendered) { errors.textContent = "The editor could not connect. Try Update preview or reopen it."; errors.hidden = false; status.textContent = "Connection unavailable."; submit.disabled = false; produce.disabled = false; syncWorkspaceReadiness(); scheduleResize(); }
      });
    </script>
  </body>
</html>'''
    result = (
        html.replace("__QCB_FONT_FACES__", _embedded_font_faces())
        .replace("__QCB_HOST_THEME__", (ASSET_DIR / "host-theme.css").read_text(encoding="utf-8"))
        .replace("__QCB_HOST_CONTEXT__", (ASSET_DIR / "host-context.js").read_text(encoding="utf-8"))
        .replace("__QCB_TOOL_RESULTS__", (ASSET_DIR / "tool-results.js").read_text(encoding="utf-8"))
        .replace("__QCB_PRODUCT_WORDMARK__", _brand_data_uri("quote-card-builder-wordmark.svg", "image/svg+xml"))
        .replace("__QCB_VINCOS_LOCKUP__", _brand_data_uri("vincos-lockup-white.svg", "image/svg+xml"))
        .replace("__QCB_APP_VERSION__", QUOTE_CARD_APP_VERSION)
        .replace("__QCB_APP_INFO_VERSION__", QUOTE_CARD_APP_VERSION.removeprefix("v"))
        .replace("__QCB_WORKSPACE_MODE__", "true" if workspace else "false")
        .replace("__QCB_REDIRECT_ORIGINS__", json.dumps(QUOTE_CARD_DOWNLOAD_REDIRECT_DOMAINS))
        .replace("__QCB_REMOTE_EXPORT_ORIGIN__", json.dumps(_remote_export_origin()))
    )
    # Indentation has no semantic role in this authored HTML/CSS/JavaScript.
    # Keep the self-contained resource below the transport size budget without
    # changing strings, user data, or cached-resource compatibility. Standalone
    # comments in these authored scripts are omitted from the transport copy.
    return "\n".join(line.lstrip() for line in result.splitlines() if not line.lstrip().startswith("//"))
