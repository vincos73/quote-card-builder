import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


class McpUiReliabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if shutil.which("node") is None:
            raise unittest.SkipTest("Node.js non disponibile: test affidabilità UI saltato")
        import sys

        if str(SCRIPTS) not in sys.path:
            sys.path.insert(0, str(SCRIPTS))
        import mcp_app

        cls.html = mcp_app.quote_card_preview_html()
        cls.workspace_html = mcp_app.quote_card_preview_html(workspace=True)
        cls.tool_results = (ROOT / "assets/mcp-editor/tool-results.js").read_text()
        cls.app_version = mcp_app.QUOTE_CARD_APP_VERSION

    def _run(self, source, *, module=False):
        command = ["node"]
        if module:
            command.append("--input-type=module")
        command.extend(["-e", source])
        completed = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)

    def test_preview_caption_uses_a_scoped_class_not_svg_meta(self):
        self.assertIn('class="qcb-preview-caption" id="meta"', self.workspace_html)
        self.assertIn(".qcb-preview-caption {", self.workspace_html)
        self.assertNotIn(".meta {", self.workspace_html)
        self.assertIn(self.app_version, self.workspace_html)

    def test_request_timeout_rejects_and_removes_pending_entry(self):
        request_source = self.html.split(
            "const REQUEST_TIMEOUT_MS", 1
        )[1].split("function schedulePreview", 1)[0].replace(" = 30000;", " = 15;", 1)
        self._run(
            """
const pending = new Map();
let nextId = 1;
const posted = [];
const window = { parent:{ postMessage(message) { posted.push(message); } } };
"""
            + "const REQUEST_TIMEOUT_MS"
            + request_source
            + r'''
let rejected = null;
try { await request("ui/initialize", {}); }
catch (error) { rejected = error; }
if (!rejected || !rejected.message.includes("ui/initialize")) throw new Error("timeout message did not name the request");
if (pending.size !== 0) throw new Error(`timed-out request remained pending: ${pending.size}`);
if (posted.length !== 1 || posted[0].method !== "ui/initialize") throw new Error("request was not posted once");
''',
            module=True,
        )

    def test_prepare_download_discards_delayed_raster_after_edit(self):
        delivery_source = "function validatedDownloadUrl" + self.html.split(
            "function validatedDownloadUrl", 1
        )[1].split("async function openPreparedDownload", 1)[0]
        self._run(
            r'''
let deliveryUrl = "";
let deliveryFileId = "";
let deliveryFilename = "";
let deliveryFile = null;
let hostCapabilities = {};
let editRevision = 0;
let actionSequence = 1;
const hostState = null;
const download = { disabled:true, textContent:"" };
const handoff = { hidden:true, disabled:false };
const deliveryName = { textContent:"" };
const delivery = { hidden:true };
const status = { textContent:"" };
const errors = { textContent:"", hidden:true };
const scheduleResize = () => {};
const document = { body:{ append(){} }, createElement:() => ({ style:{}, click(){}, remove(){} }) };
const allowedDownloadOrigins = new Set(["https://oaisdmntpritalynorth.blob.core.windows.net"]);
const window = { openai:{
  uploadFile:async () => ({ fileId:"should-not-upload" }),
  getFileDownloadUrl:async () => ({ downloadUrl:"https://oaisdmntpritalynorth.blob.core.windows.net/files/stale.png" }),
} };
const clearProduction = (invalidate = true) => {
  if (invalidate) { editRevision += 1; actionSequence += 1; }
  deliveryUrl = ""; deliveryFileId = ""; deliveryFilename = ""; deliveryFile = null;
  download.disabled = true; delivery.hidden = true;
};
let releaseRaster;
const svgToPngFile = () => new Promise((resolve) => { releaseRaster = resolve; });
'''
            + delivery_source
            + r'''
const revision = editRevision;
const sequence = actionSequence;
const pending = prepareDownload({ produced:true, svg:"<svg/>", filename:"stale.svg" }, revision, sequence);
await Promise.resolve();
clearProduction();
releaseRaster({ name:"stale.png", type:"image/png" });
if (await pending !== false) throw new Error("stale raster was reported as published");
if (deliveryFile || deliveryFilename || deliveryUrl || !delivery.hidden) throw new Error("stale raster resurrected delivery state");
''',
            module=True,
        )

    def test_prepare_download_discards_delayed_upload_after_edit(self):
        delivery_source = "function validatedDownloadUrl" + self.html.split(
            "function validatedDownloadUrl", 1
        )[1].split("async function openPreparedDownload", 1)[0]
        self._run(
            r'''
let deliveryUrl = "";
let deliveryFileId = "";
let deliveryFilename = "";
let deliveryFile = null;
let hostCapabilities = {};
let editRevision = 0;
let actionSequence = 1;
const hostState = null;
const download = { disabled:true, textContent:"" };
const handoff = { hidden:true, disabled:false };
const deliveryName = { textContent:"" };
const delivery = { hidden:true };
const status = { textContent:"" };
const errors = { textContent:"", hidden:true };
const scheduleResize = () => {};
const document = { body:{ append(){} }, createElement:() => ({ style:{}, click(){}, remove(){} }) };
const allowedDownloadOrigins = new Set(["https://oaisdmntpritalynorth.blob.core.windows.net"]);
let releaseUpload;
const uploadGate = new Promise((resolve) => { releaseUpload = resolve; });
const window = { openai:{
  uploadFile:async () => { await uploadGate; return { fileId:"stale-upload" }; },
  getFileDownloadUrl:async () => ({ downloadUrl:"https://oaisdmntpritalynorth.blob.core.windows.net/files/stale-upload.png" }),
} };
const clearProduction = (invalidate = true) => {
  if (invalidate) { editRevision += 1; actionSequence += 1; }
  deliveryUrl = ""; deliveryFileId = ""; deliveryFilename = ""; deliveryFile = null;
  download.disabled = true; delivery.hidden = true;
};
const svgToPngFile = async (_svg, filename) => ({ name:filename.replace(/\.svg$/i, ".png"), type:"image/png" });
'''
            + delivery_source
            + r'''
const revision = editRevision;
const sequence = actionSequence;
const pending = prepareDownload({ produced:true, svg:"<svg/>", filename:"stale-upload.svg" }, revision, sequence);
await Promise.resolve();
clearProduction();
releaseUpload();
if (await pending !== false) throw new Error("stale upload was reported as published");
if (deliveryFile || deliveryFileId || deliveryFilename || deliveryUrl || !delivery.hidden) throw new Error("stale upload resurrected delivery state");
''',
            module=True,
        )

    def test_prepare_download_discards_delayed_download_url_after_edit(self):
        delivery_source = "function validatedDownloadUrl" + self.html.split(
            "function validatedDownloadUrl", 1
        )[1].split("async function openPreparedDownload", 1)[0]
        self._run(
            r'''
let deliveryUrl = "";
let deliveryFileId = "";
let deliveryFilename = "";
let deliveryFile = null;
let hostCapabilities = {};
let editRevision = 0;
let actionSequence = 1;
const hostState = null;
const download = { disabled:true, textContent:"" };
const handoff = { hidden:true, disabled:false };
const deliveryName = { textContent:"" };
const delivery = { hidden:true };
const status = { textContent:"" };
const errors = { textContent:"", hidden:true };
const scheduleResize = () => {};
const document = { body:{ append(){} }, createElement:() => ({ style:{}, click(){}, remove(){} }) };
const allowedDownloadOrigins = new Set(["https://oaisdmntpritalynorth.blob.core.windows.net"]);
let releaseUrl;
const urlGate = new Promise((resolve) => { releaseUrl = resolve; });
let getUrlCount = 0;
const window = { openai:{
  uploadFile:async () => ({ fileId:"stale-url" }),
  getFileDownloadUrl:async () => { getUrlCount += 1; await urlGate; return { downloadUrl:"https://oaisdmntpritalynorth.blob.core.windows.net/files/stale-url.png" }; },
} };
const clearProduction = (invalidate = true) => {
  if (invalidate) { editRevision += 1; actionSequence += 1; }
  deliveryUrl = ""; deliveryFileId = ""; deliveryFilename = ""; deliveryFile = null;
  download.disabled = true; delivery.hidden = true;
};
const svgToPngFile = async (_svg, filename) => ({ name:filename.replace(/\.svg$/i, ".png"), type:"image/png" });
'''
            + delivery_source
            + r'''
const revision = editRevision;
const sequence = actionSequence;
const pending = prepareDownload({ produced:true, svg:"<svg/>", filename:"stale-url.svg" }, revision, sequence);
await new Promise((resolve) => setTimeout(resolve, 0));
if (getUrlCount !== 1) throw new Error("download URL request did not start");
clearProduction();
releaseUrl();
if (await pending !== false) throw new Error("stale download URL was reported as published");
if (deliveryFile || deliveryFileId || deliveryFilename || deliveryUrl || !delivery.hidden) throw new Error("stale URL resurrected delivery state");
''',
            module=True,
        )

    def test_prepare_download_bounds_stalled_rasterization(self):
        delivery_source = "function validatedDownloadUrl" + self.html.split(
            "function validatedDownloadUrl", 1
        )[1].split("async function openPreparedDownload", 1)[0].replace("30000", "15")
        self._run(
            r'''
let deliveryUrl = "";
let deliveryFileId = "";
let deliveryFilename = "";
let deliveryFile = null;
let hostCapabilities = {};
let editRevision = 0;
let actionSequence = 1;
const hostState = null;
const download = { disabled:true, textContent:"" };
const handoff = { hidden:true, disabled:false };
const deliveryName = { textContent:"" };
const delivery = { hidden:true };
const status = { textContent:"" };
const errors = { textContent:"", hidden:true };
const scheduleResize = () => {};
const document = { body:{ append(){} }, createElement:() => ({ style:{}, click(){}, remove(){} }) };
const allowedDownloadOrigins = new Set(["https://oaisdmntpritalynorth.blob.core.windows.net"]);
const window = { openai:undefined };
const clearProduction = (invalidate = true) => {
  if (invalidate) { editRevision += 1; actionSequence += 1; }
  deliveryUrl = ""; deliveryFileId = ""; deliveryFilename = ""; deliveryFile = null;
  download.disabled = true; delivery.hidden = true;
};
const svgToPngFile = () => new Promise(() => {});
'''
            + delivery_source
            + r'''
const started = Date.now();
const result = await prepareDownload({ produced:true, svg:"<svg/>", filename:"stalled.svg" }, editRevision, actionSequence);
if (result !== false) throw new Error("stalled rasterization was not rejected");
if (Date.now() - started > 500) throw new Error("rasterization timeout was not bounded");
if (!errors.textContent.includes("PNG conversion did not complete")) throw new Error("rasterization timeout message was lost");
if (deliveryFile || deliveryFilename || !delivery.hidden) throw new Error("timed-out rasterization published delivery state");
''',
            module=True,
        )

    def test_open_download_does_not_restore_cleared_button_after_edit(self):
        delivery_source = "function validatedDownloadUrl" + self.html.split(
            "function validatedDownloadUrl", 1
        )[1].split("async function openPreparedDownload", 1)[0]
        open_source = "async function openPreparedDownload" + self.html.split(
            "async function openPreparedDownload", 1
        )[1].split("function receiveInitialInput", 1)[0]
        self._run(
            r'''
let deliveryUrl = "https://oaisdmntpritalynorth.blob.core.windows.net/files/card.png";
let deliveryFileId = "file-card";
let deliveryFilename = "card.png";
let deliveryFile = { name:"card.png" };
let hostCapabilities = {};
let editRevision = 0;
let actionSequence = 1;
const hostState = null;
const download = { disabled:false, textContent:"Open PNG" };
const handoff = { hidden:true, disabled:false };
const deliveryName = { textContent:"card.png" };
const delivery = { hidden:false };
const status = { textContent:"PNG ready." };
const errors = { textContent:"", hidden:true };
const scheduleResize = () => {};
const document = { body:{ append(){} }, createElement:() => ({ style:{}, click(){}, remove(){} }) };
const allowedDownloadOrigins = new Set(["https://oaisdmntpritalynorth.blob.core.windows.net"]);
let releaseOpen;
const openGate = new Promise((resolve) => { releaseOpen = resolve; });
const window = { openai:{ openExternal:async () => { await openGate; return {}; } } };
const clearProduction = (invalidate = true) => {
  if (invalidate) { editRevision += 1; actionSequence += 1; }
  deliveryUrl = ""; deliveryFileId = ""; deliveryFilename = ""; deliveryFile = null;
  status.textContent = "Edited.";
  download.disabled = true; delivery.hidden = true;
};
'''
            + delivery_source
            + open_source
            + r'''
const pending = openPreparedDownload();
await Promise.resolve();
clearProduction();
releaseOpen();
await pending;
if (!download.disabled) throw new Error("stale open finally re-enabled the cleared download button");
if (status.textContent !== "Edited.") throw new Error("stale open status overwrote the edited state");
''',
            module=True,
        )

    def test_is_error_tool_envelope_keeps_server_message(self):
        helpers = self.html.split(
            "function responseErrorMessage", 1
        )[1].split("function request", 1)[0]
        self._run(
            self.tool_results
            + "\nfunction responseErrorMessage"
            + helpers
            + r'''
const envelope = { isError:true, content:[{ type:"text", text:"Renderer refused this quote: invalid palette" }] };
if (!hasErrorEnvelope(envelope)) throw new Error("isError envelope was not detected");
if (responseErrorMessage(envelope) !== "Renderer refused this quote: invalid palette") throw new Error("useful tool error was lost");
const hydrated = QcbToolResults.read({structuredContent:{valid:true,rendered:true},_meta:{quoteCard:{svg:"<svg/>"}}});
if (hydrated.svg !== "<svg/>") throw new Error("portable tool-result helper was not loaded");
''',
            module=True,
        )

    def test_request_rejects_is_error_response_with_server_message(self):
        request_source = self.html.split(
            "const REQUEST_TIMEOUT_MS", 1
        )[1].split("function schedulePreview", 1)[0]
        message_handler = 'window.addEventListener("message",' + self.html.split(
            'window.addEventListener("message",', 1
        )[1].split("if (typeof ResizeObserver", 1)[0]
        self._run(
            """
const pending = new Map();
let nextId = 1;
let posted = null;
let onMessage = null;
const parent = { postMessage(message) { posted = message; } };
const window = { parent, addEventListener(_name, callback) { onMessage = callback; } };
const REQUEST_TIMEOUT_MS"""
            + request_source
            + message_handler
            + r'''
const response = request("tools/call", {});
await Promise.resolve();
onMessage({ source:parent, data:{ jsonrpc:"2.0", id:posted.id, result:{ isError:true, content:[{ type:"text", text:"Renderer refused this quote: invalid palette" }] } } });
let rejected = null;
try { await response; } catch (error) { rejected = error; }
if (!rejected || rejected.message !== "Renderer refused this quote: invalid palette") throw new Error("isError response did not preserve its server message");
if (pending.size !== 0) throw new Error("isError response remained pending");
''',
            module=True,
        )

    def test_newer_produce_wins_over_older_preview_and_stale_finally_is_ignored(self):
        lifecycle = "async function updatePreview()" + self.html.split(
            "async function updatePreview()", 1
        )[1].split("function startNewWorkspaceCard", 1)[0]
        self._run(
            r'''
const form = { addEventListener(){} };
const submit = { disabled:false, dataset:{} };
const produce = { disabled:false, dataset:{}, listener:null, addEventListener(_name, callback) { this.listener = callback; } };
const errors = { textContent:"", hidden:true };
const status = { textContent:"" };
let editRevision = 0;
let actionSequence = 0;
let previewSequence = 0;
let previewTimer = 0;
let preparedSignature = "", deliveryFile = null;
const hostState = null;
const workspaceReadiness = () => ({ready:true,message:""});
const syncWorkspaceReadiness = () => {};
const remoteLink = {hidden:true,removeAttribute(){}};
let previewRelease, previewArguments = null;
const previewGate = new Promise((resolve) => { previewRelease = resolve; });
const clearProduction = (invalidate = true) => { if (invalidate) { editRevision += 1; actionSequence += 1; } };
const isCurrentAction = (action, revision) => action === actionSequence && revision === editRevision;
const currentArguments = () => ({ text:"quote", transformation:"EDITED", evidence_status:"UNVERIFIED", alt_text:"Accepted chat edit" });
const currentSignature = () => "quote";
const textValue = () => "quote";
const request = async (_method, params) => { if (params.name === "preview_quote_card") { previewArguments = params.arguments; return previewGate; } return { produced:true, valid:true, rendered:true, svg:"<svg/>", filename:"quote.svg" }; };
const extractStructuredContent = (value) => value;
const render = (value) => { status.textContent = value.produced ? "generated" : "preview"; };
const prepareDownload = async () => { deliveryFile={name:"quote.png"}; preparedSignature="quote"; return true; };
const openPreparedDownload = async () => { status.textContent="download started"; };
const scheduleResize = () => {};
const window = { clearTimeout(){} };
'''
            + lifecycle
            + r'''
const olderPreview = updatePreview();
await Promise.resolve();
if (!produce.listener) throw new Error("produce handler was not registered");
const newerProduce = produce.listener();
await newerProduce;
if (status.textContent !== "download started") throw new Error(`one-click production did not start download: ${status.textContent}`);
previewRelease({ produced:false, valid:true, rendered:true });
await olderPreview;
if (status.textContent !== "download started") throw new Error("stale preview overwrote the newer result");
if (previewArguments?.transformation !== "EDITED" || previewArguments?.evidence_status !== "UNVERIFIED" || previewArguments?.alt_text !== "Accepted chat edit") throw new Error("ordinary preview omitted the accepted chat edit provenance");
if (submit.disabled || produce.disabled) throw new Error("current action controls were not restored");
''',
            module=True,
        )

    def test_workspace_and_inline_html_have_distinct_server_flags(self):
        self.assertIn('data-qcb-workspace="true"', self.workspace_html)
        self.assertIn("const workspaceMode = true;", self.workspace_html)
        self.assertIn('data-qcb-workspace="false"', self.html)
        self.assertIn("const workspaceMode = false;", self.html)
        self.assertIn('id="newCard"', self.workspace_html)
        self.assertIn("env(safe-area-inset-top", self.workspace_html)
        self.assertIn('appCapabilities:{ availableDisplayModes:["fullscreen"] }', self.workspace_html)
        self.assertIn(f'appInfo:{{ name:"quote-card-builder-ui", version:"{self.app_version.removeprefix("v")}" }}', self.workspace_html)
        self.assertIn('const demoQuoteLayout = "Le idee migliori\\nmeritano\\ndi essere\\ncondivise.";', self.workspace_html)
        self.assertIn('id="title"', self.workspace_html)
        self.assertIn('id="demoHelper"', self.workspace_html)
        self.assertIn('id="demoNoneOption"', self.workspace_html)
        self.assertIn('id="demoNeutralOption"', self.workspace_html)
        self.assertIn("data:image/svg+xml;base64,", self.workspace_html)

    def test_restored_custom_palette_cannot_become_the_neutral_or_new_card_palette(self):
        apply_input_source = "function applyInput(params)" + self.workspace_html.split(
            "function applyInput(params)", 1
        )[1].split("async function svgToPngFile", 1)[0]
        self._run(
            r'''
const workspaceMode = true;
let demoChoices = false, demoAttributionChoice = false, demoPaletteChoice = false;
const canonicalNeutralPalette = {name:"Initial palette",colors:{primary:"#072743",accent:"#E3F4FF",background:"#FEFDFB",text:"#323232"}};
let paletteInitial = JSON.parse(JSON.stringify(canonicalNeutralPalette));
let currentPalette = null;
let styles = [];
let hasRendered = false;
let graphicSeed = 0;
const format = {value:"4x5"};
const attribution = {value:"",disabled:true};
const attributionDecision = {value:""};
const paletteDecision = {value:"neutral"};
const demoHelper = {hidden:true};
const demoNoneOption = {textContent:"No attribution"};
const demoNeutralOption = {textContent:"Neutral palette"};
const resetDemoLabels = () => {};
const scale = {value:"100"};
const scaleValue = {textContent:"100%"};
const position = {value:"center"};
const normalizeStyles = (value) => value;
const setTextValue = () => {};
const renderEditor = () => {};
const setStyleChoice = () => {};
const styleKeyFromInput = () => "blocks";
const writePalette = (value, remember = false) => {
  currentPalette = JSON.parse(JSON.stringify(value));
  if (remember) paletteInitial = JSON.parse(JSON.stringify(value));
};
const updateStyleState = () => {};
const syncWorkspaceReadiness = () => {};
const scheduleResize = () => {};
'''
            + apply_input_source
            + r'''
const custom = {name:"Brand",colors:{primary:"#AA0000",accent:"#00AA00",background:"#0000AA",text:"#FFFFFF"}};
applyInput({text:"restored",palette:custom,_workspace:{attributionDecision:"none",paletteDecision:"custom"}});
if (JSON.stringify(paletteInitial) !== JSON.stringify(canonicalNeutralPalette)) throw new Error("restored custom palette replaced the canonical neutral palette");
applyInput({text:"restored",palette:custom,_workspace:{attributionDecision:"none",paletteDecision:"neutral"}});
if (JSON.stringify(currentPalette) !== JSON.stringify(canonicalNeutralPalette)) throw new Error("neutral choice kept restored custom colors");
applyInput({text:"pending palette",palette:custom,_workspace:{attributionDecision:"none"}});
if (paletteDecision.value !== "neutral" || JSON.stringify(currentPalette) !== JSON.stringify(canonicalNeutralPalette)) throw new Error("pending palette choice did not resolve to canonical neutral");
applyInput({text:"plain input"});
if (paletteDecision.value !== "neutral" || JSON.stringify(currentPalette) !== JSON.stringify(canonicalNeutralPalette)) throw new Error("input without a palette did not select canonical neutral");
if (attributionDecision.value !== "none") throw new Error("input without an attribution did not select no attribution");
applyInput({text:"legacy author",attribution:"Legacy source",_workspace:{attributionDecision:"",paletteDecision:""}});
if (attributionDecision.value !== "named" || attribution.value !== "Legacy source") throw new Error("legacy author text was not preserved as named attribution");
applyInput({text:"named but blank",attribution:"",_workspace:{attributionDecision:"named",paletteDecision:"neutral"}});
if (attributionDecision.value !== "named" || attribution.value !== "") throw new Error("explicit named-but-empty attribution was converted to no attribution");
'''
        )
        self.assertIn("writePalette(canonicalNeutralPalette);", self.workspace_html)

    def test_renderer_hydration_preserves_explicit_and_legacy_workspace_choices(self):
        render_source = "function render(result)" + self.workspace_html.split(
            "function render(result)", 1
        )[1].split("function applyInput", 1)[0]
        self._run(
            r'''
const workspaceMode = true;
let demoChoices = false, demoAttributionChoice = false, demoPaletteChoice = false;
let hasRendered = false;
let initialContentObserved = false;
let draftTransformation = "VERBATIM", draftEvidenceStatus = "USER_SUPPLIED", draftAltText = "";
const attributionDecision = {value:"none"};
const paletteDecision = {value:"neutral"};
const format = {value:"4x5"}, scale = {value:"100"}, position = {value:"center"};
const status = {textContent:""}, errors = {textContent:"",hidden:true};
const image = {hidden:true,replaceChildren(){},setAttribute(){}};
const meta = {textContent:""};
const document = {activeElement:null};
const text = {contains(){return false;}};
const textValue = () => "Restored quote";
const currentSignature = () => "restored-signature";
const selectionRange = () => null;
let hydrated = null;
const isWorkspaceOpeningResult = () => false;
const syncWorkspaceReadiness = () => {};
const scheduleResize = () => {};
const safeInlineSvg = () => ({});
const showErrors = () => {};
const selectedStyle = () => ({label:"Blocks"});
const applyInput = (state) => { hydrated = structuredClone(state); };
const hostState = null;
const named = {valid:true,rendered:true,svg:"<svg/>",profile:"Custom",format:"4x5",text_scale:1,editor_state:{text:"Restored quote",attribution:"Ada",profile_mode:"custom",palette:{name:"Brand",colors:{primary:"#123456",accent:"#FFF4CC",background:"#FFFFFF",text:"#111111"}}}};
'''
            + render_source
            + r'''
render(named);
if (hydrated?._workspace?.attributionDecision !== "named" || hydrated?._workspace?.paletteDecision !== "custom") throw new Error("fresh renderer mount did not infer choices from the populated editor state");
if (hydrated?._workspace?.demoExample !== false) throw new Error("renderer hydration inferred the demo marker");
hasRendered = false;
demoChoices = true;
demoAttributionChoice = true;
demoPaletteChoice = true;
attributionDecision.value = "none";
paletteDecision.value = "neutral";
hydrated = null;
render(named);
if (hydrated?._workspace?.demoExample !== true || hydrated?._workspace?.demoAttributionChoice !== true || hydrated?._workspace?.demoPaletteChoice !== true) throw new Error("first preview hydration cleared the locally initialized demo state");
if (hydrated?._workspace?.attributionDecision !== "none" || hydrated?._workspace?.paletteDecision !== "neutral") throw new Error("first preview hydration replaced the demo's explicit none/neutral choices");
hasRendered = true;
demoChoices = false;
attributionDecision.value = "named";
paletteDecision.value = "neutral";
hydrated = null;
render(named);
if (hydrated?._workspace?.attributionDecision !== "named" || hydrated?._workspace?.paletteDecision !== "neutral") throw new Error("renderer hydration changed named attribution or neutral palette");
if (hydrated?._workspace?.demoExample !== false) throw new Error("pending renderer hydration inferred demo content");
draftTransformation = "EDITED";
draftEvidenceStatus = "UNVERIFIED";
draftAltText = "Accepted chat edit description";
hydrated = null;
render({...named,editor_state:{...named.editor_state,transformation:"VERBATIM",evidence_status:"USER_SUPPLIED",alt_text:""}});
if (hydrated?.transformation !== "EDITED" || hydrated?.evidence_status !== "UNVERIFIED" || hydrated?.alt_text !== "Accepted chat edit description") throw new Error("ordinary renderer hydration overwrote accepted chat edit provenance or alt text");
''',
            module=True,
        )

    def test_demo_normalization_preserves_whitespace_and_formatting_changes(self):
        demo_edit_source = "function clearDemoChoicesOnEdit()" + self.workspace_html.split(
            "function clearDemoChoicesOnEdit()", 1
        )[1].split("function initializeDemoWorkspace", 1)[0]
        self._run(
            r'''
const demoQuote = "Le idee migliori meritano di essere condivise.";
let quote = "Le idee migliori\nmeritano\ndi essere\ncondivise.";
let demoChoices = true, demoAttributionChoice = true, demoPaletteChoice = true;
const demoHelper = {hidden:false};
const attributionDecision = {value:"none"};
const attribution = {value:"",disabled:true};
const demoNoneOption = {textContent:"Scelta demo: nessuna attribuzione"};
const demoNeutralOption = {textContent:"Palette neutra demo"};
const resetDemoLabels = () => {
  demoNoneOption.textContent = demoAttributionChoice ? "Scelta demo: nessuna attribuzione" : "No attribution";
  demoNeutralOption.textContent = demoPaletteChoice ? "Palette neutra demo" : "Neutral palette";
};
const syncWorkspaceReadiness = () => {};
const textValue = () => quote;
'''
            + demo_edit_source
            + r'''
quote = "Le idee migliori   meritano\t di essere\n condivise.";
clearDemoChoicesOnEdit();
if (!demoChoices || demoHelper.hidden || !demoAttributionChoice || !demoPaletteChoice) throw new Error("whitespace-only edits cleared the demo state");
if (demoNoneOption.textContent !== "Scelta demo: nessuna attribuzione" || demoNeutralOption.textContent !== "Palette neutra demo") throw new Error("demo labels were lost after whitespace changes");
quote = "Un nuovo testo editoriale.";
clearDemoChoicesOnEdit();
if (demoChoices || !demoHelper.hidden || demoAttributionChoice || demoPaletteChoice) throw new Error("actual content edit retained demo markers");
if (attributionDecision.value !== "none" || !attribution.disabled) throw new Error("actual content edit did not preserve no attribution");
if (demoNeutralOption.textContent !== "Neutral palette") throw new Error("actual content edit retained the demo-only palette label");
''',
            module=True,
        )

    def test_workspace_readiness_announces_technical_palette_error_after_first_render(self):
        readiness_source = "function syncWorkspaceReadiness(options = {})" + self.workspace_html.split(
            "function syncWorkspaceReadiness(options = {})", 1
        )[1].split("function currentSignature", 1)[0]
        self._run(
            r'''
const workspaceMode = true, hasRendered = true;
const submit = {disabled:false,dataset:{}}, produce = {disabled:false,dataset:{}};
const status = {textContent:"Preview validated by the canonical renderer."};
const workspaceReadiness = () => ({ready:false,message:"Enter a valid six-digit hex value for every palette color."});
'''
            + readiness_source
            + r'''
const result = syncWorkspaceReadiness({announce:true});
if (result.ready || !status.textContent.includes("six-digit hex")) throw new Error("technical readiness was hidden after the first rendered preview");
if (!submit.disabled || !produce.disabled) throw new Error("an incomplete workspace remained actionable");
''',
            module=True,
        )

    def test_upload_failure_falls_back_to_local_blob_download(self):
        delivery_source = "function validatedDownloadUrl" + self.html.split(
            "function validatedDownloadUrl", 1
        )[1].split("function receiveInitialInput", 1)[0]
        self._run(
            r'''
let deliveryUrl = "";
let deliveryFileId = "";
let deliveryFilename = "";
let deliveryFile = null;
let preparedSignature = "";
let hostCapabilities = {message:{image:{}}};
let editRevision = 0;
let actionSequence = 1;
const hostState = null;
const download = {disabled:true,textContent:""};
const handoff = {hidden:true,disabled:false};
const deliveryName = {textContent:""};
const delivery = {hidden:true};
const status = {textContent:""};
const errors = {textContent:"",hidden:true};
let clicked = 0;
const document = {body:{append(){}},createElement:() => ({style:{},click(){clicked += 1;},remove(){}})};
const NativeURL = globalThis.URL;
class URL extends NativeURL {}
URL.createObjectURL = (file) => `blob:local/${file.name}`;
URL.revokeObjectURL = () => {};
const allowedDownloadOrigins = new Set(["https://oaisdmntpritalynorth.blob.core.windows.net","https://oaisdmntprnortheu.blob.core.windows.net","https://oaisdmntprpolandcentral.blob.core.windows.net"]);
const window = {openai:{uploadFile:async () => {throw new Error("offline");},getFileDownloadUrl:async () => ({})}};
const remoteLink = {hidden:true,removeAttribute(){}};
const scheduleResize = () => {};
const currentSignature = () => "fallback";
const clearProduction = () => {deliveryUrl="";deliveryFileId="";deliveryFilename="";deliveryFile=null;preparedSignature="";download.disabled=true;delivery.hidden=true;};
const svgToPngFile = async () => ({name:"fallback.png",type:"image/png"});
const request = async () => ({});
'''
            + delivery_source
            + r'''
if (!await prepareDownload({produced:true,svg:"<svg/>",filename:"fallback.svg"},0,1)) throw new Error("fallback preparation failed");
if (deliveryUrl !== "blob:local/fallback.png" || deliveryFileId) throw new Error("upload failure did not select the local blob");
if (deliveryName.textContent !== "fallback.png" || delivery.hidden) throw new Error("prepared PNG was not exposed for the immediate download route");
await openPreparedDownload();
if (clicked !== 1 || status.textContent !== "PNG download started.") throw new Error("local PNG was not downloaded");
''',
            module=True,
        )

    def test_primary_download_click_generates_prepares_and_reuses_until_edit(self):
        handler = "async function downloadLatestPng()" + self.workspace_html.split(
            "async function downloadLatestPng()", 1
        )[1].split('produce.addEventListener("click", downloadLatestPng);', 1)[0]
        chat_request = self.workspace_html.split("async function requestModelCompositions(base)", 1)[1].split("async function adoptBrand", 1)[0]
        self.assertIn("sendFollowUpMessage", chat_request)
        self.assertIn('request("ui/message"', chat_request)
        self.assertNotIn("sendFollowUpMessage", handler)
        self.assertNotIn('request("ui/message"', handler)
        self._run(
            r'''
let editRevision = 0, actionSequence = 0, signature = "first quote";
let productionCalls = 0, preparationCalls = 0, openCalls = 0, handler = null;
let preparedSignature = "", deliveryFile = null;
let previewTimer = 0;
const workspaceMode = true;
const submit = {disabled:false,dataset:{}};
const produce = {disabled:false,dataset:{},addEventListener(_name,callback){handler=callback;}};
const errors = {textContent:"",hidden:true};
const status = {textContent:""};
const remoteLink = {hidden:false};
const workspaceReadiness = () => ({ready:true,message:""});
const syncWorkspaceReadiness = () => {};
const scheduleResize = () => {};
const window = {clearTimeout(){}};
const currentSignature = () => signature;
const textValue = () => signature;
const currentArguments = () => ({text:signature});
const isCurrentAction = (action,revision) => action===actionSequence&&revision===editRevision;
const clearProduction = (invalidate=true) => {if(invalidate){editRevision++;actionSequence++;}deliveryFile=null;preparedSignature="";};
const extractStructuredContent = value => value;
const request = async (_method,params) => {if(params.name!=="produce_quote_card")throw new Error("unexpected tool");productionCalls++;return {produced:true,valid:true,rendered:true,svg:"<svg/>",filename:"quote.svg"};};
const render = () => {};
const prepareDownload = async () => {preparationCalls++;deliveryFile={name:"quote.png"};preparedSignature=signature;return true;};
const openPreparedDownload = async () => {openCalls++;if(openCalls===1){errors.textContent="Temporary publication failure";errors.hidden=false;}};
'''
            + handler
            + 'produce.addEventListener("click", downloadLatestPng);\n'
            + r'''
if (!handler) throw new Error("Download PNG click handler was not registered");
await handler();
if (productionCalls!==1||preparationCalls!==1||openCalls!==1) throw new Error("one click did not run production, PNG preparation, and download in order");
if (!errors.textContent.includes("Temporary publication failure")) throw new Error("download failure was not left visible for retry");
await handler();
if (productionCalls!==1||preparationCalls!==1||openCalls!==2) throw new Error("retry did not reuse the unchanged prepared PNG");
signature="edited quote";clearProduction();
await handler();
if (productionCalls!==2||preparationCalls!==2||openCalls!==3) throw new Error("editing did not invalidate cached production and prepare a new PNG");
''',
            module=True,
        )

    def test_workspace_requires_quote_and_valid_colors_but_author_is_optional(self):
        readiness_source = "function workspaceReadiness()" + self.workspace_html.split(
            "function workspaceReadiness()", 1
        )[1].split("function syncWorkspaceReadiness", 1)[0]
        self._run(
            r'''
const workspaceMode = true;
let quote = "";
const textValue = () => quote;
const attributionDecision = {value:""};
const paletteDecision = {value:"neutral"};
const attribution = {value:""};
const paletteFields = {primary:["primaryColor","primaryHex"],accent:["accentColor","accentHex"],background:["backgroundColor","backgroundHex"],text:["textColor","textHex"]};
const values = {primaryHex:"#072743",accentHex:"#E3F4FF",backgroundHex:"#FEFDFB",textHex:"#323232"};
const $ = (id) => ({value:values[id]});
const normalizeHex = (value) => /^#[0-9A-F]{6}$/i.test(value) ? value.toUpperCase() : null;
const customPaletteIsValid = () => Object.values(paletteFields).every((ids) => Boolean(normalizeHex($(ids[1]).value)));
'''
            + readiness_source
            + r'''
if (workspaceReadiness().ready || !workspaceReadiness().message.includes("quote")) throw new Error("empty quote was accepted");
quote = "A deliberate quote";
if (!workspaceReadiness().ready) throw new Error("optional attribution decision blocked a supplied quote");
attributionDecision.value = "named";
if (!workspaceReadiness().ready) throw new Error("blank optional author blocked a supplied quote");
attribution.value = "Author";
if (!workspaceReadiness().ready) throw new Error("neutral base palette remained blocked");
paletteDecision.value = "custom";
if (!workspaceReadiness().ready) throw new Error("complete workspace input remained blocked");
values.accentHex = "not-a-color";
if (workspaceReadiness().ready || !workspaceReadiness().message.includes("six-digit hex")) throw new Error("invalid custom color remained exportable");
values.accentHex = "#E3F4FF";
attributionDecision.value = "none";
attribution.value = "";
paletteDecision.value = "neutral";
if (!workspaceReadiness().ready) throw new Error("explicit no-attribution/neutral choice remained blocked");
paletteDecision.value = "";
if (!workspaceReadiness().ready) throw new Error("undecided palette blocked valid existing card colors");
''',
            module=True,
        )

    def test_inline_preview_and_production_readiness_reject_invalid_palette_hex(self):
        readiness_source = "function workspaceReadiness()" + self.html.split(
            "function workspaceReadiness()", 1
        )[1].split("function syncWorkspaceReadiness", 1)[0]
        self._run(
            r'''
const workspaceMode = false;
const paletteFields = {primary:["primaryColor","primaryHex"],accent:["accentColor","accentHex"],background:["backgroundColor","backgroundHex"],text:["textColor","textHex"]};
const values = {primaryHex:"#072743",accentHex:"#E3F4FF",backgroundHex:"#FEFDFB",textHex:"#323232"};
const $ = (id) => ({value:values[id]});
const normalizeHex = (value) => /^#[0-9A-F]{6}$/i.test(value) ? value.toUpperCase() : null;
const customPaletteIsValid = () => Object.values(paletteFields).every((ids) => Boolean(normalizeHex($(ids[1]).value)));
const textValue = () => "quote";
const attributionDecision = {value:"none"};
const paletteDecision = {value:"custom"};
const attribution = {value:""};
'''
            + readiness_source
            + r'''
if (!workspaceReadiness().ready) throw new Error("valid inline palette was blocked");
values.textHex = "#123";
if (workspaceReadiness().ready || !workspaceReadiness().message.includes("six-digit hex")) throw new Error("invalid inline color remained exportable");
''',
            module=True,
        )

    def test_invalid_edit_clears_stale_busy_state_before_readiness_disables_actions(self):
        clear_source = "function clearProduction" + self.workspace_html.split(
            "function clearProduction", 1
        )[1].split("function selectedStyleKey", 1)[0]
        self._run(
            r'''
const workspaceMode = true;
const hostState = null;
let editRevision = 0;
let actionSequence = 4;
let preparedSignature = "";
let deliveryUrl = "";
let deliveryFileId = "file_old";
let deliveryFilename = "old.png";
let deliveryFile = {};
const submit = {disabled:true,dataset:{busy:"true"}};
const produce = {disabled:true,dataset:{busy:"true"}};
const download = {disabled:false,textContent:"Download PNG"};
const handoff = {hidden:false,disabled:true};
const remoteLink = {hidden:true,removeAttribute(){}};
const delivery = {hidden:false};
const syncWorkspaceReadiness = () => {
  const ready = false;
  if (workspaceMode && !submit.dataset.busy) submit.disabled = !ready;
  if (workspaceMode && !produce.dataset.busy) produce.disabled = !ready;
};
'''
            + clear_source
            + r'''
clearProduction();
if ("busy" in submit.dataset || "busy" in produce.dataset) throw new Error("invalidating edit left stale busy markers");
if (!submit.disabled || !produce.disabled) throw new Error("invalid palette edit left preview or production enabled");
if (editRevision !== 1 || actionSequence !== 5) throw new Error("pending request was not invalidated");
''',
            module=True,
        )

    def test_empty_workspace_tool_payload_cannot_replace_a_restored_draft(self):
        receive_source = "function receiveInitialInput" + self.workspace_html.split(
            "function receiveInitialInput", 1
        )[1].split("function receiveInitialResult", 1)[0]
        self._run(
            r'''
const workspaceMode = true;
let applied = 0;
let hasRendered = false;
let editRevision = 0;
let initialContentObserved = false;
const hostState = {hasRestoredDraft:() => true};
const applyInput = () => { applied += 1; };
const clearUntouchedDemoForIncomingContent = () => false;
const isEditorUpdateInput = () => false;
'''
            + receive_source
            + r'''
receiveInitialInput({});
receiveInitialInput({arguments:{}});
receiveInitialInput({mode:"workspace"});
receiveInitialInput({arguments:{text:"server text"}});
if (applied !== 0) throw new Error("initial workspace payload replaced restored state");
''',
            module=True,
        )


if __name__ == "__main__":
    unittest.main()
