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
        self.assertEqual(["file_saved"], result["state"]["imageIds"])
        self.assertTrue(result["hasRestoredDraft"])

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
helper.initialize({hostContext: {theme: "dark", styles: {variables: {"--color-background-primary": "#121212", "--font-sans": "system-ui"}}}});
helper.setDraft({text: "Current quote", attribution: "Author", palette: {name: "Current"}, styles: [{start: 0, end: 7, type: "bold"}]});
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
        self.assertEqual("system-ui", result["fontBefore"])
        self.assertEqual("light", result["theme"])
        self.assertEqual("system-ui", result["css"]["--font-sans"])

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
    def test_theme_asset_uses_host_tokens_and_neutral_controls(self):
        css = THEME.read_text(encoding="utf-8")
        for token in ("--color-background-primary", "--color-text-primary", "--font-sans", "--border-radius-md"):
            self.assertIn(token, css)
        self.assertIn("@media (prefers-color-scheme: dark)", css)
        self.assertIn("font-family: var(--qcb-font-sans)", css)
        self.assertIn(".app-header", css)
        self.assertIn("button.primary", css)
        self.assertIn("var(--qcb-accent)", css)


if __name__ == "__main__":
    unittest.main()
