"""Contract tests for the dependency-free MCP Apps host helper."""

from __future__ import annotations

import json
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
HELPER = ROOT / "assets" / "mcp-editor" / "host-context.js"
THEME = ROOT / "assets" / "mcp-editor" / "host-theme.css"


@unittest.skipUnless(shutil.which("node"), "Node.js is required for the host helper tests")
class HostContextTests(unittest.TestCase):
    def run_node(self, body: str) -> dict:
        script = f"""
const QcbHostContext = require({json.dumps(str(HELPER))});
{body}
"""
        completed = subprocess.run(
            ["node", "--input-type=commonjs", "-e", script],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        try:
            return json.loads(completed.stdout)
        except json.JSONDecodeError as error:
            self.fail(f"Node helper did not emit JSON: {completed.stdout!r} ({error})")

    def test_restored_draft_wins_over_initial_input_and_result(self):
        result = self.run_node(
            r'''
const saved = {
  schema: "qcb-editor-state", schemaVersion: 1,
  modelContent: {text: "saved draft", attribution: "A"},
  privateContent: {filename: "saved.png"}, imageIds: ["file_saved"],
};
let restored = null;
const bridge = {widgetState: saved, setWidgetState() { throw new Error("should not write during restore"); }};
const helper = new QcbHostContext({openai: bridge, onRestore: (draft) => { restored = draft; }});
helper.initialize({initialInput: {text: "incoming tool input"}, initialResult: {rendered: true, editor_state: {text: "server result"}}});
const output = {
  draft: helper.getDraft(), restored,
  authoritative: helper.getAuthoritativeResult(),
  state: helper.getState(), hasRestoredDraft: helper.hasRestoredDraft(),
};
helper.destroy();
console.log(JSON.stringify(output));
'''
        )
        self.assertEqual("saved draft", result["draft"]["text"])
        self.assertEqual("saved draft", result["restored"]["text"])
        self.assertEqual("server result", result["authoritative"]["editor_state"]["text"])
        self.assertEqual([], result["state"]["imageIds"])
        self.assertTrue(result["hasRestoredDraft"])

    def test_workspace_restores_versioned_local_draft_and_ignores_widget_state(self):
        result = self.run_node(
            r'''
const storageValues = new Map([[QcbHostContext.WORKSPACE_STORAGE_KEY, JSON.stringify({
  schema: QcbHostContext.WORKSPACE_SCHEMA, schemaVersion: 1,
  modelContent: {text: "local workspace", attribution: "", _workspace:{attributionDecision:"none", paletteDecision:"neutral"}},
})]]);
const storage = {
  getItem(key) { return storageValues.get(key) || null; },
  setItem(key, value) { storageValues.set(key, value); },
  removeItem(key) { storageValues.delete(key); },
};
const bridge = {widgetState:{schema:"qcb-editor-state",schemaVersion:1,modelContent:{text:"stale widget"},imageIds:["removed-file"]},setWidgetState(){throw new Error("workspace touched widget state");}};
let restored = null;
const helper = new QcbHostContext({workspace:true, storage, openai:bridge, onRestore:(draft) => { restored = draft; }});
helper.initialize({initialInput:{}, initialResult:{mode:"workspace",workspace_state:"empty",rendered:false}});
const output = {restored, draft:helper.getDraft(), imageIds:helper.getImageIds(), stored:JSON.parse(storageValues.get(QcbHostContext.WORKSPACE_STORAGE_KEY))};
helper.destroy();
console.log(JSON.stringify(output));
'''
        )
        self.assertEqual("local workspace", result["restored"]["text"])
        self.assertEqual("local workspace", result["draft"]["text"])
        self.assertEqual([], result["imageIds"])
        self.assertEqual("qcb-workspace-draft", result["stored"]["schema"])

    def test_workspace_round_trips_demo_marker_without_inferring_from_quote_text(self):
        result = self.run_node(
            r'''
const sample = "Le idee migliori\nmeritano\ndi essere\ncondivise.";
const values = new Map([[QcbHostContext.WORKSPACE_STORAGE_KEY, JSON.stringify({
  schema: QcbHostContext.WORKSPACE_SCHEMA, schemaVersion: 1,
  modelContent: {text: sample, _workspace: {attributionDecision:"none", paletteDecision:"neutral", demoExample:true}},
})]]);
const storage = {getItem:key => values.get(key) || null, setItem:(key,value) => values.set(key,value), removeItem:key => values.delete(key)};
const helper = new QcbHostContext({workspace:true, storage, openai:{}});
helper.initialize({});
const restoredDemo = helper.getDraft();
helper.setDraft({text:sample,_workspace:{attributionDecision:"none",paletteDecision:"neutral"}},{context:false});
const ordinaryQuote = helper.getDraft();
console.log(JSON.stringify({restoredDemo,ordinaryQuote}));
helper.destroy();
'''
        )
        self.assertEqual("Le idee migliori\nmeritano\ndi essere\ncondivise.", result["restoredDemo"]["text"])
        self.assertTrue(result["restoredDemo"]["_workspace"]["demoExample"])
        self.assertEqual(result["ordinaryQuote"]["text"], result["restoredDemo"]["text"])
        self.assertFalse(result["ordinaryQuote"]["_workspace"].get("demoExample", False))

    def test_workspace_clear_prevents_old_draft_from_returning(self):
        result = self.run_node(
            r'''
const values = new Map();
const storage = {getItem:(key) => values.get(key) || null, setItem:(key,value) => values.set(key,value), removeItem:(key) => values.delete(key)};
const first = new QcbHostContext({workspace:true, storage, openai:{}});
first.initialize({});
first.setDraft({text:"temporary",_workspace:{attributionDecision:"none",paletteDecision:"neutral"}},{context:false});
const existed = values.has(QcbHostContext.WORKSPACE_STORAGE_KEY);
first.clearDraft();
first.destroy();
let restored = false;
const second = new QcbHostContext({workspace:true, storage, openai:{}, onRestore:() => { restored = true; }});
second.initialize({});
const output = {existed, remains:values.has(QcbHostContext.WORKSPACE_STORAGE_KEY), restored, draft:second.getDraft()};
second.destroy();
console.log(JSON.stringify(output));
'''
        )
        self.assertTrue(result["existed"])
        self.assertFalse(result["remains"])
        self.assertFalse(result["restored"])
        self.assertEqual({}, result["draft"])

    def test_inline_and_workspace_persistence_are_isolated(self):
        result = self.run_node(
            r'''
let widget = null;
let storageWrites = 0;
const storage = {getItem:() => null, setItem:() => { storageWrites += 1; }, removeItem() {}};
const bridge = {setWidgetState(value) { widget = value; }};
const inline = new QcbHostContext({workspace:false, storage, openai:bridge});
inline.setDraft({text:"inline"},{context:false});
const workspace = new QcbHostContext({workspace:true, storage, openai:bridge});
workspace.setDraft({text:"workspace",_workspace:{attributionDecision:"none",paletteDecision:"neutral"}},{context:false});
const output = {widgetText:widget.modelContent.text, storageWrites};
inline.destroy(); workspace.destroy();
console.log(JSON.stringify(output));
'''
        )
        self.assertEqual("inline", result["widgetText"])
        self.assertEqual(1, result["storageWrites"])

    def test_workspace_reports_unavailable_storage_without_breaking_edits(self):
        result = self.run_node(
            r'''
const statuses = [];
const storage = {getItem(){throw new Error("blocked");},setItem(){throw new Error("blocked");},removeItem(){throw new Error("blocked");}};
const helper = new QcbHostContext({workspace:true,storage,openai:{},onPersistenceStatus:(status) => statuses.push(status)});
helper.initialize({});
helper.setDraft({text:"still editable"},{context:false});
console.log(JSON.stringify({draft:helper.getDraft(),statuses}));
helper.destroy();
'''
        )
        self.assertEqual("still editable", result["draft"]["text"])
        self.assertTrue(result["statuses"])
        self.assertFalse(result["statuses"][-1]["available"])

    def test_approved_input_can_replace_restored_draft(self):
        result = self.run_node(
            r'''
let saved = {
  schema: "qcb-editor-state", schemaVersion: 1,
  modelContent: {text: "old"}, privateContent: {filename: "old.png"}, imageIds: ["file_old"],
};
const bridge = {widgetState: saved, setWidgetState(value) { saved = value; }};
const helper = new QcbHostContext({openai: bridge, debounceMs: 0});
helper.initialize({initialInput: {text: "ignored initial input"}});
if (!helper.acceptToolInput({arguments: {text: "approved current input", attribution: "Editor"}})) throw new Error("approved input was rejected");
helper.setPrivateContent({filename: "new.png"}, {persist: false});
helper.setImageIds(["file_new"], {persist: false});
helper.setDraft({text: "edited after approval", palette: {name: "Current"}}, {context: false});
helper.flush();
const output = {draft: helper.getDraft(), state: saved, restored: helper.hasRestoredDraft()};
helper.destroy();
console.log(JSON.stringify(output));
'''
        )
        self.assertEqual("edited after approval", result["draft"]["text"])
        self.assertEqual("new.png", result["state"]["privateContent"]["filename"])
        self.assertEqual(["file_new"], result["state"]["imageIds"])
        self.assertFalse(result["restored"])

    def test_model_context_is_debounced_and_theme_variables_are_applied(self):
        result = self.run_node(
            r'''
const listeners = {};
const css = {};
const document = {
  documentElement: {
    style: {setProperty(name, value) { css[name] = value; }, removeProperty(name) { delete css[name]; }},
    setAttribute(name, value) { this[name] = value; },
  },
};
const root = {
  document,
  parent: {},
  addEventListener(name, handler) { listeners[name] = handler; },
  removeEventListener() {},
};
const requests = [];
const helper = new QcbHostContext({root, openai: {}, request: (method, params) => { requests.push({method, params}); }, debounceMs: 1000});
helper.initialize({hostContext: {theme: "dark", safeAreaInsets:{top:10,right:"12px",bottom:4,left:0}, styles: {variables: {"--color-background-primary": "#121212", "--font-sans": "system-ui"}}}});
helper.setDraft({text: "Current quote", format:"4x5", attribution: "Author", profile_mode:"custom", transformation:"VERBATIM", evidence_status:"VERIFIED", direction:"editorial", graphic_mode:"auto", graphic_variant:"cover", graphic_seed:0, text_scale:1, vertical_position:"center", palette: {name: "Current", colors:{primary:"#123456",accent:"#FFF4CC",background:"#FFFFFF",text:"#111111"}}, lines:null, styles: [{start: 0, end: 7, type: "bold"}], alt_text:"Current description", _editor_revision:4});
if (requests.length !== 0) throw new Error("model context was not debounced");
helper.flush();
const fontBefore = css["--font-sans"];
listeners.message({source: {}, data: {jsonrpc: "2.0", method: "ui/notifications/host-context-changed", params: {theme: "light"}}});
if (document.documentElement["data-theme"] !== "dark") throw new Error("untrusted host message changed theme");
listeners.message({source: root.parent, data: {jsonrpc: "2.0", method: "ui/notifications/host-context-changed", params: {theme: "light", styles: {variables: {"--color-background-primary": "#fff"}}}}});
const output = {requests, css, fontBefore, theme: document.documentElement["data-theme"]};
helper.destroy();
console.log(JSON.stringify(output));
'''
        )
        self.assertEqual(1, len(result["requests"]))
        self.assertEqual("ui/update-model-context", result["requests"][0]["method"])
        content = result["requests"][0]["params"]["structuredContent"]["modelContent"]
        self.assertEqual("Current quote", content["text"])
        self.assertEqual("Author", content["attribution"])
        self.assertNotIn("privateContent", content)
        fallback = result["requests"][0]["params"]["content"][0]
        self.assertEqual(["assistant"], fallback["annotations"]["audience"])
        self.assertIn("Current quote", fallback["text"])
        self.assertIn("Current editor snapshot:", fallback["text"])
        self.assertIn("editor_revision=4", fallback["text"])
        self.assertIn('"profile_mode":"custom"', fallback["text"])
        self.assertIn('"palette":{"name":"Current"', fallback["text"])
        self.assertEqual("system-ui", result["fontBefore"])
        self.assertEqual("light", result["theme"])
        self.assertEqual("system-ui", result["css"]["--font-sans"])
        self.assertEqual("10px", result["css"]["--qcb-safe-area-top"])
        self.assertEqual("12px", result["css"]["--qcb-safe-area-right"])
        self.assertEqual("4px", result["css"]["--qcb-safe-area-bottom"])
        self.assertEqual("0px", result["css"]["--qcb-safe-area-left"])

    def test_clear_draft_replaces_previous_model_context_with_empty_context(self):
        result = self.run_node(
            r'''
const requests = [];
const helper = new QcbHostContext({
  workspace:true,
  storage:{getItem:() => null,setItem(){},removeItem(){}},
  openai:{},
  request:(method, params) => { requests.push({method, params}); return {}; },
});
helper.setDraft({text:"old visible quote",attribution:"Author",_workspace:{attributionDecision:"named",paletteDecision:"neutral"}},{context:false});
helper.clearDraft();
const output = {draft:helper.getDraft(), requests};
helper.destroy();
console.log(JSON.stringify(output));
'''
        )
        self.assertEqual({}, result["draft"])
        self.assertEqual(1, len(result["requests"]))
        request = result["requests"][0]
        self.assertEqual("ui/update-model-context", request["method"])
        self.assertEqual({}, request["params"]["structuredContent"]["modelContent"])
        self.assertEqual([], request["params"]["content"])
        self.assertNotIn("old visible quote", json.dumps(request))

    def test_host_model_context_removal_drops_live_attachment_ids(self):
        result = self.run_node(
            r'''
let saved = null;
const bridge = {setWidgetState(value) { saved = value; }};
const helper = new QcbHostContext({workspace:false,openai:bridge});
helper.setDraft({text:"current"},{context:false});
helper.setImageIds(["file_live"]);
helper.setPrivateContent({filename:"old.png"});
helper.applyHostContext({"openai/modelContext":null});
const output = {imageIds:helper.getImageIds(),privateContent:helper.getPrivateContent(),saved};
helper.destroy();
console.log(JSON.stringify(output));
'''
        )
        self.assertEqual([], result["imageIds"])
        self.assertEqual({}, result["privateContent"])
        self.assertEqual([], result["saved"]["imageIds"])
        self.assertEqual({}, result["saved"]["privateContent"])

    def test_model_context_update_id_is_read_from_standard_result_metadata_only(self):
        result = self.run_node(
            r'''
const requests = [];
const helper = new QcbHostContext({
  openai:{},
  request:(method, params) => {
    requests.push({method, params});
    return {_meta:{"openai/modelContext":{updateId:"model-update-2"}}};
  },
});
helper.setDraft({text:"context"},{context:false,persist:false});
(async () => {
  await helper._sendModelContext();
  await helper._sendModelContext();
  const output = {requests,tracked:helper._modelContextUpdateId};
  helper.destroy();
  console.log(JSON.stringify(output));
})().catch((error) => { console.error(error); process.exitCode = 1; });
'''
        )
        self.assertEqual("model-update-2", result["tracked"])
        self.assertEqual(2, len(result["requests"]))
        self.assertNotIn("updateId", result["requests"][0]["params"])
        self.assertNotIn("updateId", result["requests"][1]["params"])

    def test_native_root_timers_are_called_with_their_receiver(self):
        result = self.run_node(
            r'''
const timerRoot = {
  setTimeout(callback) { if (this !== timerRoot) throw new Error("setTimeout receiver lost"); return {unref() {}}; },
  clearTimeout(timer) { if (this !== timerRoot) throw new Error("clearTimeout receiver lost"); },
};
const helper = new QcbHostContext({root: timerRoot, openai: {}});
helper.setDraft({text: "timer receiver"});
helper.destroy();
console.log(JSON.stringify({ok: true}));
'''
        )
        self.assertTrue(result["ok"])


class HostThemeAssetTests(unittest.TestCase):
    def test_original_skin_keeps_workspace_and_safe_area_support(self):
        css = THEME.read_text(encoding="utf-8")
        for token in ("--chrome:#2b1830", "--deep:#1b121f", "--signal:#b9d936", '--ui:"QCB Barlow"'):
            self.assertIn(token, css)
        self.assertNotIn("var(--color-background-primary", css)
        self.assertNotIn("var(--font-sans", css)
        self.assertIn('.shell[data-workspace="true"]', css)
        self.assertIn("display: grid", css)
        self.assertIn("var(--qcb-safe-area-top, 0px)", css)
        self.assertNotIn("display: none !important", css)


if __name__ == "__main__":
    unittest.main()
