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
        cls.tool_results = (ROOT / "assets/mcp-editor/tool-results.js").read_text()

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
const allowedDownloadOrigins = new Set(["https://oaisdmntpritalynorth.blob.core.windows.net", "https://oaisdmntprnortheu.blob.core.windows.net", "https://oaisdmntprpolandcentral.blob.core.windows.net"]);
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
const allowedDownloadOrigins = new Set(["https://oaisdmntpritalynorth.blob.core.windows.net", "https://oaisdmntprnortheu.blob.core.windows.net", "https://oaisdmntprpolandcentral.blob.core.windows.net"]);
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
const allowedDownloadOrigins = new Set(["https://oaisdmntpritalynorth.blob.core.windows.net", "https://oaisdmntprnortheu.blob.core.windows.net", "https://oaisdmntprpolandcentral.blob.core.windows.net"]);
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
const allowedDownloadOrigins = new Set(["https://oaisdmntpritalynorth.blob.core.windows.net", "https://oaisdmntprnortheu.blob.core.windows.net", "https://oaisdmntprpolandcentral.blob.core.windows.net"]);
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
const allowedDownloadOrigins = new Set(["https://oaisdmntpritalynorth.blob.core.windows.net", "https://oaisdmntprnortheu.blob.core.windows.net", "https://oaisdmntprpolandcentral.blob.core.windows.net"]);
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
        )[1].split('window.addEventListener("message"', 1)[0]
        self._run(
            r'''
const form = { addEventListener(){} };
const submit = { disabled:false };
const produce = { disabled:false, listener:null, addEventListener(_name, callback) { this.listener = callback; } };
const errors = { textContent:"", hidden:true };
const status = { textContent:"" };
let editRevision = 0;
let actionSequence = 0;
let previewSequence = 0;
let previewTimer = 0;
const hostState = null;
let previewRelease;
const previewGate = new Promise((resolve) => { previewRelease = resolve; });
const clearProduction = (invalidate = true) => { if (invalidate) { editRevision += 1; actionSequence += 1; } };
const isCurrentAction = (action, revision) => action === actionSequence && revision === editRevision;
const currentArguments = () => ({ text:"quote" });
const currentSignature = () => "quote";
const request = async (_method, params) => params.name === "preview_quote_card" ? previewGate : { produced:true, valid:true, rendered:true };
const extractStructuredContent = (value) => value;
const render = (value) => { status.textContent = value.produced ? "generated" : "preview"; };
const prepareDownload = async () => true;
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
if (status.textContent !== "generated") throw new Error(`produce result was not published: ${status.textContent}`);
previewRelease({ produced:false, valid:true, rendered:true });
await olderPreview;
if (status.textContent !== "generated") throw new Error("stale preview overwrote the newer result");
if (submit.disabled || produce.disabled) throw new Error("current action controls were not restored");
''',
            module=True,
        )


if __name__ == "__main__":
    unittest.main()
