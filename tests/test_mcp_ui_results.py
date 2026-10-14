import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("node"), "Node.js required")
class ToolResultHydrationTests(unittest.TestCase):
    def test_compact_results_hydrate_from_portable_and_chatgpt_envelopes(self):
        source = (ROOT / "assets/mcp-editor/tool-results.js").read_text()
        checks = r'''
const assert = require('node:assert/strict');
const state={valid:true,rendered:true,editor_state:{text:'Current card'}};
const full={structuredContent:state,_meta:{quoteCard:{svg:'<svg/>'}}};
assert.equal(QcbToolResults.read(full).svg,'<svg/>');
assert.equal(QcbToolResults.read({params:full}).svg,'<svg/>');
for(const key of ['call_tool_result','mcp_tool_result']) {
  assert.equal(QcbToolResults.read(state,{status:'success',[key]:full}).svg,'<svg/>');
}
assert.equal(QcbToolResults.read(state).editor_state.text,'Current card');
assert.equal(QcbToolResults.read({content:[{type:'text',text:JSON.stringify({...state,svg:'legacy'})}]}).svg,'legacy');
assert.equal(QcbToolResults.read({content:[{type:'text',text:'Not JSON'}]}),null);
const kit={name:'Studio',font:{regular:{data_base64:'font-bytes'}}};
const compact={structuredContent:{valid:true,rendered:false,editor_state:{text:'Edited'}},_meta:{quoteCard:{brand_kit:kit}}};
assert.deepEqual(QcbToolResults.read(compact).editor_state.brand_kit,kit);
const cleared={structuredContent:{valid:true,rendered:false,editor_state:{text:'Edited',brand_kit:kit}},_meta:{quoteCard:{brand_kit:null}}};
assert.equal(QcbToolResults.read(cleared).editor_state.brand_kit,null);
const cyclic={};cyclic.result=cyclic;assert.equal(QcbToolResults.read(cyclic),null);
assert.equal(state.svg,undefined);
'''
        subprocess.run(["node", "-e", source + checks], check=True, capture_output=True, text=True)
