/* Real card-editor browser smoke. All output and stores remain in this folder. */
const {chromium} = require('playwright');
const fs = require('fs');
const path = require('path');
const assert = require('assert/strict');
const crypto = require('crypto');
const OUT = path.resolve(process.env.QCB_RIBBON_OUTPUT || path.join(__dirname, '../../work/native-ribbons-verification'));
fs.mkdirSync(OUT,{recursive:true});
const url = process.env.QCB_RIBBON_URL || JSON.parse(fs.readFileSync(path.join(OUT, 'ready.json'))).url;
assert.ok(['127.0.0.1','localhost'].includes(new URL(url).hostname),'The ribbon smoke must target an isolated localhost editor.');
const storageKey = `quote-card-editor:${new URL(url).searchParams.get('token')}`;
const errors = [], requests = [], results = [];
let browser, page, latestPreview;
function record(name, details = {}) { results.push({name, passed:true, ...details}); console.log(name); }
function compactQa(body) { return {passed:body.qa?.passed, warnings:body.qa?.warnings?.map(w=>({code:w.code,message:w.message})), formats:body.previews?.map(p=>({format:p.format,font_size:p.font_size,valid:p.ribbon_layout?.valid}))}; }
async function draft() { return page.evaluate(key=>JSON.parse(localStorage.getItem(key))?.draft,storageKey); }
async function previewAfter(action, valid = true) {
  const response = page.waitForResponse(r=>new URL(r.url()).pathname==='/api/preview' && r.request().method()==='POST', {timeout:60000});
  await action(); const received=await response;
  const body=await received.json(); latestPreview=body;
  assert.equal(received.status(),200,body.error);
  if(valid) assert.equal(body.qa.passed,true,JSON.stringify(compactQa(body)));
  await page.waitForFunction(()=>Boolean(document.querySelector('#preview-content svg')));
  return body;
}
async function selectText(fragment) {
  await page.evaluate(fragment=>{
    const editor=document.querySelector('#visual-text-editor'); editor.focus();
    const walker=document.createTreeWalker(editor,NodeFilter.SHOW_TEXT); const nodes=[];
    while(walker.nextNode()) nodes.push(walker.currentNode);
    const full=nodes.map(n=>n.textContent).join(''); const start=full.indexOf(fragment);
    if(start<0) throw new Error(`Selection not found: ${fragment}`);
    let offset=0, a, b;
    for(const node of nodes){ const end=offset+node.textContent.length;
      if(!a&&start>=offset&&start<end) a=[node,start-offset];
      if(start+fragment.length>offset&&start+fragment.length<=end) b=[node,start+fragment.length-offset];
      offset=end;
    }
    const range=document.createRange(); range.setStart(...a);range.setEnd(...b);
    const selection=getSelection();selection.removeAllRanges();selection.addRange(range);
    document.dispatchEvent(new Event('selectionchange'));
  }, fragment);
}
async function reuse(mode, text, author) {
  await page.locator(`[data-reuse-mode="${mode}"]`).first().click();
  await page.locator('#style-reuse-text').fill(text);
  await page.locator('#style-reuse-author').fill(author);
  const response=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/styles/apply'&&r.request().method()==='POST',{timeout:60000});
  const preview=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/preview'&&r.request().method()==='POST',{timeout:60000});
  await page.locator('#style-reuse-confirm').click();
  const received=await response, body=await received.json(); assert.equal(received.status(),200,body.error);
  const checkedResponse=await preview, checked=await checkedResponse.json(); latestPreview=checked;
  assert.equal(checkedResponse.status(),200,checked.error);
  assert.equal(checked.qa.passed,true,JSON.stringify(compactQa(checked)));
  await page.waitForFunction(()=>document.querySelector('#style-reuse-form').hidden);
  return body;
}
(async()=>{
  browser=await chromium.launch({headless:true,channel:'chrome'});
  const context=await browser.newContext({viewport:{width:1440,height:1050},acceptDownloads:true,deviceScaleFactor:1});
  page=await context.newPage();page.on('pageerror',error=>errors.push(String(error)));
  page.on('response', async response=>{
    const route=new URL(response.url()).pathname;
    if(route.startsWith('/api/')&&response.request().method()==='POST') {
      const body=await response.json().catch(()=>({}));
      requests.push({route,status:response.status(),...compactQa(body),error:body.error});
    }
  });
  const initial=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/preview'&&r.request().method()==='POST',{timeout:60000});
  await page.goto(url);latestPreview=await (await initial).json();
  assert.equal(latestPreview.qa.passed,true,JSON.stringify(compactQa(latestPreview)));
  await page.locator('#preview-content svg').waitFor();
  await page.locator('#composition-proposals img').nth(2).waitFor();
  assert.equal(await page.locator('#composition-proposals button[data-composition-id]').count(),3);
  assert.match(await page.locator('#composition-source').innerText(),/modello/);
  assert.equal(await page.locator('#preview-content svg image').count(),1);
  record('three numeric model compositions and real Vincos logo');
  await page.screenshot({path:path.join(OUT,'01-proposals.png'),fullPage:true});

  await previewAfter(()=>page.locator('#composition-proposals button[data-composition-id="qa-side-loops"]').click());
  const chosen=(await draft()).presentation.composition;
  assert.equal(chosen.id,'qa-side-loops');
  const baseSize=latestPreview.previews[0].font_size;
  await selectText('tecnologia');
  const enlarged=await previewAfter(async()=>{await page.locator('#selection-size').fill('140');await page.locator('#selection-size').dispatchEvent('change');},false);
  const sized=await draft();
  assert.equal(sized.presentation.quote_font_size,Number(baseSize.toFixed(2)),'manual span edit freezes the current absolute quote size');
  assert.ok(sized.styles.some(s=>s.type==='size'&&s.scale===1.4));
  record('local size edit freezes Auto and keeps selected composition',{baseSize,reportedOverflow:!enlarged.qa.passed});

  await previewAfter(async()=>{await page.locator('#quote-font-size').fill('92');await page.locator('#quote-font-size').dispatchEvent('change');});
  await previewAfter(async()=>{await page.locator('#author-font-size').fill('32');await page.locator('#author-font-size').dispatchEvent('change');});
  await selectText('La tecnologia apre nuove possibilità.');
  await previewAfter(()=>page.keyboard.press('Control+Shift+h'));
  await selectText('valore');
  await previewAfter(()=>page.locator('[data-style="bold"]').click());
  await previewAfter(()=>page.locator('#attribution-label').fill('Autore dimostrativo\nFonte di prova'));
  const corrected=await draft();
  assert.equal(corrected.presentation.quote_font_size,92);
  assert.equal(corrected.presentation.author_font_size,32);
  assert.ok(corrected.styles.some(s=>s.type==='highlight'));
  const fragments=await page.locator('#preview-content text.quote').evaluateAll(nodes=>nodes.map(n=>({text:n.textContent,size:Number(n.getAttribute('font-size')),y:Number(n.getAttribute('y'))})));
  assert.ok(fragments.some(n=>n.text==='tecnologia'&&Math.abs(n.size-128.8)<.01));
  const highlights=await page.locator('#preview-content .highlight-marker').count();
  assert.ok(highlights>=2,'highlight has a separate rectangle on each wrapped row');
  await page.evaluate(()=>document.fonts.ready);
  const widths=await page.locator('#preview-content text.quote').evaluateAll(nodes=>nodes.map(n=>({
    text:n.textContent, measured:Number(n.getAttribute('data-measured-width')), drawn:n.getComputedTextLength(), size:Number(n.getAttribute('font-size')),
  })));
  fs.writeFileSync(path.join(OUT,'text-metrics.json'),JSON.stringify(widths,null,2)+'\n');
  // Chromium counts a final negative tracking advance; the layout bounds
  // deliberately keep that advance outside the visible fragment width.
  assert.ok(widths.every(row=>row.drawn<=row.measured+.5 && row.measured-row.drawn<=row.size*.025+.5),JSON.stringify(widths));
  record('quote 92px, span 140%, bold, wrapped highlight and two-line author 32px',{highlights});
  const reloadPreview=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/preview'&&r.request().method()==='POST',{timeout:60000});
  await page.reload();latestPreview=await(await reloadPreview).json();
  await page.locator('#preview-content svg').waitFor();
  assert.deepEqual((await draft()).presentation,corrected.presentation);
  assert.deepEqual((await draft()).styles,corrected.styles);
  assert.equal(await page.locator('#attribution-label').inputValue(),'Autore dimostrativo\nFonte di prova');
  await page.screenshot({path:path.join(OUT,'02-corrected.png'),fullPage:true});
  record('reload preserves local draft, attribution and exact formatting');

  await page.locator('#style-name').fill('Nastri QA Vincos');
  const savedResponse=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/styles'&&r.request().method()==='POST',{timeout:60000});
  await page.locator('#style-save-confirm').click();
  const saved=await(await savedResponse).json();assert.ok(saved.saved_style_id);
  await page.locator('[data-reuse-mode="card"]').first().waitFor();
  const projectDownload=page.waitForEvent('download');await page.locator('#project-download').click();
  await (await projectDownload).saveAs(path.join(OUT,'corrected-project.json'));
  const project=JSON.parse(fs.readFileSync(path.join(OUT,'corrected-project.json')));
  assert.deepEqual(project.content.styles,corrected.styles);
  assert.equal(project.brand.font.family,'Barlow');
  assert.deepEqual(project.presentation.composition,chosen);
  record('saved reusable base and full editable project JSON');

  await previewAfter(async()=>{await page.locator('#quote-font-size').fill('75');await page.locator('#quote-font-size').dispatchEvent('change');});
  await reuse('card',corrected.text,corrected.attribution.label);
  assert.equal((await draft()).presentation.quote_font_size,92);
  assert.deepEqual((await draft()).styles,corrected.styles);
  record('same-text card reuse restores base dimensions and preserves current text formatting');

  const newQuote='L’IA aiuta le persone: più possibilità, più cura, più responsabilità.';
  await reuse('card',newQuote,'Nuovo autore');
  const reused=await draft();assert.equal(reused.text,newQuote);
  assert.deepEqual(reused.presentation.composition,chosen);
  assert.deepEqual(reused.styles,[]);assert.equal(reused.styles_customized,true);
  assert.equal(reused.attribution.label,'Nuovo autore');
  record('reuse exact geometry on Unicode quote, clearing obsolete emphasis');

  await reuse('style',newQuote,'');
  const varied=await draft();assert.notDeepEqual(varied.presentation.composition,chosen);
  assert.equal(varied.attribution.label,'');assert.deepEqual(varied.styles,[]);
  assert.equal(varied.proposal_source,'demo');
  assert.match(await page.locator('#composition-source').innerText(),/dimostrativi/);
  record('same-style reuse varies numeric paths and honestly labels demo generation; optional author empty');

  const imported=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/project/load'&&r.request().method()==='POST',{timeout:60000});
  await page.locator('#project-file').setInputFiles(path.join(OUT,'corrected-project.json'));
  const importedResponse=await imported, importedBody=await importedResponse.json();latestPreview=importedBody;
  assert.equal(importedResponse.status(),200,importedBody.error);assert.equal(importedBody.qa.passed,true,JSON.stringify(compactQa(importedBody)));
  await page.waitForFunction(()=>document.querySelector('#quote-font-size').value==='92');
  assert.equal((await draft()).text,corrected.text);assert.deepEqual((await draft()).styles,corrected.styles);
  assert.deepEqual((await draft()).presentation.composition,chosen);
  record('project reimport restores branded composition and granular typography');

  const oversized=await previewAfter(async()=>{await page.locator('#author-font-size').fill('500');await page.locator('#author-font-size').dispatchEvent('change');},false);
  assert.equal(oversized.qa.passed,false);assert.equal((await draft()).presentation.author_font_size,500);
  assert.ok(oversized.qa.warnings.some(w=>w.code==='author_overflow'||w.code==='attribution_outside_safe_area'));
  record('oversized manual author is warned without silently reducing 500px');
  latestPreview=await previewAfter(async()=>{await page.locator('#author-font-size').fill('32');await page.locator('#author-font-size').dispatchEvent('change');});
  const expectedSvg=latestPreview.previews[0].svg;
  fs.writeFileSync(path.join(OUT,'approved-preview.svg'),expectedSvg);
  const generation=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/generate'&&r.request().method()==='POST',{timeout:120000});
  await page.locator('#generate').click();
  const generatedResponse=await generation, generated=await generatedResponse.json();
  assert.equal(generatedResponse.status(),200,generated.error);assert.equal(generated.chatbot.status,'unavailable');
  assert.equal(generated.generation.outputs[0].kind,'png');
  fs.writeFileSync(path.join(OUT,'generation.json'),JSON.stringify(generated,null,2)+'\n');
  const pngPath=generated.generation.outputs[0].absolute_path;
  assert.equal(fs.readFileSync(pngPath).subarray(1,4).toString(),'PNG');
  const proofPath=path.join(OUT,'session/production/vincos-nastri-smoke-editorial-4x5-approved-proof.svg');
  assert.equal(fs.readFileSync(proofPath,'utf8'),expectedSvg,'approved proof must be identical to selected preview');
  const previewPage=await context.newPage();
  await previewPage.setViewportSize({width:1440,height:1800});
  await previewPage.setContent(`<style>html,body{margin:0;width:1440px;height:1800px}svg{display:block}</style>${expectedSvg}`);
  await previewPage.evaluate(()=>document.fonts.ready);
  await previewPage.locator('svg').screenshot({path:path.join(OUT,'approved-preview.png')});
  fs.copyFileSync(pngPath,path.join(OUT,'generated.png'));
  const sharp=require('sharp');
  const a=await sharp(path.join(OUT,'approved-preview.png')).ensureAlpha().raw().toBuffer({resolveWithObject:true});
  const b=await sharp(pngPath).ensureAlpha().raw().toBuffer({resolveWithObject:true});
  assert.deepEqual([a.info.width,a.info.height],[b.info.width,b.info.height]);
  let differentPixels=0, maximumDifference=0;
  for(let pixel=0;pixel<a.data.length;pixel+=4){
    let different=false;
    for(let channel=0;channel<4;channel++){const delta=Math.abs(a.data[pixel+channel]-b.data[pixel+channel]);maximumDifference=Math.max(maximumDifference,delta);if(delta)different=true;}
    if(different)differentPixels++;
  }
  const pixelComparison={size_preview:[a.info.width,a.info.height],size_export:[b.info.width,b.info.height],same_pixels:differentPixels===0,different_pixels:differentPixels,difference_percent:100*differentPixels/(a.info.width*a.info.height),maximum_difference:maximumDifference};
  fs.writeFileSync(path.join(OUT,'pixel-comparison.json'),JSON.stringify(pixelComparison,null,2)+'\n');
  assert.equal(differentPixels,0,JSON.stringify(pixelComparison));
  record('local export produces PNG and identical approved SVG; no Codex handoff',{pngPath,previewSha256:crypto.createHash('sha256').update(expectedSvg).digest('hex')});
  await previewPage.close();
  await page.screenshot({path:path.join(OUT,'03-generated.png'),fullPage:true});
  assert.deepEqual(errors,[]);
  fs.writeFileSync(path.join(OUT,'report.json'),JSON.stringify({passed:true,scope:'localhost card-editor, real renderer; no native Codex or ChatGPT host',results,errors,requests},null,2)+'\n');
  await browser.close();
})().catch(async error=>{
  console.error(error.stack);
  if(page){await page.screenshot({path:path.join(OUT,'failure.png'),fullPage:true}).catch(()=>{});fs.writeFileSync(path.join(OUT,'failure-draft.json'),JSON.stringify(await draft().catch(()=>null),null,2));}
  fs.writeFileSync(path.join(OUT,'report.json'),JSON.stringify({passed:false,error:String(error),results,errors,requests},null,2)+'\n');
  if(browser)await browser.close();process.exitCode=1;
});
