"""Portable MCP Apps UI for the Quote Card Builder preview tool."""

from __future__ import annotations

import base64
import json
from pathlib import Path


QUOTE_CARD_APP_VERSION = "v1.41"
QUOTE_CARD_PREVIEW_RESOURCE = "ui://quote-card-builder/preview/v1.41.html"
QUOTE_CARD_LEGACY_PREVIEW_RESOURCES = (
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
)
QUOTE_CARD_PREVIEW_MIME_TYPE = "text/html;profile=mcp-app"
QUOTE_CARD_PREVIEW_DOMAIN = "https://quote-card-builder-mcp-960066178304.europe-west8.run.app"
QUOTE_CARD_DOWNLOAD_REDIRECT_DOMAINS = (
    "https://oaisdmntpritalynorth.blob.core.windows.net",
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


def quote_card_preview_html() -> str:
    """Return the self-contained editor component used by compatible hosts."""
    html = r'''<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Quote Card Builder</title>
    <style>
      __QCB_FONT_FACES__
      __QCB_HOST_THEME__
      :root {
        --chrome:#2b1830; --deep:#1b121f; --raised:#35203b; --concrete:#cdd5cf;
        --concrete-light:#e7e9e5; --signal:#b9d936; --signal-dark:#6f8217;
        --lavender:#9b86ad; --lavender-light:#d8cedb; --ink:#171619;
        --paper:#252328; --danger:#ff8b77; --seam:rgba(216,206,219,.24);
        --seam-strong:rgba(216,206,219,.48); --line:rgba(23,22,25,.22);
        --ui:"QCB Barlow","Helvetica Neue",system-ui,sans-serif;
        --mono:"IBM Plex Mono","SFMono-Regular","Cascadia Mono","Roboto Mono",Consolas,monospace;
        color-scheme:dark; background:var(--deep); color:var(--lavender-light);
        font-family:var(--ui); font-synthesis:none;
      }
      * { box-sizing:border-box; }
      html { min-width:320px; background:var(--deep); scrollbar-color:var(--lavender) var(--deep); }
      body { min-width:320px; margin:0; padding:0; background:var(--deep); color:var(--lavender-light); font-size:14px; line-height:1.4; }
      button, input, select { font:inherit; }
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
      input, select, .editor { width:100%; min-height:38px; padding:9px 10px; border:1px solid var(--seam-strong); border-radius:0; background:var(--deep); color:var(--lavender-light); }
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
      input:focus, select:focus, .editor:focus, button:focus-visible { border-color:var(--signal); outline:2px solid var(--signal); outline-offset:2px; }
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
      .meta { color:var(--paper); font-family:var(--mono); font-size:9px; text-align:center; text-transform:uppercase; }
      .errors { padding:10px 14px; border-top:1px solid var(--danger); background:var(--deep); color:var(--danger); font-size:12px; }
      .errors[hidden] { display:none; }
      .delivery { display:grid; grid-template-columns:1fr auto; align-items:center; gap:12px; padding:13px 14px; border-bottom:1px solid var(--seam); background:var(--deep); }
      .delivery[hidden] { display:none; }
      .delivery strong { color:var(--signal); font-family:var(--mono); font-size:10px; font-weight:500; text-transform:uppercase; }
      .delivery-actions { display:flex; align-items:center; justify-content:flex-end; gap:8px; flex-wrap:wrap; }
      .download { min-height:38px; padding:9px 12px; border:1px solid var(--signal); border-radius:0; background:transparent; color:var(--signal); font-weight:700; }
      .download:hover { background:var(--signal); color:var(--ink); }
      .direct-download { color:var(--lavender-light); font-family:var(--mono); font-size:9px; text-decoration:underline; text-underline-offset:3px; }
      .direct-download[hidden] { display:none; }
      .hint { margin:0; color:var(--lavender); font-size:11px; line-height:1.35; }
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
    </style>
  </head>
  <body>
    <main class="shell" aria-labelledby="title" data-version="__QCB_APP_VERSION__">
      <header class="app-header">
        <div class="product-heading"><img class="product-title" id="title" src="__QCB_PRODUCT_WORDMARK__" alt="Quote Card Builder"><div class="product-byline"><span>by</span><img src="__QCB_VINCOS_LOCKUP__" alt="Vincos"></div></div>
        <div class="version-badge" aria-label="Quote Card Builder version __QCB_APP_VERSION__">__QCB_APP_VERSION__</div>
      </header>
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
          <label>Attribution <input id="attribution" maxlength="160" placeholder="Name or leave blank"></label>
          <p class="hint">Select words in the quote and use B, I, U, A, O, or H. The canonical renderer preserves the selected ranges.</p>
        </fieldset>

        <fieldset>
          <legend>Style</legend>
          <div class="style-picker" id="stylePicker" role="group" aria-label="Choose a visual style">
            <button type="button" data-style-choice="blocks" aria-pressed="true">Blocks</button>
            <button type="button" data-style-choice="cutouts" aria-pressed="false">Cutouts</button>
            <button type="button" data-style-choice="constellations" aria-pressed="false">Constellations</button>
            <button type="button" data-style-choice="gradient" aria-pressed="false">Gradient</button>
            <button class="plain-style" type="button" data-style-choice="plain" aria-pressed="false">Hide pattern</button>
          </div>
          <p class="hint" id="styleHint">Blocks selected. Vary the pattern to explore another deterministic composition.</p>
          <div class="variation" id="patternVariation">
            <button type="button" id="patternPrevious">Previous</button>
            <button type="button" id="patternNext">Vary pattern</button>
            <output id="patternSeed" aria-live="polite">Seed 0</output>
          </div>
        </fieldset>

        <fieldset>
          <legend>Composition</legend>
          <label for="format">Format <select id="format"><option value="4x5" selected>4:5 portrait</option><option value="1x1">1:1 square</option></select></label>
          <div class="range-row"><label for="scale">Scale from maximum</label><output id="scaleValue" for="scale">100%</output></div>
          <input id="scale" type="range" min="80" max="100" value="100" step="1">
          <div class="range-row"><label for="position">Vertical position</label><select id="position"><option value="upper">Upper</option><option value="center" selected>Center</option><option value="lower">Lower</option></select></div>
        </fieldset>

        <fieldset>
          <legend>Card palette</legend>
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
          <button class="primary" id="produce" type="button"><span class="action-title">Generate PNG</span><span class="action-detail">Prepare image</span></button>
        </div>
      </form>
      <div class="status" id="status" role="status" aria-live="polite">Waiting for a quote card.</div>
      <div class="delivery" id="delivery" hidden><strong id="deliveryName">PNG ready</strong><div class="delivery-actions"><button class="download" id="download" type="button" disabled>Open PNG</button><button class="direct-download" id="handoff" type="button" hidden>Send link to chat</button></div></div>
      <section class="preview" aria-label="Quote card preview"><div id="image" class="svg-preview" role="img" aria-label="" hidden></div><div class="meta" id="meta"></div></section>
      <div class="errors" id="errors" role="alert" hidden></div>
    </main>
    <script>__QCB_HOST_CONTEXT__</script>
    <script>__QCB_TOOL_RESULTS__</script>
    <script>
      let hostState = null;
      const pending = new Map(); let nextId = 1; let hasRendered = false;
      const $ = (id) => document.getElementById(id);
      const form = $("form"), text = $("text"), attribution = $("attribution");
      const direction = { value: "editorial" }, paletteName = $("paletteName"), palette = $("palette"), palettePreset = $("palettePreset");
      const format = $("format"), scale = $("scale"), scaleValue = $("scaleValue"), position = $("position");
      const submit = $("submit"), produce = $("produce"), status = $("status"), image = $("image"), meta = $("meta"), errors = $("errors"), toolbarStatus = $("toolbarStatus");
      const delivery = $("delivery"), deliveryName = $("deliveryName"), download = $("download"), handoff = $("handoff");
      const allowedDownloadOrigins = new Set(__QCB_REDIRECT_ORIGINS__);
      let styles = []; let lastTextValue = ""; let resizeFrame = 0; let deliveryUrl = ""; let deliveryFileId = ""; let deliveryFilename = ""; let deliveryFile = null; let hostCapabilities = {}; let previewTimer = 0; let previewSequence = 0; let graphicSeed = 0; let editRevision = 0; let actionSequence = 0;
      let paletteInitial = { name:"Initial palette", colors:{ primary:"#072743", accent:"#E3F4FF", background:"#FEFDFB", text:"#323232" } };
      const styleOptions = {
        blocks:{ direction:"editorial", variant:"cover", label:"Blocks" },
        cutouts:{ direction:"editorial", variant:"cutouts", label:"Cutouts" },
        constellations:{ direction:"contextual", variant:"constellations", label:"Constellations" },
        gradient:{ direction:"editorial", variant:"gradient", label:"Gradient" },
        plain:{ direction:"editorial", variant:"default", hidden:true, label:"Hide pattern" },
      };
      const palettePresets = {
        forest:{ name:"Bosco", colors:{ primary:"#173D35", accent:"#C8E0CC", background:"#F6F8F0", text:"#173D35" } },
        paper:{ name:"Carta", colors:{ primary:"#072743", accent:"#E3F4FF", background:"#FEFDFB", text:"#323232" } },
        warm:{ name:"Calda", colors:{ primary:"#5A2C2A", accent:"#E8B4A8", background:"#FFF8F2", text:"#332423" } },
      };
      const paletteFields = { primary:["primary","primaryHex"], accent:["accent","accentHex"], background:["background","backgroundHex"], text:["textColor","textHex"] };
      const hexPattern = /^#[0-9a-f]{6}$/i;
      function pointLength(value) { return Array.from(String(value || "")).length; }
      function cpOffset(value, utf16Index) { return pointLength(String(value || "").slice(0, utf16Index)); }
      function normalizeStyles(value) { const grouped = new Map(); (Array.isArray(value) ? value : []).forEach((item) => { if (!item || !["bold","italic","underline","highlight","accent","outline"].includes(item.type) || !Number.isInteger(item.start) || !Number.isInteger(item.end) || item.start >= item.end) return; if (!grouped.has(item.type)) grouped.set(item.type, []); grouped.get(item.type).push({ start:item.start, end:item.end, type:item.type }); }); const merged = []; grouped.forEach((ranges, type) => { ranges.sort((first, second) => first.start - second.start || first.end - second.end); ranges.forEach((range) => { const previous = merged.at(-1); if (previous?.type === type && range.start <= previous.end) previous.end = Math.max(previous.end, range.end); else merged.push({ ...range }); }); }); return merged.sort((first, second) => first.start - second.start || first.end - second.end || first.type.localeCompare(second.type)); }
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
                span.className = signature.split(" ").map((kind) => `style-${kind}`).join(" ");
                span.textContent = content;
                block.appendChild(span);
              }
            };
            for (let index = 0; index < line.length; index += 1) {
              const signature = styles.filter((item) => item.start <= globalOffset + index && item.end > globalOffset + index).map((item) => item.type).sort().join(" ");
              if (signature !== previous) { appendRun(index, previous); runStart = index; previous = signature; }
            }
            appendRun(line.length, previous);
          }
          fragment.appendChild(block);
          globalOffset += line.length + (lineIndex < lines.length - 1 ? 1 : 0);
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
          return first && last ? [{ start:first.index, end:last.index + 1, type:item.type }] : [];
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
      }
      function readLines() { const value = textValue(); return value.includes("\n") ? value.split("\n") : null; }
      function normalizeHex(value) { const normalized = String(value || "").trim().toUpperCase(); return hexPattern.test(normalized) ? normalized : null; }
      function readPalette() { return { name:paletteName.value.trim() || "Custom palette", colors:Object.fromEntries(Object.entries(paletteFields).map(([key, ids]) => [key, normalizeHex($(ids[1]).value) || $(ids[0]).value.toUpperCase()])) }; }
      function writePalette(value, rememberInitial = false) { if (!value?.colors) return; const colors = {}; Object.entries(paletteFields).forEach(([key, ids]) => { const color = normalizeHex(value.colors[key]); if (!color) return; colors[key] = color; $(ids[0]).value = color; $(ids[1]).value = color; }); if (Object.keys(colors).length !== 4) return; paletteName.value = String(value.name || "Custom palette"); if (rememberInitial) paletteInitial = { name:paletteName.value, colors:{ ...colors } }; syncPalettePreset(); }
      function samePalette(first, second) { return Object.keys(paletteFields).every((key) => normalizeHex(first?.colors?.[key]) === normalizeHex(second?.colors?.[key])); }
      function syncPalettePreset() { const current = readPalette(); if (samePalette(current, paletteInitial)) palettePreset.value = "initial"; else { const match = Object.entries(palettePresets).find(([, value]) => samePalette(current, value)); palettePreset.value = match?.[0] || "custom"; } }
      function currentArguments() { const value = textValue(), style = selectedStyle(); return { text:value, format:format.value, attribution:attribution.value, styles:styles.length ? styles : [], lines:readLines(), direction:style.direction, graphic_mode:style.hidden ? "hidden" : "auto", graphic_variant:style.variant, graphic_seed:graphicSeed, text_scale:Number(scale.value) / 100, vertical_position:position.value, palette:readPalette() }; }
      function currentSignature() { return JSON.stringify(currentArguments()); }
      function clearProduction(invalidate = true) { if (invalidate) { if (hostState) { hostState.setDraft(currentArguments()); hostState.setImageIds([]); hostState.setPrivateContent({}); } editRevision += 1; actionSequence += 1; submit.disabled = false; produce.disabled = false; } if (deliveryUrl && deliveryUrl.startsWith("blob:")) URL.revokeObjectURL(deliveryUrl); deliveryUrl = ""; deliveryFileId = ""; deliveryFilename = ""; deliveryFile = null; download.disabled = true; download.textContent = "Download PNG"; handoff.hidden = true; handoff.disabled = false; delivery.hidden = true; }
      function selectedStyleKey() { return document.querySelector('[data-style-choice][aria-pressed="true"]')?.dataset.styleChoice || "blocks"; }
      function selectedStyle() { return styleOptions[selectedStyleKey()] || styleOptions.blocks; }
      function styleKeyFromInput(input) { if (input?.graphic_mode === "hidden") return "plain"; if (styleOptions[input?.style] && !styleOptions[input.style].hidden) return input.style; const match = Object.entries(styleOptions).find(([, option]) => !option.hidden && option.direction === input?.direction && option.variant === input?.graphic_variant); return match?.[0] || "blocks"; }
      function updateStyleState() { const selected = selectedStyle(); direction.value = selected.direction; $("styleHint").textContent = selected.hidden ? "Pattern hidden. Choose a style to restore it." : `${selected.label} selected. Vary the pattern to explore another deterministic composition.`; $("patternVariation").hidden = Boolean(selected.hidden); $("patternSeed").textContent = `Seed ${graphicSeed}`; $("patternPrevious").disabled = graphicSeed === 0; }
      function setStyleChoice(key) { if (!styleOptions[key]) key = "blocks"; document.querySelectorAll("[data-style-choice]").forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.styleChoice === key))); updateStyleState(); }
      const REQUEST_TIMEOUT_MS = 30000;
      function responseErrorMessage(value, fallback = "The host returned an error.") { const visited = new Set(); function visit(item) { if (item instanceof Error && item.message) return item.message; if (typeof item === "string" && item.trim()) return item.trim(); if (!item || typeof item !== "object" || visited.has(item)) return null; visited.add(item); if (item.message) { const message = visit(item.message); if (message) return message; } if (item.error) { const message = visit(item.error); if (message) return message; } if (item.data) { const message = visit(item.data); if (message) return message; } for (const key of ["call_tool_result", "mcp_tool_result", "result", "params"]) { const message = visit(item[key]); if (message) return message; } if (Array.isArray(item.content)) { for (const part of item.content) { if (part?.text) { const message = visit(part.text); if (message) return message; } } } return null; } return visit(value) || fallback; }
      function hasErrorEnvelope(value) { const visited = new Set(); function visit(item) { if (!item || typeof item !== "object" || visited.has(item)) return false; visited.add(item); if (item.isError === true || item.error) return true; return [item.result, item.params, item.toolResult, item.tool_result, item.output, item.call_tool_result, item.mcp_tool_result].some(visit); } return visit(value); }
      function request(method, params, timeoutMs = REQUEST_TIMEOUT_MS) { const id = nextId++; return new Promise((resolve, reject) => { let settled = false; const finish = (callback, value) => { if (settled) return; settled = true; pending.delete(id); clearTimeout(timeoutId); callback(value); }; const timeoutId = setTimeout(() => finish(reject, new Error(`The host did not respond to ${method}.`)), timeoutMs); pending.set(id, { resolve:(value) => finish(resolve, value), reject:(error) => finish(reject, error instanceof Error ? error : new Error(responseErrorMessage(error))) }); try { window.parent.postMessage({ jsonrpc:"2.0", id, method, params }, "*"); } catch (error) { finish(reject, error); } }); }
      function schedulePreview(delay = 160) { window.clearTimeout(previewTimer); previewTimer = window.setTimeout(() => updatePreview(), delay); }
      function showErrors(items) { const messages = (items || []).map((item) => item.message || String(item)); errors.textContent = messages.join(" "); errors.hidden = messages.length === 0; }
      function extractStructuredContent(message, metadata) {
        const result = QcbToolResults.read(message, metadata);
        if (hasErrorEnvelope(message) || hasErrorEnvelope(metadata)) return result || { valid:false, rendered:false, errors:[{ message:responseErrorMessage(metadata || message, "The host returned an error while running the tool.") }] };
        return result;
      }
      function safeInlineSvg(svgText) { if (typeof svgText !== "string" || !svgText.trim()) return null; const parsed = new DOMParser().parseFromString(svgText, "image/svg+xml"); const root = parsed.documentElement; if (!root || root.nodeName.toLowerCase() !== "svg" || parsed.querySelector("parsererror")) return null; root.querySelectorAll("script, foreignObject").forEach((node) => node.remove()); root.querySelectorAll("*").forEach((node) => [...node.attributes].forEach((attribute) => { const name = attribute.name.toLowerCase(); const value = attribute.value.trim().toLowerCase(); if (name.startsWith("on") || ((name === "href" || name === "xlink:href") && !value.startsWith("#"))) node.removeAttribute(attribute.name); })); return document.importNode(root, true); }
      function render(result) { if (!result || typeof result.valid !== "boolean" || typeof result.rendered !== "boolean") { errors.textContent = "The preview response was incomplete. Select Update preview to retry."; errors.hidden = false; status.textContent = "Preview response unavailable."; scheduleResize(); return; } if (result.editor_state) { const editorState = { ...result.editor_state }; if (!editorState.palette && result.palette) editorState.palette = { name:result.profile || "Initial palette", colors:result.palette }; applyInput(editorState); } hasRendered = true; if (hostState) { hostState.receiveToolResult(result); hostState.acceptToolInput(currentArguments()); } showErrors(result.errors); const svgNode = result.valid && result.rendered ? safeInlineSvg(result.svg) : null; if (!svgNode) { image.replaceChildren(); image.hidden = true; meta.textContent = "The preview is unavailable."; status.textContent = "Review the errors and try again."; scheduleResize(); return; } if (result.format) format.value = result.format; image.replaceChildren(svgNode); image.setAttribute("aria-label", result.alt_text || "Quote card preview"); image.hidden = false; meta.textContent = `${result.profile} · ${selectedStyle().label} · ${result.format} · ${Math.round((result.text_scale || Number(scale.value) / 100) * 100)}% · ${result.vertical_position || position.value}`; status.textContent = result.produced ? "Quote card generated by the canonical renderer." : "Preview validated by the canonical renderer."; scheduleResize(); }
      function applyInput(params) { const input = params?.arguments || params; if (!input) return; if (Array.isArray(input.styles)) styles = normalizeStyles(input.styles); if (typeof input.text === "string") setTextValue(input.text); else renderEditor(); if (["4x5", "1x1"].includes(input.format)) format.value = input.format; if (typeof input.attribution === "string") attribution.value = input.attribution; setStyleChoice(styleKeyFromInput(input)); if (Number.isInteger(input.graphic_seed) && input.graphic_seed >= 0 && input.graphic_seed <= 999999) graphicSeed = input.graphic_seed; if (input.palette?.colors) writePalette(input.palette, !hasRendered); else if (!hasRendered) writePalette(paletteInitial, true); if (typeof input.text_scale === "number") { scale.value = String(Math.round(input.text_scale * 100)); scaleValue.textContent = `${scale.value}%`; } if (typeof input.vertical_position === "string") position.value = input.vertical_position; updateStyleState(); scheduleResize(); }
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
      function canHostDownload(snapshot = currentDeliverySnapshot()) { return Boolean(snapshot?.file && hostCapabilities?.downloadFile); }
      function canSendImageToChat(snapshot = currentDeliverySnapshot()) { return Boolean(snapshot?.file && hostCapabilities?.message?.image); }
      async function fileToBase64(file) {
        const bytes = new Uint8Array(await file.arrayBuffer());
        let binary = "";
        for (let offset = 0; offset < bytes.length; offset += 32768) {
          binary += String.fromCharCode(...bytes.subarray(offset, offset + 32768));
        }
        return btoa(binary);
      }
      async function requestNativeDownload(snapshot = currentDeliverySnapshot()) {
        if (!canHostDownload(snapshot)) throw new Error("This host does not advertise native file downloads.");
        status.textContent = "Opening the save dialog…";
        scheduleResize();
        const filename = snapshot.filename || "quote-card.png";
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
      async function sendPreparedImageToChat(snapshot = currentDeliverySnapshot()) {
        if (!canSendImageToChat(snapshot)) throw new Error("This host cannot receive PNG images from the widget.");
        status.textContent = "Sending the PNG to chat…";
        scheduleResize();
        const filename = snapshot.filename || "quote-card.png";
        const blob = await fileToBase64(snapshot.file);
        const result = await withTimeout(
          request("ui/message", {
            role:"user",
            content:[
              { type:"text", text:"Quote Card Builder generated " + filename + ". Return the image as generated; do not invoke the builder again." },
              { type:"image", data:blob, mimeType:"image/png" },
            ],
          }),
          30000,
          "The host did not accept the PNG hand-off.",
        );
        if (result?.isError) throw new Error("The PNG hand-off was denied by the host.");
        if (!isCurrentDelivery(snapshot)) return false;
        status.textContent = "PNG sent to chat. Open the image there to save it.";
        return true;
      }
      function canHandoffToChat(snapshot = currentDeliverySnapshot()) {
        const bridge = window.openai;
        return Boolean(snapshot?.fileId && snapshot?.url?.startsWith("https:") && bridge?.sendFollowUpMessage);
      }
      async function handoffPreparedDownload(snapshot = currentDeliverySnapshot()) {
        if (!canHandoffToChat(snapshot)) throw new Error("This ChatGPT client cannot send the PNG link to the chat.");
        const bridge = window.openai;
        status.textContent = "Sending the PNG link to chat…";
        handoff.disabled = true;
        scheduleResize();
        try {
          if (typeof hostState !== "undefined" && hostState) {
            hostState.setPrivateContent({filename:snapshot.filename});
            hostState.setImageIds([snapshot.fileId]);
          } else if (typeof bridge.setWidgetState === "function") {
            bridge.setWidgetState({
              modelContent:"Quote Card Builder generated " + snapshot.filename + ". Preserve the image exactly as generated and do not invoke the builder again.",
              privateContent:{ filename:snapshot.filename },
              imageIds:[snapshot.fileId],
            });
          }
          const prompt = "The PNG “" + snapshot.filename + "” is ready. Return only a clickable Markdown link labelled “Download PNG” for this exact temporary URL, without invoking Quote Card Builder again:\n" + snapshot.url;
          await withTimeout(
            bridge.sendFollowUpMessage({ prompt, scrollToBottom:true }),
            5000,
            "ChatGPT did not accept the PNG hand-off.",
          );
          if (!isCurrentDelivery(snapshot)) return false;
          status.textContent = "PNG link sent to chat. Use Download PNG in the conversation.";
          return true;
        } finally {
          if (isCurrentDelivery(snapshot)) {
            handoff.disabled = false;
            scheduleResize();
          }
        }
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
        deliveryFile = file;
        deliveryFilename = downloadableName;
        const bridge = window.openai;
        if (!canHostDownload() && !canSendImageToChat() && bridge?.uploadFile && bridge?.getFileDownloadUrl) {
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
            errors.textContent = error?.message || "Unable to prepare the PNG in ChatGPT.";
            errors.hidden = false;
            status.textContent = "PNG unavailable: try again.";
            scheduleResize();
            return;
          }
        } else if (!canHostDownload() && !canSendImageToChat()) {
          deliveryUrl = URL.createObjectURL(file);
        }
        if (!isCurrentAction(sequence, revision)) return false;
        const hostCanDownload = canHostDownload();
        const hostCanSendImage = canSendImageToChat();
        const bridgeCanOpen = Boolean(deliveryFileId && window.openai?.openExternal);
        const bridgeCanHandoff = canHandoffToChat();
        download.textContent = hostCanDownload ? "Download PNG" : hostCanSendImage ? "Send PNG to chat" : bridgeCanOpen ? "Open PNG" : bridgeCanHandoff ? "Send link to chat" : "Save PNG";
        handoff.hidden = !(bridgeCanOpen && bridgeCanHandoff);
        download.disabled = false; deliveryName.textContent = downloadableName; delivery.hidden = false; scheduleResize();
        status.textContent = hostCanDownload
          ? "PNG ready. Download it through the host save dialog."
          : hostCanSendImage
            ? "PNG ready. Send the image to the conversation."
          : bridgeCanOpen
          ? "PNG ready. Open it, or send its link to the chat."
          : bridgeCanHandoff
            ? "PNG ready. Send its temporary download link to the chat."
            : "PNG ready. Save it from this host.";
        return true;
      }
      async function openPreparedDownload() {
        const snapshot = currentDeliverySnapshot();
        if (!snapshot.file && !snapshot.url && !snapshot.fileId) return;
        download.disabled = true;
        status.textContent = canHostDownload(snapshot) ? "Opening the save dialog…" : canSendImageToChat(snapshot) ? "Sending the PNG to chat…" : canHandoffToChat(snapshot) && !window.openai?.openExternal ? "Sending the PNG link to chat…" : "Opening PNG…";
        scheduleResize();
        try {
          const bridge = window.openai;
          if (canHostDownload(snapshot)) {
            await requestNativeDownload(snapshot);
          } else if (canSendImageToChat(snapshot)) {
            await sendPreparedImageToChat(snapshot);
          } else if (snapshot.fileId && bridge?.openExternal) {
            await withTimeout(
              bridge.openExternal({ href:snapshot.url, redirectUrl:false }),
              5000,
              "ChatGPT did not respond to the open request.",
            );
            if (!isCurrentDelivery(snapshot)) return;
            status.textContent = "Open request sent. If no tab appeared, send the link to chat.";
          } else if (canHandoffToChat(snapshot)) {
            await handoffPreparedDownload(snapshot);
          } else if (snapshot.url.startsWith("blob:")) {
            const link = document.createElement("a");
            link.href = snapshot.url; link.download = snapshot.filename || "quote-card.png";
            link.style.display = "none"; document.body.append(link); link.click(); link.remove();
            if (!isCurrentDelivery(snapshot)) return;
            status.textContent = "Save request sent to this host.";
          } else {
            throw new Error("This host cannot open the PNG or send it to the chat.");
          }
        } catch (error) {
          if (!isCurrentDelivery(snapshot)) return;
          errors.textContent = error?.message || "Unable to open the PNG.";
          errors.hidden = false;
          status.textContent = "PNG unavailable: try again.";
        } finally { if (isCurrentDelivery(snapshot)) { download.disabled = false; scheduleResize(); } }
      }
      function receiveInitialInput(input) { if (!hasRendered && editRevision === 0 && !hostState?.hasRestoredDraft()) applyInput(input); }
      function receiveInitialResult(result) { if (!hasRendered && editRevision === 0 && !hostState?.hasRestoredDraft()) render(result); }
      function syncFromOpenAiAliases() {
        const bridge = window.openai;
        if (!bridge || hasRendered || editRevision > 0 || hostState?.hasRestoredDraft()) return;
        receiveInitialInput(bridge.toolInput);
        if (bridge.toolOutput || bridge.toolResponseMetadata) receiveInitialResult(extractStructuredContent(bridge.toolOutput, bridge.toolResponseMetadata));
      }
      document.querySelectorAll("[data-style]").forEach((button) => { button.addEventListener("mousedown", (event) => event.preventDefault()); button.addEventListener("click", () => applyStyle(button.dataset.style)); });
      download.addEventListener("click", openPreparedDownload);
      handoff.addEventListener("click", async () => { try { await handoffPreparedDownload(); } catch (error) { errors.textContent = error?.message || "Unable to send the PNG link to chat."; errors.hidden = false; status.textContent = "PNG hand-off failed."; scheduleResize(); } });
      document.querySelectorAll("[data-style-choice]").forEach((button) => button.addEventListener("click", () => { setStyleChoice(button.dataset.styleChoice); clearProduction(); schedulePreview(0); }));
      $("patternPrevious").addEventListener("click", () => { graphicSeed = (graphicSeed + 999999) % 1000000; updateStyleState(); clearProduction(); schedulePreview(0); });
      $("patternNext").addEventListener("click", () => { graphicSeed = (graphicSeed + 1) % 1000000; updateStyleState(); clearProduction(); schedulePreview(0); });
      palettePreset.addEventListener("change", () => { const chosen = palettePreset.value === "initial" ? paletteInitial : palettePresets[palettePreset.value]; if (chosen) writePalette(chosen); clearProduction(); schedulePreview(0); });
      $("paletteReset").addEventListener("click", () => { writePalette(paletteInitial); clearProduction(); schedulePreview(0); });
      format.addEventListener("change", () => { clearProduction(); scheduleResize(); schedulePreview(0); }); scale.addEventListener("input", () => { scaleValue.textContent = `${scale.value}%`; clearProduction(); scheduleResize(); schedulePreview(); }); position.addEventListener("change", () => { clearProduction(); schedulePreview(0); });
      paletteName.addEventListener("input", () => { clearProduction(); schedulePreview(); });
      Object.entries(paletteFields).forEach(([, ids]) => { const picker = $(ids[0]), hex = $(ids[1]); picker.addEventListener("input", () => { hex.value = picker.value.toUpperCase(); syncPalettePreset(); clearProduction(); schedulePreview(); }); hex.addEventListener("input", () => { const value = normalizeHex(hex.value); hex.setAttribute("aria-invalid", String(!value)); if (value) picker.value = value; syncPalettePreset(); clearProduction(); if (value) schedulePreview(); }); hex.addEventListener("blur", () => { const value = normalizeHex(hex.value); hex.value = value || picker.value.toUpperCase(); hex.removeAttribute("aria-invalid"); }); });
      $("rebalance").addEventListener("click", () => { const previous = textValue(); const words = previous.trim().split(/\s+/).filter(Boolean); if (words.length < 4) return; const target = Math.max(2, Math.ceil(words.length / 2)); const next = [words.slice(0, target).join(" "), words.slice(target).join(" ")].filter(Boolean).join("\n"); styles = remapStylesAfterEdit(previous, next, styles); setTextValue(next); clearProduction(); toolbarStatus.textContent = "Line breaks rebalanced: formatting preserved"; scheduleResize(); });
      text.addEventListener("beforeinput", (event) => {
        if (!['insertParagraph', 'insertLineBreak'].includes(event.inputType)) return;
        const range = selectionRange();
        if (!range) return;
        event.preventDefault();
        const previous = textValue();
        const inserted = insertAuthoredNewline(previous, range);
        styles = remapStylesAfterEdit(previous, inserted.value, styles);
        setTextValue(inserted.value, inserted.range);
        clearProduction();
        toolbarStatus.textContent = "Line break inserted: formatting preserved";
        scheduleResize();
      });
      text.addEventListener("input", () => { const current = textValue(); const caret = selectionRange(); const bounded = pointLength(current) > 600 ? Array.from(current).slice(0, 600).join("") : current; styles = remapStylesAfterEdit(lastTextValue, bounded, styles); if (bounded !== current) text.textContent = bounded; // Ordinary typing keeps the native DOM intact; only over-limit text is rebuilt. Authored newlines are handled canonically in beforeinput.
        if (bounded !== current) renderEditor(caret); lastTextValue = bounded; clearProduction(); toolbarStatus.textContent = "Text updated: formatting preserved"; scheduleResize(); });
      form.addEventListener("input", (event) => { if (event.target !== text && event.target !== scale) clearProduction(); });
      form.addEventListener("change", clearProduction);
      document.addEventListener("selectionchange", () => { if (document.activeElement === text || text.contains(document.activeElement)) toolbarStatus.textContent = selection() ? "Selection ready for formatting" : "Select part of the quote"; });
      async function updatePreview() { const arguments_ = currentArguments(), signature = currentSignature(), sequence = ++previewSequence, action = ++actionSequence, revision = editRevision; if (!arguments_.text.trim()) { errors.textContent = "Write or choose a quote before refreshing the preview."; errors.hidden = false; return; } submit.disabled = true; produce.disabled = true; errors.hidden = true; status.textContent = "Validating…"; try { const result = await request("tools/call", { name:"preview_quote_card", arguments:{ ...arguments_, output_image:false, compact_output:true } }); if (!isCurrentAction(action, revision) || signature !== currentSignature()) return; const structured = extractStructuredContent(result); if (!structured) throw new Error("The preview response was incomplete. Select Update preview to retry."); render(structured); } catch (error) { if (!isCurrentAction(action, revision)) return; errors.textContent = error?.message || "The preview was not refreshed. Try again."; errors.hidden = false; status.textContent = "The preview was not refreshed."; scheduleResize(); } finally { if (isCurrentAction(action, revision)) { submit.disabled = false; produce.disabled = false; scheduleResize(); } } }
      form.addEventListener("submit", (event) => { event.preventDefault(); window.clearTimeout(previewTimer); updatePreview(); });
      produce.addEventListener("click", async () => { const arguments_ = currentArguments(), signature = currentSignature(); if (!arguments_.text.trim()) { errors.textContent = "Write or choose a quote before generating the card."; errors.hidden = false; return; } window.clearTimeout(previewTimer); clearProduction(); const action = ++actionSequence, revision = editRevision; submit.disabled = true; produce.disabled = true; errors.hidden = true; status.textContent = "Generating…"; try { const result = extractStructuredContent(await request("tools/call", { name:"produce_quote_card", arguments:{ ...arguments_, compact_output:true } })); if (!isCurrentAction(action, revision) || signature !== currentSignature()) return; if (!result) throw new Error("The generation response was incomplete. Select Generate PNG to retry."); render(result); if (result?.produced) await prepareDownload(result, revision, action); else { errors.textContent = "The card was not generated. Review the errors and try again."; errors.hidden = false; } } catch (error) { if (!isCurrentAction(action, revision)) return; errors.textContent = error?.message || "The card was not generated. Try again."; errors.hidden = false; status.textContent = "Generation did not complete."; scheduleResize(); } finally { if (isCurrentAction(action, revision)) { submit.disabled = false; produce.disabled = false; scheduleResize(); } } });
      window.addEventListener("message", (event) => { if (event.source !== window.parent) return; const message = event.data; if (!message || message.jsonrpc !== "2.0") return; if (message.id !== undefined && pending.has(message.id)) { const current = pending.get(message.id); if (message.error) current.reject(new Error(responseErrorMessage(message.error))); else if (hasErrorEnvelope(message.result)) current.reject(new Error(responseErrorMessage(message.result))); else current.resolve(message.result); return; } if (message.method === "ui/notifications/tool-input") receiveInitialInput(message.params); if (["ui/notifications/tool-result","ui/tool-result","tool-result","mcp/tool-result"].includes(message.method)) receiveInitialResult(extractStructuredContent(message.params || message.result)); if (["ui/notifications/tool-call-result","tool-calls/result"].includes(message.method)) receiveInitialResult(extractStructuredContent(message)); });
      if (typeof ResizeObserver === "function") { const observer = new ResizeObserver(scheduleResize); observer.observe(document.documentElement); observer.observe(document.body); }
      setStyleChoice("blocks"); writePalette(paletteInitial, true);
      hostState = new QcbHostContext({ openai:window.openai, request, document, onRestore:(draft) => { applyInput(draft); editRevision += 1; } });
      hostState.initialize({hostContext:{theme:window.openai?.theme}});
      window.addEventListener("pagehide", () => { hostState.flush(); hostState.destroy(); });
      syncFromOpenAiAliases(); renderEditor(); scheduleResize(); let aliasChecks = 0; const aliasTimer = window.setInterval(() => { aliasChecks += 1; syncFromOpenAiAliases(); if (hasRendered || aliasChecks >= 20) window.clearInterval(aliasTimer); }, 100);
      request("ui/initialize", {
        protocolVersion:"2026-01-26",
        appCapabilities:{},
        appInfo:{ name:"quote-card-builder-ui", version:"0.3.1" },
      }).then((result) => {
        hostCapabilities = result?.hostCapabilities || {};
        hostState.applyHostContext(result?.hostContext || {});
        window.parent.postMessage({ jsonrpc:"2.0", method:"ui/notifications/initialized", params:{} }, "*");
        syncFromOpenAiAliases();
        if (hostState.hasRestoredDraft()) schedulePreview(0);
      }).catch((error) => {
        syncFromOpenAiAliases();
        if (!hasRendered) { errors.textContent = "The editor could not connect. Try Update preview or reopen it."; errors.hidden = false; status.textContent = "Connection unavailable."; submit.disabled = false; produce.disabled = false; scheduleResize(); }
      });
    </script>
  </body>
</html>'''
    return (
        html.replace("__QCB_FONT_FACES__", _embedded_font_faces())
        .replace("__QCB_HOST_THEME__", (ASSET_DIR / "host-theme.css").read_text(encoding="utf-8"))
        .replace("__QCB_HOST_CONTEXT__", (ASSET_DIR / "host-context.js").read_text(encoding="utf-8"))
        .replace("__QCB_TOOL_RESULTS__", (ASSET_DIR / "tool-results.js").read_text(encoding="utf-8"))
        .replace("__QCB_PRODUCT_WORDMARK__", _brand_data_uri("quote-card-builder-wordmark.svg", "image/svg+xml"))
        .replace("__QCB_VINCOS_LOCKUP__", _brand_data_uri("vincos-lockup-white.svg", "image/svg+xml"))
        .replace("__QCB_APP_VERSION__", QUOTE_CARD_APP_VERSION)
        .replace("__QCB_REDIRECT_ORIGINS__", json.dumps(QUOTE_CARD_DOWNLOAD_REDIRECT_DOMAINS))
    )
