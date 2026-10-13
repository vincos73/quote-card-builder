import shutil
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


class McpRemoteUiDeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if shutil.which("node") is None:
            raise unittest.SkipTest("Node.js non disponibile: test remoto UI saltato")
        if str(SCRIPTS) not in sys.path:
            sys.path.insert(0, str(SCRIPTS))
        import mcp_app

        html = mcp_app.quote_card_preview_html()
        cls.delivery_source = "function validatedDownloadUrl" + html.split(
            "function validatedDownloadUrl", 1
        )[1].split("async function openPreparedDownload", 1)[0]

    def run_js(self, scenario):
        setup = r'''(async () => {
const crypto = require("node:crypto").webcrypto;
globalThis.btoa = (value) => Buffer.from(value, "binary").toString("base64");
let deliveryUrl = "", deliveryFileId = "", deliveryFilename = "card.svg", deliveryFile = null, preparedSignature = "";
let hostCapabilities = {}, editRevision = 0, actionSequence = 4;
const remoteExportOrigin = "https://quote-card-builder-mcp-960066178304.europe-west8.run.app";
const allowedDownloadOrigins = new Set(["https://oaisdmntpritalynorth.blob.core.windows.net"]);
const hostState = null;
const status = {textContent:""}, errors = {textContent:"", hidden:true};
const deliveryName = {textContent:""}, delivery = {hidden:true};
const handoff = {disabled:false}, download = {disabled:false};
const remoteLink = {hidden:true,href:"",download:"",textContent:"",removeAttribute(name){if(name==="href")this.href="";}};
const scheduleResize = () => {};
const window = {openai:{}};
const request = async (method, params) => requestImpl(method, params);
const extractStructuredContent = (response) => response?.structuredContent || response;
const currentSignature = () => "card signature";
const clearProduction = (invalidate = true) => { if (invalidate) { editRevision++; actionSequence++; } deliveryUrl=""; deliveryFileId=""; deliveryFilename="card.svg"; deliveryFile=null; };
const pngBytes = Uint8Array.from([137,80,78,71,13,10,26,10,0,1,2,3]);
const makeFile = () => ({name:"card.png",type:"image/png",arrayBuffer:async () => pngBytes.buffer.slice(0)});
const svgToPngFile = async (_svg, filename) => ({...makeFile(),name:filename.replace(/\.svg$/i,".png")});
const validUrl = remoteExportOrigin + "/exports/Abcdefghijklmnopqrstuvwxyz012345.png";
const sha256 = async () => Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",pngBytes)),b=>b.toString(16).padStart(2,"0")).join("");
const publishResult = async (expires = Date.now()+60000) => {
  const hash = await sha256();
  return {structuredContent:{url:validUrl,filename:"quote-card-"+hash.slice(0,16)+".png",mime_type:"image/png",sha256:hash,expires_at:new Date(expires).toISOString()}};
};
'''
        script = setup + self.delivery_source + scenario + "\n})().catch(error => { console.error(error); process.exitCode = 1; });"
        completed = subprocess.run(
            ["node", "-e", script], cwd=ROOT, capture_output=True, text=True, check=False
        )
        self.assertEqual(0, completed.returncode, completed.stderr)

    def test_concurrent_explicit_actions_publish_exact_png_once(self):
        self.run_js(r'''
let publishCalls = 0, releasePublish, sentBytes = "";
const gate = new Promise(resolve => { releasePublish = resolve; });
const requestImpl = async (method, params) => {
  if (method !== "tools/call" || params.name !== "quote_card_builder_publish_png") throw new Error("unexpected request");
  publishCalls++; sentBytes = params.arguments.png_base64; await gate; return await publishResult();
};
deliveryFile = makeFile(); deliveryFile.qcbRemoteDelivery = true;
const snapshot = currentDeliverySnapshot();
const first = prepareRemotePng(snapshot), second = prepareRemotePng(snapshot);
for (let i=0; i<20 && publishCalls===0; i++) await new Promise(resolve => setTimeout(resolve,0));
if (publishCalls !== 1) throw new Error("concurrent publication count was " + publishCalls);
releasePublish();
const values = await Promise.all([first,second]);
if (values[0] !== values[1] || !deliveryFile.qcbRemoteExport) throw new Error("remote URL was not cached on the PNG file");
if (sentBytes !== Buffer.from(pngBytes).toString("base64")) throw new Error("published bytes differ from the generated PNG");
''')

    def test_stale_publish_response_is_discarded_after_edit(self):
        self.run_js(r'''
let releasePublish, calls = 0;
const gate = new Promise(resolve => { releasePublish = resolve; });
const requestImpl = async () => { calls++; await gate; return await publishResult(); };
deliveryFile = makeFile(); deliveryFile.qcbRemoteDelivery = true;
const pending = prepareRemotePng(currentDeliverySnapshot());
for (let i=0; i<20 && calls===0; i++) await new Promise(resolve => setTimeout(resolve,0));
clearProduction(); releasePublish();
if (await pending !== null || calls !== 1 || deliveryFile || deliveryUrl) throw new Error("stale publication restored delivery state");
''')

    def test_hash_and_export_metadata_are_verified(self):
        self.run_js(r'''
let invalid = "hash";
const requestImpl = async () => {
  const result = await publishResult();
  if (invalid === "hash") result.structuredContent.sha256 = "0".repeat(64);
  else result.structuredContent.url = "https://attacker.invalid/exports/Abcdefghijklmnopqrstuvwxyz012345.png";
  return result;
};
deliveryFile = makeFile(); deliveryFile.qcbRemoteDelivery = true;
const snapshot = currentDeliverySnapshot();
for (const problem of ["hash","url"]) {
  invalid = problem; let rejected = false;
  try { await prepareRemotePng(snapshot); } catch (_) { rejected = true; }
  if (!rejected || deliveryFile.qcbRemoteExport) throw new Error("invalid " + problem + " metadata was accepted");
}
''')

    def test_failed_publication_is_not_cached(self):
        self.run_js(r'''
const requestImpl = async () => ({isError:true});
deliveryFile = makeFile(); deliveryFile.qcbRemoteDelivery = true;
let rejected = false;
try { await prepareRemotePng(currentDeliverySnapshot()); } catch (_) { rejected = true; }
if (!rejected || deliveryFile.qcbRemoteExport) throw new Error("failed publication was cached");
''')

    def test_expired_url_is_republished_on_next_explicit_action(self):
        self.run_js(r'''
let calls = 0;
const requestImpl = async () => { calls++; return await publishResult(Date.now()+60000); };
deliveryFile = makeFile(); deliveryFile.qcbRemoteDelivery = true;
deliveryFile.qcbRemoteExport = {url:validUrl,filename:"quote-card-expired.png",mimeType:"image/png",sha256:"",expiresAt:new Date(Date.now()-1000).toISOString()};
const result = await prepareRemotePng(currentDeliverySnapshot());
if (calls !== 1 || !result || result.expiresAt <= new Date().toISOString()) throw new Error("expired link was reused");
''')

    def test_remote_flag_does_not_use_chatgpt_file_upload_or_eager_publish(self):
        self.run_js(r'''
let hostUploads = 0;
window.openai.uploadFile = async () => { hostUploads++; throw new Error("login required"); };
window.openai.getFileDownloadUrl = async () => { throw new Error("unexpected host lookup"); };
const requestImpl = async () => { throw new Error("must wait for an explicit click"); };
if (!await prepareDownload({produced:true,svg:"<svg/>",filename:"card.svg",remote_file_delivery:true},editRevision,actionSequence)) throw new Error("remote result preparation failed");
if (hostUploads || !deliveryFile?.qcbRemoteDelivery || deliveryUrl) throw new Error("remote result used a host upload or local blob");
''')

    def test_native_download_and_public_fallback(self):
        self.run_js(r'''
let nativePayload, externalHref = "", nativeAccepted = true;
hostCapabilities = {downloadFile:true};
const requestImpl = async (method, params) => {
  if (method === "tools/call") return await publishResult();
  if (method === "ui/download-file") { nativePayload = params.contents[0].resource.blob; return nativeAccepted ? {} : {isError:true}; }
  throw new Error("unexpected request");
};
window.openai.openExternal = async ({href}) => { externalHref = href; };
deliveryFile = makeFile(); deliveryFile.qcbRemoteDelivery = true;
const snapshot = currentDeliverySnapshot();
if (!await downloadRemotePng(snapshot) || nativePayload !== Buffer.from(pngBytes).toString("base64")) throw new Error("native download did not receive exact PNG bytes");
nativeAccepted = false;
if (!await downloadRemotePng(snapshot) || externalHref !== validUrl+"?download=1") throw new Error("failed native download did not use the verified URL");
''')

    def test_host_open_link_is_used_before_external_or_frame_fallback(self):
        self.run_js(r'''
let openRequest;
const requestImpl = async (method, params) => {
  if (method === "tools/call") return await publishResult();
  if (method === "ui/open-link") { openRequest = params; return {}; }
  throw new Error("unexpected request: " + method);
};
deliveryFile = makeFile(); deliveryFile.qcbRemoteDelivery = true;
if (!await downloadRemotePng(currentDeliverySnapshot())) throw new Error("host open-link request was not accepted");
if (openRequest?.url !== validUrl+"?download=1") throw new Error("host did not receive the verified download URL");
if (!remoteLink.hidden || window.openai.openExternal) throw new Error("lower-priority fallback was used after host acceptance");
if (!status.textContent.includes("accepted")) throw new Error("status claimed more than host acceptance");
''')

    def test_host_rejection_exposes_a_direct_verified_link_without_auto_click(self):
        self.run_js(r'''
const requestImpl = async method => {
  if (method === "tools/call") return await publishResult();
  if (method === "ui/open-link") return {isError:true};
  throw new Error("unexpected request: " + method);
};
deliveryFile = makeFile(); deliveryFile.qcbRemoteDelivery = true;
if (await downloadRemotePng(currentDeliverySnapshot())) throw new Error("rejected host request was reported as accepted");
if (remoteLink.hidden || remoteLink.href !== validUrl+"?download=1" || remoteLink.download !== "quote-card-"+(await sha256()).slice(0,16)+".png") throw new Error("verified fallback link was not exposed");
if (!status.textContent.includes("Use the direct download link")) throw new Error("fallback status was misleading");
''')


if __name__ == "__main__":
    unittest.main()
