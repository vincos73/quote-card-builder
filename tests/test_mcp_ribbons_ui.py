"""Behavioral contracts for Nastri in the portable, self-contained MCP editor."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import mcp_app


@unittest.skipUnless(shutil.which("node"), "Node.js required")
class McpRibbonsUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = mcp_app.quote_card_preview_html(workspace=True)
        cls.helper_path = ROOT / "assets/mcp-editor/host-context.js"
        cls.gallery_reader = (ROOT / "assets/mcp-editor/tool-results.js").read_text()

    def run_js(self, source):
        completed = subprocess.run(["node", "--input-type=module", "-e", source],
                                   cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(0, completed.returncode, completed.stderr)

    def functions(self, start, end):
        return start + self.html.split(start, 1)[1].split(end, 1)[0]

    def helper_setup(self):
        return f"""
import {{ createRequire }} from 'node:module';
import assert from 'node:assert/strict';
const require=createRequire(import.meta.url);
const QcbHostContext=require({json.dumps(str(self.helper_path))});
const scene={{version:1,id:'own-scene',name:'Own scene',quote_box:{{x:.1,y:.12,width:.8,height:.5}},author_box:{{x:.1,y:.66,width:.8,height:.08}},logo_box:{{x:.1,y:.9,width:.2,height:.03}},ribbons:[{{id:'r1',role:'primary',width_ratio:.2,points:[[0,.8],[.3,.1],[.7,.9],[1,.5]]}}],crossings:[],text_role:'text',background_role:'background'}};
const draft={{text:'🌱 Le idee migliori.',format:'9x16',attribution:'Autore',profile_mode:'custom',transformation:'VERBATIM',evidence_status:'VERIFIED',direction:'editorial',graphic_mode:'auto',graphic_variant:'default',graphic_seed:7,text_scale:1,vertical_position:'center',palette:{{name:'My brand',colors:{{primary:'#3524FF',accent:'#FF47CA',background:'#DAFF00',text:'#072743'}}}},lines:null,styles:[{{start:5,end:9,type:'size',scale:1.5}},{{start:5,end:9,type:'highlight'}}],alt_text:'Existing description',visual_grammar:'ribbons',composition:scene,composition_candidates:[scene],proposal_source:'model',quote_font_size:120,author_font_size:28}};
const values=new Map();
const storage={{getItem:key=>values.get(key)||null,setItem:(key,value)=>values.set(key,value),removeItem:key=>values.delete(key)}};
"""

    def test_device_bases_and_recovered_draft_keep_geometry_sizes_and_model_snapshot(self):
        self.run_js(self.helper_setup() + r'''
const requests=[];
const first=new QcbHostContext({workspace:true,storage,openai:{},request:async(method,params)=>{requests.push({method,params});return {};}});
first.initialize({});first.setDraft(draft,{context:false});
const saved=first.saveBase('My base',draft);
const second=new QcbHostContext({workspace:true,storage,openai:{},request:async(method,params)=>{requests.push({method,params});return {};}});
second.initialize({});
assert.deepEqual(second.getDraft(),draft);
assert.deepEqual(second.listBases()[0].draft.composition,scene);
assert.equal(second.listBases()[0].draft.quote_font_size,120);
assert.equal(second.listBases()[0].draft.author_font_size,28);
assert.equal(second.listBases()[0].draft.styles[0].scale,1.5);
second.acceptToolInput(draft);await Promise.resolve();
const context=requests.find(item=>item.method==='ui/update-model-context').params;
assert.deepEqual(context.structuredContent.modelContent.composition,scene);
assert.ok(context.content[0].text.includes('"quote_font_size":120'));
assert.ok(context.content[0].text.includes('"composition_candidates":'));
assert.ok(!context.content[0].text.includes('<svg'));
second.clearDraft();assert.equal(second.listBases()[0].id,saved.id);
first.destroy();second.destroy();
''')

    def test_unavailable_base_storage_keeps_open_draft_and_json_export(self):
        self.run_js(self.helper_setup() + r'''
const helper=new QcbHostContext({openai:{},storage:{getItem(){throw new Error('blocked');},setItem(){throw new Error('blocked');}}});
helper.setDraft(draft,{persist:false,context:false});
assert.throws(()=>helper.saveBase('My base',draft));
assert.deepEqual(helper.getDraft(),draft);
const restored=QcbHostContext.draftFromProject(JSON.parse(JSON.stringify(QcbHostContext.projectFromDraft(draft))));
assert.deepEqual(restored,draft);
helper.destroy();
''')

    def test_json_and_faithful_reuse_preserve_brand_and_sizes_without_host_svg_state(self):
        self.run_js(self.helper_setup() + r'''
const project=QcbHostContext.projectFromDraft({...draft,svg:'<svg/>',_editor_revision:50,_workspace:{demoExample:true},privateContent:{secret:'x'},composition_previews:[{svg:'<svg/>'}]},'Reusable');
assert.ok(!JSON.stringify(project).includes('<svg'));
assert.ok(!('_editor_revision' in project.draft));
assert.ok(!('_workspace' in project.draft));
assert.ok(!('privateContent' in project.draft));
const imported=QcbHostContext.draftFromProject(JSON.parse(JSON.stringify(project)));
const reused=QcbHostContext.reuseBase(imported,draft.text,draft.attribution,'card');
assert.deepEqual(reused.draft,draft);
assert.equal(reused.reuse_composition,null);
assert.deepEqual(draft.composition,scene);
assert.throws(()=>QcbHostContext.draftFromProject({schema:'other',draft}));
''')

    def test_new_quote_clears_stale_formatting_and_provenance_and_style_variation_inherits_scene(self):
        self.run_js(self.helper_setup() + r'''
const card=QcbHostContext.reuseBase(draft,'Una nuova frase.','','card');
assert.deepEqual(card.draft.styles,[]);assert.equal(card.draft.quote_font_size,null);
assert.equal(card.draft.author_font_size,28);assert.equal(card.draft.attribution,'');
assert.equal(card.draft.evidence_status,'USER_SUPPLIED');assert.equal(card.draft.alt_text,'');
assert.deepEqual(card.draft.palette,draft.palette);assert.deepEqual(card.draft.composition,scene);
const style=QcbHostContext.reuseBase(draft,'Una nuova frase.','Nuovo autore','style');
assert.deepEqual(style.reuse_composition,scene);
assert.equal(style.draft.composition,null);assert.deepEqual(style.draft.composition_candidates,[]);
assert.equal(style.draft.proposal_source,'demo');assert.equal(style.draft.graphic_seed,8);
assert.deepEqual(draft.composition_candidates,[scene]);assert.equal(draft.quote_font_size,120);
const whitespace=QcbHostContext.reuseBase(draft,'🌱 Le\nidee migliori.','Autore','card');
assert.equal(whitespace.draft.styles[0].scale,1.5);assert.equal(whitespace.draft.evidence_status,'VERIFIED');
assert.equal(whitespace.draft.text.slice(6,10),'idee');
''')

    def test_size_ranges_survive_unicode_and_newlines_and_bold_remains_independent(self):
        functions = self.functions("function normalizeStyles", "const blockTags")
        functions += self.functions("function overlap", "function insertAuthoredNewline")
        self.run_js("import assert from 'node:assert/strict';\n" + functions + r'''
const old='🌱 Le idee migliori.';
const styles=[{start:5,end:9,type:'size',scale:1.5},{start:5,end:9,type:'bold'}];
const moved=remapStylesAfterEdit(old,'🌱 Le\nidee migliori.',styles);
assert.deepEqual(moved.find(item=>item.type==='size'),styles[0]);
assert.deepEqual(moved.find(item=>item.type==='bold'),styles[1]);
const changed=remapStylesAfterEdit(old,'🌱 Le nuove idee migliori.',styles);
assert.equal(changed.find(item=>item.type==='size').scale,1.5);
assert.deepEqual(normalizeStyles([{start:0,end:3,type:'size',scale:1.5},{start:3,end:6,type:'size',scale:1.5},{start:6,end:9,type:'size',scale:2}]),[{start:0,end:6,type:'size',scale:1.5},{start:6,end:9,type:'size',scale:2}]);
assert.deepEqual(normalizeStyles([{start:0,end:2,type:'size',scale:9}]),[]);
''')

    def test_selection_size_freezes_fitted_quote_without_resizing_author_or_losing_fills(self):
        core = self.functions("function normalizeStyles", "const blockTags")
        core += self.functions("function overlap", "function remapStylesAcrossWhitespace")
        core += self.functions("function subtractRange", "function applyStyle")
        self.run_js("import assert from 'node:assert/strict';\n" + r'''
let styles=[{start:0,end:12,type:'size',scale:1.5},{start:4,end:8,type:'highlight'}];
const selection=()=>({start:4,end:8}),trimRangeWhitespace=range=>range,isRibbonStyle=()=>true;
const selectionSize={value:'125'},quoteFontSize={value:''},authorFontSize={value:'28'};
let savedSelection=null,ribbonLayout={font_size:126.25};
const toolbarStatus={textContent:''};let renderCount=0,previewCount=0;
const renderEditor=()=>{renderCount++;},clearProduction=()=>{},scheduleResize=()=>{},schedulePreview=()=>{previewCount++;};
''' + core + r'''
applySelectionSize();
assert.equal(quoteFontSize.value,'126.25');assert.equal(authorFontSize.value,'28');
assert.deepEqual(styles,[{start:0,end:4,type:'size',scale:1.5},{start:4,end:8,type:'highlight'},{start:4,end:8,type:'size',scale:1.25},{start:8,end:12,type:'size',scale:1.5}]);
selectionSize.value='100';applySelectionSize();
assert.ok(!styles.some(item=>item.type==='size' && item.start===4 && item.end===8));
assert.ok(styles.some(item=>item.type==='highlight'));assert.equal(previewCount,2);
''')

    def test_nastri_fields_reach_wire_and_persisted_snapshot_without_transient_reuse(self):
        code = self.functions("function currentArguments", "function resetDemoLabels")
        self.run_js(self.helper_setup() + r'''
let style={direction:'editorial',variant:'default',grammar:'ribbons'};
const selectedStyle=()=>style,textValue=()=>draft.text,readLines=()=>null,readPalette=()=>draft.palette;
const format={value:'9x16'},attribution={value:'Autore'},scale={value:'100'},position={value:'center'};
const quoteFontSize={value:'120'},authorFontSize={value:'28'},paletteDecision={value:'custom'},attributionDecision={value:'named'};
let styles=draft.styles,graphicSeed=7,draftTransformation='VERBATIM',draftEvidenceStatus='VERIFIED',draftAltText='';
let ribbonComposition=scene,ribbonCandidates=[scene],ribbonProposalSource='model',pendingReuseComposition=scene;
let editRevision=11,draftUpdateStatus='',appliedUpdateFingerprints=[],demoChoices=false,demoAttributionChoice=false,demoPaletteChoice=false;
''' + code + r'''
const wire=currentArguments();assert.equal(wire.format,'9x16');assert.deepEqual(wire.composition,scene);
assert.equal(wire.quote_font_size,120);assert.equal(wire.author_font_size,28);assert.equal(wire.styles[0].scale,1.5);
assert.deepEqual(wire.reuse_composition,scene);
const persisted=currentDraft();assert.ok(!('reuse_composition' in persisted));assert.deepEqual(persisted.composition_candidates,[scene]);
style={direction:'editorial',variant:'cover'};const legacy=currentArguments();
assert.equal(legacy.visual_grammar,null);assert.equal(legacy.composition,null);assert.deepEqual(legacy.composition_candidates,[]);
assert.ok(!legacy.styles.some(item=>item.type==='size'));assert.equal(legacy.styles[0].type,'highlight');
''')

    def test_editor_dom_uses_code_point_offsets_for_size_after_emoji(self):
        render = self.functions("function renderEditor", "function setTextValue")
        self.run_js("import assert from 'node:assert/strict';\n" + r'''
function element(tag){return {tag,children:[],style:{},appendChild(child){this.children.push(child);},replaceChildren(child){this.children=child.children;}};}
const text=element('text'),document={createDocumentFragment:()=>element('fragment'),createElement:element,createTextNode:value=>({textContent:value})};
const textValue=()=>'🌱 idea\nnuova',pointLength=value=>Array.from(value).length,restoreSelection=()=>{};
let styles=[{start:2,end:6,type:'size',scale:1.5},{start:7,end:12,type:'bold'}];
''' + render + r'''
renderEditor();
assert.equal(text.children[0].children[0].textContent,'🌱 ');
const enlarged=text.children[0].children[1];assert.equal(enlarged.textContent,'idea');assert.equal(enlarged.style.fontSize,'1.5em');
assert.equal(text.children[1].children[0].textContent,'nuova');assert.equal(text.children[1].children[0].className,'style-bold');
''')

    def test_restore_hydrates_chosen_scene_sizes_and_source_then_sends_the_same_wire_state(self):
        hydrate = self.functions("function applyRibbonInput", "function renderRibbonProposals")
        arguments = self.functions("function currentArguments", "function resetDemoLabels")
        self.run_js(self.helper_setup() + r'''
let ribbonComposition=null,ribbonCandidates=[],ribbonProposalSource=null,pendingReuseComposition=scene;
const quoteFontSize={value:''},authorFontSize={value:''};
const isRibbonStyle=()=>true,renderRibbonProposals=()=>{},updateStyleState=()=>{};
const textValue=()=>draft.text,readPalette=()=>draft.palette,readLines=()=>draft.lines;
const selectedStyle=()=>({direction:'editorial',variant:'default',grammar:'ribbons'});
const format={value:'9x16'},attribution={value:draft.attribution},scale={value:'100'},position={value:'center'};
let styles=draft.styles,graphicSeed=7,draftTransformation=draft.transformation,draftEvidenceStatus=draft.evidence_status,draftAltText=draft.alt_text;
const paletteDecision={value:'custom'},attributionDecision={value:'named'};
let editRevision=11,draftUpdateStatus='',appliedUpdateFingerprints=[],demoChoices=false,demoAttributionChoice=false,demoPaletteChoice=false;
''' + hydrate + arguments + r'''
applyRibbonInput(JSON.parse(JSON.stringify(draft)));
const wire=currentArguments();
assert.deepEqual(wire.composition,draft.composition);assert.deepEqual(wire.composition_candidates,draft.composition_candidates);
assert.equal(wire.proposal_source,'model');assert.equal(wire.quote_font_size,120);assert.equal(wire.author_font_size,28);
assert.equal(pendingReuseComposition,null);assert.equal(wire.styles[0].scale,1.5);
assert.deepEqual(wire.palette,draft.palette);assert.equal(wire.format,'9x16');
''')

    def test_bold_and_fill_toggles_preserve_selected_size_metadata(self):
        functions = self.functions("function normalizeStyles", "const blockTags")
        functions += self.functions("function overlap", "function remapStylesAcrossWhitespace")
        functions += self.functions("function rangeCovered", "function readLines")
        self.run_js("import assert from 'node:assert/strict';\n" + r'''
let styles=[{start:2,end:6,type:'size',scale:1.5},{start:2,end:6,type:'highlight'}];
const selection=()=>({start:2,end:6}),trimRangeWhitespace=range=>range;
const toolbarStatus={textContent:''},renderEditor=()=>{},clearProduction=()=>{},scheduleResize=()=>{},schedulePreview=()=>{};
''' + functions + r'''
applyStyle('bold');assert.deepEqual(styles.find(item=>item.type==='size'),{start:2,end:6,type:'size',scale:1.5});
applyStyle('bold');assert.ok(!styles.some(item=>item.type==='bold'));
applyStyle('accent');assert.ok(!styles.some(item=>item.type==='highlight'));
assert.deepEqual(styles.find(item=>item.type==='size'),{start:2,end:6,type:'size',scale:1.5});
''')

    def test_import_validates_before_replacing_and_keeps_a_draft_edited_during_the_request(self):
        listener = '$("projectFile").addEventListener("change", ' + self.html.split(
            '$("projectFile").addEventListener("change", ', 1
        )[1].split('attributionDecision.addEventListener("change"', 1)[0]
        self.run_js(self.helper_setup() + r'''
let editRevision=3,handler=null,accepted=null,rendered=0;
const controls={projectFile:{files:[{size:100,text:async()=>JSON.stringify(QcbHostContext.projectFromDraft(draft))}],value:'x',addEventListener(type,callback){handler=callback;}},baseFeedback:{textContent:''}};
const $=id=>controls[id],scheduleResize=()=>{},extractStructuredContent=value=>value;
const acceptProjectDraft=value=>{accepted=value;},render=()=>{rendered++;};
let release,arguments_=null;
const request=async(method,params)=>{arguments_=params.arguments;return new Promise(resolve=>{release=resolve;});};
''' + listener + r'''
const pending=handler();await Promise.resolve();await Promise.resolve();
assert.ok(release);assert.equal(accepted,null);assert.ok(!('profile_mode' in arguments_));
editRevision=4;
release({rendered:true,valid:true,qa:{passed:false},warnings:[{message:'Low contrast'}],errors:[],editor_state:draft});
await pending;assert.equal(accepted,null);assert.equal(rendered,0);
assert.ok(controls.baseFeedback.textContent.includes('open draft changed'));
assert.equal(controls.projectFile.value,'');
''')

    def test_compact_gallery_hydrates_from_metadata_without_svg_in_snapshot(self):
        self.run_js("import assert from 'node:assert/strict';\n" + self.gallery_reader + r'''
const scene={id:'chosen',quote_box:{x:.1,y:.1,width:.8,height:.5}};
const output={valid:true,rendered:true,editor_state:{visual_grammar:'ribbons',composition:scene,composition_candidates:[scene]},composition_previews:[{id:'chosen',svg_sha256:'hash'}]};
const envelope={structuredContent:output,_meta:{quoteCard:{svg:'<svg/>',composition_previews:[{id:'chosen',svg:'<svg id="chosen"/>'}]}}};
const hydrated=QcbToolResults.read(output,{call_tool_result:envelope});
assert.equal(hydrated.composition_previews[0].svg,'<svg id="chosen"/>');
assert.deepEqual(hydrated.editor_state.composition,scene);assert.ok(!JSON.stringify(hydrated.editor_state).includes('<svg'));
assert.equal(output.composition_previews[0].svg,undefined);
''')

    def test_advisory_qa_false_still_renders_and_downloads_and_has_no_warning_buttons(self):
        renderer = self.functions("function render(result)", "function applyInput")
        warnings = self.functions("function renderWarnings", "function renderSavedBases")
        download = self.functions("async function downloadLatestPng()", 'produce.addEventListener("click", downloadLatestPng);')
        self.run_js("import assert from 'node:assert/strict';\n" + r'''
const elements=new Map();
function element(){return {textContent:'',hidden:true,children:[],append(item){this.children.push(item);},replaceChildren(){this.children=[];}};}
const $=id=>{if(!elements.has(id))elements.set(id,element());return elements.get(id);};
const document={activeElement:null,createElement:tag=>({...element(),tag})};
const workspaceMode=true,attributionDecision={value:'named'},attribution={value:''},paletteDecision={value:'neutral'};
const text={contains:()=>false},textValue=()=>'Quote',selectionRange=()=>null,currentSignature=()=>'exact';
let hasRendered=false,demoChoices=false,demoAttributionChoice=false,demoPaletteChoice=false,initialContentObserved=true;
let draftTransformation='VERBATIM',draftEvidenceStatus='USER_SUPPLIED',draftAltText='';
const format={value:'4x5'},scale={value:'100'},position={value:'center'},status={textContent:''},errors={hidden:true},meta={textContent:''};
let displayed=0,opened=0;
const image={hidden:true,replaceChildren(){displayed++;},setAttribute(){}},selectedStyle=()=>({label:'Nastri'});
const isWorkspaceOpeningResult=()=>false,safeInlineSvg=()=>({}),showErrors=()=>{},applyInput=()=>{},scheduleResize=()=>{},syncWorkspaceReadiness=()=>{},hostState=null;
let editRevision=0,actionSequence=0,previewTimer=0,deliveryFile=null,preparedSignature='';
const submit={disabled:false,dataset:{}},produce={disabled:false,dataset:{}},remoteLink={hidden:true};
const window={clearTimeout(){}},workspaceReadiness=()=>({ready:true}),currentArguments=()=>({text:'Quote'}),clearProduction=()=>{},isCurrentAction=()=>true;
const extractStructuredContent=value=>value;
const response={valid:true,rendered:true,produced:true,svg:'<svg/>',qa:{passed:false},warnings:[{message:'Low contrast',severity:'advisory'}],errors:[],profile:'Brand',format:'4x5'};
const request=async()=>response,prepareDownload=async()=>{preparedSignature='exact';return true;},openPreparedDownload=async()=>{opened++;};
''' + warnings + renderer + download + r'''
render(response);assert.equal(image.hidden,false);assert.equal($('warningsCount').textContent,2);
assert.ok($('warningsList').children.every(item=>item.tag==='li'&&!item.children.length));
await downloadLatestPng();assert.equal(opened,1);assert.equal(produce.disabled,false);assert.ok(displayed>=2);
''')

    def test_self_contained_resource_is_under_budget_and_all_scripts_parse(self):
        self.assertLess(len(self.html.encode()), 256_000)
        self.assertIn('value="9x16"', self.html)
        self.assertIn('data-style-choice="ribbons"', self.html)
        for script in re.findall(r"<script>(.*?)</script>", self.html, re.S):
            result = subprocess.run(["node", "--check", "-"], input=script, text=True,
                                    capture_output=True)
            self.assertEqual(0, result.returncode, result.stderr)


if __name__ == "__main__":
    unittest.main()
