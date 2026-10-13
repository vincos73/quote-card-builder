const {chromium}=require('playwright');
const fs=require('fs');
const path=require('path');
const crypto=require('crypto');
const assert=require('assert/strict');

const port=process.env.QCB_REMOTE_TEST_PORT||'8776';
const base='http://127.0.0.1:'+port;
const out=path.resolve(__dirname,'../../work/remote-mcp/browser-1.8.8');
fs.mkdirSync(out,{recursive:true});
const hash=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));

(async()=>{
 const browser=await chromium.launch({headless:true,channel:'chrome'});
 const context=await browser.newContext({viewport:{width:1440,height:950},acceptDownloads:true});
 const page=await context.newPage();
 const pageErrors=[];const downloads=[];
 page.on('pageerror',error=>pageErrors.push(String(error)));
 page.on('download',download=>downloads.push(download));
 const countCalls=name=>page.evaluate(name=>calls.filter(call=>call.name===name).length,name);
 const remoteEndpoint=await page.request.get(base+'/health').then(response=>response.json());
 assert.match(remoteEndpoint.workspace_resource,/\/workspace\/v1\.56\.html$/,'deployed workspace uses the cache-busted UI resource');
 if(process.env.QCB_REMOTE_TEST_FAIL_FIRST_PUBLISH!=='0'){
   const reset=await page.request.post(base+'/reset',{data:{}}).then(response=>response.json());
   assert.equal(reset.fail_first_publish,true,'host enables the one-time publication failure fixture');
   assert.equal(reset.publish_attempts,0,'host publication counter starts fresh for each smoke run');
 }
 await page.goto(base);
 let frame=page.frames().find(candidate=>candidate.url().endsWith('/workspace'));
 assert.ok(frame,'workspace iframe loaded');
 await frame.locator('#text').waitFor();
 await frame.locator('#demoHelper').waitFor({state:'visible',timeout:6000});
 assert.equal((await frame.locator('#text').innerText()).trim(),'Le idee migliori\nmeritano\ndi essere\ncondivise.','four-line Italian example appears after the alias grace period');
 assert.equal(await frame.locator('#demoHelper').isVisible(),true,'example helper is visible');
 assert.equal(await frame.locator('#attributionDecision').inputValue(),'none','demo attribution choice is explicit');
 assert.equal(await frame.locator('#paletteDecision').inputValue(),'neutral','demo palette choice is explicit');
 assert.equal(await frame.locator('#demoNoneOption').innerText(),'Scelta demo: nessuna attribuzione');
 assert.equal(await frame.locator('#demoNeutralOption').innerText(),'Palette neutra demo');
 await frame.waitForFunction(()=>{try{return JSON.parse(localStorage.getItem('quote-card-builder.workspace.v1'))?.modelContent?._workspace?.demoExample===true}catch(_){return false}});
 const demoDraft=await frame.evaluate(()=>JSON.parse(localStorage.getItem('quote-card-builder.workspace.v1')));
 assert.equal(demoDraft.modelContent._workspace.demoExample,true,'sample is stored with an explicit demo marker');
 assert.equal(await page.evaluate(()=>messages.length),0,'demo startup made no chat message call');
 await frame.locator('#image svg').waitFor({timeout:30000});
 assert.equal(await frame.locator('#text .style-bold').innerText(),'Le idee migliori','editor marks the first sample line bold');
 assert.deepEqual(await frame.locator('#text .style-italic').allInnerTexts(),['meritano','di essere'],'editor marks both middle phrases italic');
 assert.equal(await frame.locator('#text .style-highlight').innerText(),'condivise.','editor marks the final word highlighted');
 const demoSvg=await frame.locator('#image svg').evaluate(node=>node.outerHTML);
 assert.match(demoSvg,/<tspan[^>]*font-weight="700"[^>]*>Le idee migliori<\/tspan>/,'canonical SVG renders the first line bold');
 assert.match(demoSvg,/<tspan[^>]*font-style="italic"[^>]*>meritano<\/tspan>/,'canonical SVG renders “meritano” italic');
 assert.match(demoSvg,/<tspan[^>]*font-style="italic"[^>]*>di essere<\/tspan>/,'canonical SVG renders “di essere” italic');
 assert.match(demoSvg,/<rect[^>]*class="highlight-marker"/,'canonical SVG includes the final-line highlight');
 const demoCall=await page.evaluate(()=>calls.find(call=>call.name==='preview_quote_card')?.arguments||null);
 assert.ok(demoCall,'the initial four-line sample was validated by the canonical renderer');
 const singleLineResponse=await page.request.post(base+'/call',{data:{name:'preview_quote_card',arguments:{...demoCall,text:'Le idee migliori meritano di essere condivise.',lines:null,styles:[]}}}).then(response=>response.json());
 const singleLineStructured=singleLineResponse.structuredContent||singleLineResponse.structured_content||singleLineResponse.content?.filter(item=>item.type==='text').map(item=>{try{return JSON.parse(item.text)}catch(_){return null}}).find(item=>item&&typeof item==='object')||{};
 const singleLineSvg=singleLineStructured.svg||singleLineResponse._meta?.quoteCard?.svg;
 assert.equal(typeof singleLineSvg,'string','single-line comparison returns canonical SVG');
 const quoteSize=svg=>Number(svg.match(/<text[^>]*class="quote"[^>]*font-size="([0-9.]+)"/)?.[1]);
 const demoFontSize=quoteSize(demoSvg),singleLineFontSize=quoteSize(singleLineSvg);
 assert.ok(quoteSize(demoSvg)>quoteSize(singleLineSvg),`four-line sample font (${quoteSize(demoSvg)}) exceeds the prior one-line treatment (${quoteSize(singleLineSvg)})`);
 await page.screenshot({path:path.join(out,'remote-demo.png'),fullPage:true});
 await frame.locator('#image svg').screenshot({path:path.join(out,'remote-demo-renderer.png')});
 await page.setViewportSize({width:375,height:812});
 await page.screenshot({path:path.join(out,'remote-demo-mobile.png'),fullPage:true});
 await page.setViewportSize({width:1440,height:950});

 await frame.locator('#text').evaluate(el=>{const node=el.querySelector('.style-italic');const textNode=[...node.childNodes].find(child=>child.nodeType===Node.TEXT_NODE);const range=document.createRange();range.setStart(textNode,0);range.setEnd(textNode,textNode.length);el.focus();const selection=getSelection();selection.removeAllRanges();selection.addRange(range);});
 let previewCalls=await countCalls('preview_quote_card');
 await frame.locator('[data-style="bold"]').click();
 await page.waitForFunction(previous=>calls.filter(call=>call.name==='preview_quote_card').length>previous,previewCalls,{timeout:30000});
 await frame.locator('#produce').waitFor({state:'visible'});
 await frame.waitForFunction(()=>!document.querySelector('#produce').disabled,{timeout:30000});
 await frame.waitForFunction(()=>document.activeElement?.id==='text'&&getSelection()?.toString()==='meritano');
 assert.equal(await frame.locator('#demoHelper').isVisible(),true,'formatting-only changes keep the demo helper');
 assert.equal(await frame.locator('#paletteDecision').inputValue(),'neutral','neutral palette remains selected after formatting');
 previewCalls=await countCalls('preview_quote_card');
 await frame.locator('#text').evaluate(el=>{el.innerText=el.innerText.replace('Le idee migliori','Le idee\n migliori');el.dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'insertText',data:'\n'}));});
 await page.waitForFunction(previous=>calls.filter(call=>call.name==='preview_quote_card').length>previous,previewCalls,{timeout:30000});
 await frame.waitForFunction(()=>!document.querySelector('#produce').disabled,{timeout:30000});
 assert.equal((await frame.locator('#text').innerText()).replace(/\s+/g,' ').trim(),'Le idee migliori meritano di essere condivise.');
 assert.equal(await frame.locator('#demoHelper').isVisible(),true,'whitespace and line-break edits keep the demo helper');
 assert.equal(await frame.locator('#paletteDecision').inputValue(),'neutral','neutral remains the base palette after a line-break edit');
 assert.equal(await frame.locator('#produce').isEnabled(),true,'preview keeps download readiness visible');
 const formattedDraft=await frame.evaluate(()=>JSON.parse(localStorage.getItem('quote-card-builder.workspace.v1')));
 assert.equal(formattedDraft.modelContent._workspace.demoExample,true,'normalized sample remains marked as the demo');

 const pendingContext=await browser.newContext({viewport:{width:1000,height:760}});
 const pendingPage=await pendingContext.newPage();
 await pendingPage.goto(base);
 const pendingFrame=pendingPage.frames().find(candidate=>candidate.url().endsWith('/workspace'));
 await pendingFrame.locator('#image svg').waitFor({timeout:30000});
 await pendingFrame.locator('#attributionDecision').selectOption('named');
 await pendingFrame.waitForFunction(()=>document.querySelector('#status').textContent.includes('Add the attribution name or source.'));
 assert.equal(await pendingFrame.locator('#produce').isDisabled(),true,'an explicit named attribution without a name remains invalid after render');
 assert.equal(await pendingFrame.locator('#attribution').isEnabled(),true,'the blank named field remains editable');
 await pendingContext.close();
 assert.equal(await frame.locator('#attributionDecision').inputValue(),'none','the untouched demo keeps its no-attribution default');
 assert.equal(await frame.locator('#paletteDecision').inputValue(),'neutral','the untouched demo keeps its neutral default');

 const errorMessage=await frame.locator('#errors');
 await frame.locator('#produce').click();
 await page.waitForFunction(()=>calls.filter(call=>call.name==='produce_quote_card').length===1,{timeout:60000});
 await page.waitForFunction(()=>calls.filter(call=>call.name==='quote_card_builder_publish_png').length===1,{timeout:60000});
 await frame.locator('#errors').waitFor({state:'visible',timeout:60000});
 assert.match(await errorMessage.innerText(),/Temporary download service failure|Retry/i,'first publication failure is shown');
 assert.equal(await countCalls('produce_quote_card'),1,'the failed download still produced one canonical PNG');
 assert.equal(await countCalls('quote_card_builder_publish_png'),1,'the first click attempted remote publication');
 await wait(250);
 assert.equal(downloads.length,0,'failed publication did not start a download');
 assert.equal(await frame.locator('#produce').isEnabled(),true,'primary action remains available for retry');

 const firstDownloadEvent=page.waitForEvent('download',{timeout:60000});
 await frame.locator('#produce').click();
 const firstDownload=await firstDownloadEvent;
 const firstPath=path.join(out,'remote-browser-download.png');
 await firstDownload.saveAs(firstPath);
 const browserPng=fs.readFileSync(firstPath);
 assert.equal(browserPng.subarray(1,4).toString(),'PNG','single-click browser download contains a real PNG');
 assert.equal(await countCalls('produce_quote_card'),1,'retry reused the already produced PNG');
 assert.equal(await countCalls('quote_card_builder_publish_png'),2,'retry repeated the failed publication without rendering again');
 const firstOpenLink=await page.evaluate(()=>openLinks[0]||null);
 assert.ok(firstOpenLink,'browser used host-mediated ui/open-link');
 assert.match(firstOpenLink.url,/^https:\/\/.+\/exports\/[A-Za-z0-9_-]{32}\.png\?download=1$/);

 const published=await page.evaluate(()=>toolResults.filter(item=>item.name==='quote_card_builder_publish_png').at(-1)?.result||null);
 assert.ok(published,'successful remote publication result was forwarded');
 const publishedContent=published.structuredContent||published.structured_content||{};
 assert.match(publishedContent.filename,/^quote-card-[a-f0-9]{16}\.png$/);
 assert.equal(publishedContent.mime_type,'image/png');
 assert.equal(publishedContent.sha256,hash(browserPng),'browser download bytes match the server SHA256');
 const fetched=await page.request.get(firstOpenLink.url,{timeout:60000});
 assert.equal(fetched.status(),200,'public download URL is reachable');
 assert.match(fetched.headers()['content-type']||'',/image\/png/i);
 const remoteBytes=Buffer.from(await fetched.body());
 assert.ok(remoteBytes.equals(browserPng),'browser download matches bytes served by the deployed endpoint');
 assert.equal(hash(remoteBytes),publishedContent.sha256,'fetched PNG matches the verified publication hash');

 const secondDownloadEvent=page.waitForEvent('download',{timeout:60000});
 await frame.locator('#produce').click();
 const secondDownload=await secondDownloadEvent;
 const secondPath=path.join(out,'remote-browser-download-reused.png');
 await secondDownload.saveAs(secondPath);
 assert.ok(fs.readFileSync(secondPath).equals(browserPng),'unchanged click downloads the same PNG bytes');
 assert.equal(await countCalls('produce_quote_card'),1,'unchanged click reused production');
 assert.equal(await countCalls('quote_card_builder_publish_png'),2,'unchanged click reused the remote publication');

 const quote='La tecnologia migliore ci aiuta a decidere meglio.';
 let previewsBeforeEdit=await countCalls('preview_quote_card');
 await frame.locator('#text').fill(quote);
 assert.equal(await frame.locator('#attributionDecision').inputValue(),'none','editing real demo text preserves the no-attribution default');
 assert.equal(await frame.locator('#paletteDecision').inputValue(),'neutral','editing the sample keeps the neutral base palette');
 assert.equal(await frame.locator('#demoHelper').isVisible(),false,'helper hides after the sample is edited');
 await page.waitForFunction(previous=>calls.filter(call=>call.name==='preview_quote_card').length>previous,previewsBeforeEdit,{timeout:30000});
 await frame.waitForFunction(()=>!document.querySelector('#produce').disabled,{timeout:30000});
 await frame.waitForFunction(()=>{try{return JSON.parse(localStorage.getItem('quote-card-builder.workspace.v1'))?.modelContent?._workspace?.demoExample!==true}catch(_){return false}});
 const editedDraft=await frame.evaluate(()=>JSON.parse(localStorage.getItem('quote-card-builder.workspace.v1')));
 assert.notEqual(editedDraft.modelContent._workspace?.demoExample,true,'editing clears the demo marker');
 await frame.locator('#image svg').waitFor({timeout:30000});
 await frame.locator('#paletteDecision').selectOption('custom');
 const editedQuote='Le idee condivise diventano occasioni per tutti.';
 previewsBeforeEdit=await countCalls('preview_quote_card');
 await frame.locator('#text').fill(editedQuote);
 assert.equal(await frame.locator('#attributionDecision').inputValue(),'none','an explicit attribution choice survives later text edits');
 assert.equal(await frame.locator('#paletteDecision').inputValue(),'custom','an explicit palette choice survives later text edits');
 await frame.locator('#attributionDecision').selectOption('none');
 await frame.locator('#paletteDecision').selectOption('neutral');
 await page.waitForFunction(previous=>calls.filter(call=>call.name==='preview_quote_card').length>previous,previewsBeforeEdit,{timeout:30000});
 await frame.waitForFunction(()=>!document.querySelector('#produce').disabled,{timeout:30000});
 await page.screenshot({path:path.join(out,'remote-edited-card.png'),fullPage:true});
 const editedDownloadEvent=page.waitForEvent('download',{timeout:60000});
 await frame.locator('#produce').click();
 const editedDownload=await editedDownloadEvent;
 const editedPath=path.join(out,'remote-browser-download-edited.png');
 await editedDownload.saveAs(editedPath);
 const editedPng=fs.readFileSync(editedPath);
 assert.equal(editedPng.subarray(1,4).toString(),'PNG');
 assert.equal(await countCalls('produce_quote_card'),2,'edited text triggered fresh canonical production');
 assert.equal(await countCalls('quote_card_builder_publish_png'),3,'edited PNG was published once');
 assert.notEqual(hash(editedPng),hash(browserPng),'edited quote produced different PNG bytes');

 await page.setViewportSize({width:375,height:812});
 const dimensions=await frame.evaluate(()=>({scroll:document.documentElement.scrollWidth,width:innerWidth}));
 assert.ok(dimensions.scroll<=dimensions.width,JSON.stringify(dimensions));
 await frame.locator('#submit').focus();
 await frame.locator('#submit').press('Tab');
 const focus=await frame.locator('#produce').evaluate(el=>({active:document.activeElement===el,outline:getComputedStyle(el).outlineStyle,outlineWidth:getComputedStyle(el).outlineWidth}));
 assert.equal(focus.active,true,'Download PNG can be reached from the keyboard');
 assert.notEqual(focus.outline,'none','keyboard focus remains visible');
 await page.screenshot({path:path.join(out,'remote-edited-card-mobile.png'),fullPage:true});

 const inputContext=await browser.newContext({viewport:{width:1000,height:760}});
 const inputPage=await inputContext.newPage();
 await inputPage.goto(base);
 let inputFrame=inputPage.frames().find(candidate=>candidate.url().endsWith('/workspace'));
 await inputFrame.locator('#text').waitFor();
 await wait(250);
 await inputPage.evaluate(()=>document.querySelector('#app').contentWindow.postMessage({jsonrpc:'2.0',method:'ui/notifications/tool-input',params:{text:'Human supplied input before demo seeding.'}},location.origin));
 await inputFrame.waitForFunction(()=>document.querySelector('#text').innerText.trim()==='Human supplied input before demo seeding.');
 await wait(2300);
 assert.equal((await inputFrame.locator('#text').innerText()).trim(),'Human supplied input before demo seeding.','immediate explicit input was preserved past demo seeding');
 assert.equal(await inputFrame.locator('#demoHelper').isVisible(),false,'explicit input suppresses the demo helper');
 assert.equal(await inputFrame.locator('#attributionDecision').inputValue(),'none','explicit input without an attribution defaults to no attribution');
 assert.equal(await inputFrame.locator('#paletteDecision').inputValue(),'neutral','inputs without a palette choice select the neutral base palette');

 const choiceContext=await browser.newContext({viewport:{width:1000,height:760}});
 const choicePage=await choiceContext.newPage();
 await choicePage.goto(base);
 const choiceFrame=choicePage.frames().find(candidate=>candidate.url().endsWith('/workspace'));
 await choiceFrame.locator('#demoHelper').waitFor({state:'visible',timeout:6000});
 await choiceFrame.locator('#attributionDecision').selectOption('named');
 await choiceFrame.locator('#attribution').fill('A chosen author');
 await choiceFrame.locator('#paletteDecision').selectOption('custom');
 await choiceFrame.locator('#text').fill('A changed quote keeps deliberate choices.');
 assert.equal(await choiceFrame.locator('#attributionDecision').inputValue(),'named','a deliberate author choice survives editing the demo quote');
 assert.equal(await choiceFrame.locator('#attribution').inputValue(),'A chosen author');
 assert.equal(await choiceFrame.locator('#paletteDecision').inputValue(),'custom','a deliberate palette choice survives editing the demo quote');
 assert.equal(await choiceFrame.locator('#demoHelper').isVisible(),false);
 await choiceFrame.waitForFunction(()=>{try{return JSON.parse(localStorage.getItem('quote-card-builder.workspace.v1'))?.modelContent?._workspace?.demoExample!==true}catch(_){return false}});
 assert.notEqual((await choiceFrame.evaluate(()=>JSON.parse(localStorage.getItem('quote-card-builder.workspace.v1')))).modelContent._workspace.demoExample,true);

 await choicePage.waitForFunction(()=>contexts.some(item=>item.structuredContent?.modelContent?.attribution==='A chosen author'&&item.structuredContent.modelContent.profile_mode==='custom'),undefined,{timeout:10000});
 const updateBase=await choicePage.evaluate(()=>{
   const model=contexts.filter(item=>item.structuredContent?.modelContent?._editor_revision!==undefined).at(-1).structuredContent.modelContent;
   const fields=['text','format','attribution','profile_mode','transformation','evidence_status','direction','graphic_mode','graphic_variant','graphic_seed','text_scale','vertical_position','palette','lines','styles','alt_text'];
   return {revision:model._editor_revision,snapshot:Object.fromEntries(fields.map(key=>[key,model[key]]))};
 });
 assert.equal(updateBase.snapshot.attribution,'A chosen author','assistant-visible snapshot includes the current author');
 assert.equal(updateBase.snapshot.profile_mode,'custom','assistant-visible snapshot includes the current palette choice');
 const followupArgs={base_revision:updateBase.revision,base_snapshot:updateBase.snapshot,patch:{text:'A later chat edit changes only the requested wording.'}};
 const followupEnvelope=await choicePage.request.post(base+'/call',{data:{name:'quote_card_builder_update_editor',arguments:followupArgs}}).then(response=>response.json());
 const followup=followupEnvelope.structuredContent||followupEnvelope.structured_content;
 assert.ok(followup?.update&&followup.valid&&followup.rendered,'deployed follow-up tool returns a tagged rendered update');
 assert.deepEqual(followup.patch,{text:followupArgs.patch.text,transformation:'EDITED',evidence_status:'UNVERIFIED'},'server records text provenance defaults in the effective patch');
 await choicePage.evaluate(args=>document.querySelector('#app').contentWindow.postMessage({jsonrpc:'2.0',method:'ui/notifications/tool-input',params:{name:'quote_card_builder_update_editor',arguments:args}},location.origin),followupArgs);
 await wait(250);
 assert.equal((await choiceFrame.locator('#text').innerText()).replace(/\s+/g,' ').trim(),'A changed quote keeps deliberate choices.','follow-up input alone does not replace a mounted draft');
 await choicePage.evaluate(result=>document.querySelector('#app').contentWindow.postMessage({jsonrpc:'2.0',method:'ui/notifications/tool-result',params:result},location.origin),followup);
 await choiceFrame.waitForFunction(()=>document.querySelector('#text').innerText.includes('A later chat edit changes only the requested wording.'),undefined,{timeout:30000});
 assert.equal(await choiceFrame.locator('#attributionDecision').inputValue(),'named','sparse chat edit preserves a manually selected author');
 assert.equal(await choiceFrame.locator('#attribution').inputValue(),'A chosen author');
 assert.equal(await choiceFrame.locator('#paletteDecision').inputValue(),'custom','sparse chat edit preserves a manually selected palette');
 await choicePage.waitForFunction(()=>contexts.some(item=>item.structuredContent?.modelContent?.text==='A later chat edit changes only the requested wording.'&&item.structuredContent.modelContent._editor_revision!==undefined),undefined,{timeout:10000});
 const linesBase=await choicePage.evaluate(()=>{
   const model=contexts.filter(item=>item.structuredContent?.modelContent?.text==='A later chat edit changes only the requested wording.').at(-1).structuredContent.modelContent;
   const fields=['text','format','attribution','profile_mode','transformation','evidence_status','direction','graphic_mode','graphic_variant','graphic_seed','text_scale','vertical_position','palette','lines','styles','alt_text'];
   return {revision:model._editor_revision,snapshot:Object.fromEntries(fields.map(key=>[key,model[key]]))};
 });
 const linesArgs={base_revision:linesBase.revision,base_snapshot:linesBase.snapshot,patch:{lines:['A later chat edit','changes only the','requested wording.']}};
 const linesEnvelope=await choicePage.request.post(base+'/call',{data:{name:'quote_card_builder_update_editor',arguments:linesArgs}}).then(response=>response.json());
 const linesUpdate=linesEnvelope.structuredContent||linesEnvelope.structured_content;
 assert.ok(linesUpdate?.update&&linesUpdate.valid&&linesUpdate.rendered,'lines-only follow-up returns a tagged rendered update');
 const canonicalLinesText='A later chat edit\nchanges only the\nrequested wording.';
 assert.equal(linesUpdate.editor_state.text,canonicalLinesText,'server snapshot uses the line breaks that the renderer received');
 assert.deepEqual(linesUpdate.editor_state.lines,linesArgs.patch.lines);
 await choicePage.evaluate(args=>document.querySelector('#app').contentWindow.postMessage({jsonrpc:'2.0',method:'ui/notifications/tool-input',params:{name:'quote_card_builder_update_editor',arguments:args}},location.origin),linesArgs);
 await wait(200);
 assert.ok((await choiceFrame.locator('#text').innerText()).includes('A later chat edit changes only the requested wording.'),'line-only tool input does not directly overwrite the mounted editor');
 await choicePage.evaluate(result=>document.querySelector('#app').contentWindow.postMessage({jsonrpc:'2.0',method:'ui/notifications/tool-result',params:result},location.origin),linesUpdate);
 try { await choiceFrame.waitForFunction(text=>{const value=document.querySelector('#text').innerText;return value.replace(/\s+/g,' ').trim()===text.replace(/\s+/g,' ').trim()&&value.includes('\n')},canonicalLinesText,{timeout:30000}); }
 catch (error) { console.error('lines-only browser state',JSON.stringify({frame:await choiceFrame.evaluate(()=>({text:document.querySelector('#text').innerText,textContent:document.querySelector('#text').textContent,status:document.querySelector('#status').innerText,errors:document.querySelector('#errors').innerText,revision:JSON.parse(localStorage.getItem('quote-card-builder.workspace.v1'))?.modelContent?._editor_revision})),context:await choicePage.evaluate(()=>contexts.at(-1)?.structuredContent?.modelContent),base:linesArgs})); throw error; }
 await choicePage.waitForFunction(text=>contexts.some(item=>item.structuredContent?.modelContent?.text===text),canonicalLinesText,{timeout:10000});
 const linesContext=await choicePage.evaluate(text=>contexts.filter(item=>item.structuredContent?.modelContent?.text===text).at(-1).structuredContent.modelContent,canonicalLinesText);
 assert.equal(linesContext.transformation,'EDITED','automatic preview keeps the accepted chat edit transformation');
 assert.equal(linesContext.evidence_status,'UNVERIFIED','automatic preview keeps the accepted chat edit evidence status');
 const linesEditorText=await choiceFrame.locator('#text').innerText();
 assert.equal(await choiceFrame.locator('#attribution').inputValue(),'A chosen author','line-only update preserves the selected author');
 assert.equal(await choiceFrame.locator('#paletteDecision').inputValue(),'custom','line-only update preserves the selected palette');
 await choiceFrame.locator('#text').fill('A manual change after chat remains the current draft.');
 await choicePage.evaluate(result=>document.querySelector('#app').contentWindow.postMessage({jsonrpc:'2.0',method:'ui/notifications/tool-result',params:result},location.origin),followup);
 await wait(250);
 assert.equal((await choiceFrame.locator('#text').innerText()).replace(/\s+/g,' ').trim(),'A manual change after chat remains the current draft.','replayed update cannot overwrite a later manual edit');

 const seededContext=await browser.newContext({viewport:{width:1000,height:760}});
 const seededPage=await seededContext.newPage();
 await seededPage.goto(base);
 const seededFrame=seededPage.frames().find(candidate=>candidate.url().endsWith('/workspace'));
 await seededFrame.locator('#text').waitFor();
 await wait(100);
 await seededPage.evaluate(result=>document.querySelector('#app').contentWindow.postMessage({jsonrpc:'2.0',method:'ui/notifications/tool-result',params:result},location.origin),followup);
 await seededFrame.waitForFunction(()=>document.querySelector('#text').innerText.includes('A later chat edit changes only the requested wording.'),undefined,{timeout:30000});
 assert.equal(await seededFrame.locator('#attributionDecision').inputValue(),'named','a fresh widget seeds the tagged update with its author');
 assert.equal(await seededFrame.locator('#attribution').inputValue(),'A chosen author');
 assert.equal(await seededFrame.locator('#paletteDecision').inputValue(),'custom','a fresh widget seeds the tagged update with its custom palette');
 const updateRestoredContext=await browser.newContext({viewport:{width:1000,height:760}});
 await updateRestoredContext.addInitScript(revision=>localStorage.setItem('quote-card-builder.workspace.v1',JSON.stringify({schema:'qcb-workspace-draft',schemaVersion:1,modelContent:{text:'A persisted manual draft wins.',format:'4x5',attribution:'Saved author',profile_mode:'neutral',transformation:'USER_SUPPLIED',evidence_status:'USER_SUPPLIED',direction:'editorial',graphic_mode:'auto',graphic_variant:'cover',graphic_seed:0,text_scale:1,vertical_position:'center',palette:{name:'Neutral',colors:{primary:'#072743',accent:'#E3F4FF',background:'#FEFDFB',text:'#323232'}},lines:null,styles:[],alt_text:'Saved card',_editor_revision:revision}})),followup.editor_revision);
 const updateRestoredPage=await updateRestoredContext.newPage();
 await updateRestoredPage.goto(base);
 const restoredUpdateFrame=updateRestoredPage.frames().find(candidate=>candidate.url().endsWith('/workspace'));
 await restoredUpdateFrame.locator('#text').waitFor();
 await restoredUpdateFrame.waitForFunction(()=>document.querySelector('#text').innerText.includes('A persisted manual draft wins.'),undefined,{timeout:10000});
 await updateRestoredPage.evaluate(result=>document.querySelector('#app').contentWindow.postMessage({jsonrpc:'2.0',method:'ui/notifications/tool-result',params:result},location.origin),followup);
 await wait(250);
 assert.equal((await restoredUpdateFrame.locator('#text').innerText()).replace(/\s+/g,' ').trim(),'A persisted manual draft wins.','a restored draft takes precedence over a replayed chat result');

 const lateInputContext=await browser.newContext({viewport:{width:1000,height:760}});
 const lateInputPage=await lateInputContext.newPage();
 await lateInputPage.goto(base);
 const lateInputFrame=lateInputPage.frames().find(candidate=>candidate.url().endsWith('/workspace'));
 await lateInputFrame.locator('#demoHelper').waitFor({state:'visible',timeout:6000});
 const lateInput={text:'Late approved input replaces an untouched example.',attribution:'A real author',palette:{name:'Explicit test palette',colors:{primary:'#123456',accent:'#FFF4CC',background:'#FFFFFF',text:'#111111'}}};
 await lateInputPage.evaluate(input=>document.querySelector('#app').contentWindow.postMessage({jsonrpc:'2.0',method:'ui/notifications/tool-input',params:input},location.origin),lateInput);
 await lateInputFrame.waitForFunction(()=>document.querySelector('#text').innerText.trim()==='Late approved input replaces an untouched example.');
 assert.equal(await lateInputFrame.locator('#demoHelper').isVisible(),false,'late approved input replaces the untouched demo');
 const lateResultResponse=await lateInputPage.request.post(base+'/call',{data:{name:'preview_quote_card',arguments:lateInput}});
 const lateResultEnvelope=await lateResultResponse.json();
 const lateResult=lateResultEnvelope.structuredContent;
 assert.ok(lateResult?.valid&&lateResult?.rendered&&lateResult?.editor_state,'deployed preview result includes real editable preview state');
 await lateInputPage.evaluate(result=>document.querySelector('#app').contentWindow.postMessage({jsonrpc:'2.0',method:'ui/notifications/tool-result',params:result},location.origin),lateResult);
 await lateInputFrame.locator('#image svg').waitFor({timeout:30000});
 assert.equal((await lateInputFrame.locator('#text').innerText()).trim(),lateInput.text);
 assert.equal(await lateInputFrame.locator('#attributionDecision').inputValue(),'named','late result retains its explicit author choice');
 assert.equal(await lateInputFrame.locator('#attribution').inputValue(),'A real author');
 assert.equal(await lateInputFrame.locator('#paletteDecision').inputValue(),'custom','late result retains its explicit palette choice');
 assert.equal(await lateInputFrame.locator('#demoHelper').isVisible(),false);

 const restoredContext=await browser.newContext({viewport:{width:1000,height:760}});
 await restoredContext.addInitScript(()=>localStorage.setItem('quote-card-builder.workspace.v1',JSON.stringify({schema:'qcb-workspace-draft',schemaVersion:1,modelContent:{text:'Le idee migliori\nmeritano\ndi essere\ncondivise.',attribution:'',_workspace:{attributionDecision:'none',paletteDecision:'neutral'}}})));
 const restoredPage=await restoredContext.newPage();
 await restoredPage.goto(base);
 const restoredFrame=restoredPage.frames().find(candidate=>candidate.url().endsWith('/workspace'));
 await restoredFrame.locator('#text').waitFor();
 await wait(2300);
 assert.equal((await restoredFrame.locator('#text').innerText()).trim(),'Le idee migliori\nmeritano\ndi essere\ncondivise.','same-text saved draft outranks demo');
 assert.equal(await restoredFrame.locator('#attributionDecision').inputValue(),'none');
 assert.equal(await restoredFrame.locator('#paletteDecision').inputValue(),'neutral');
 assert.equal(await restoredFrame.locator('#demoHelper').isVisible(),false,'same text without a demo marker stays personal');

 const legacyContext=await browser.newContext({viewport:{width:1000,height:760}});
 await legacyContext.addInitScript(()=>localStorage.setItem('quote-card-builder.workspace.v1',JSON.stringify({schema:'qcb-workspace-draft',schemaVersion:1,modelContent:{text:'A legacy quote without an author.',attribution:'',_workspace:{attributionDecision:'',paletteDecision:''}}})));
 const legacyPage=await legacyContext.newPage();
 await legacyPage.goto(base);
 const legacyFrame=legacyPage.frames().find(candidate=>candidate.url().endsWith('/workspace'));
 await legacyFrame.locator('#text').waitFor();
 await wait(2300);
 assert.equal(await legacyFrame.locator('#attributionDecision').inputValue(),'none','legacy empty attribution decision becomes no attribution');
 assert.equal(await legacyFrame.locator('#paletteDecision').inputValue(),'neutral','legacy empty palette decision becomes neutral');
 assert.equal(await legacyFrame.locator('#produce').isEnabled(),true,'a legacy unattributed draft is ready after restoration');

 const legacyNamedContext=await browser.newContext({viewport:{width:1000,height:760}});
 await legacyNamedContext.addInitScript(()=>localStorage.setItem('quote-card-builder.workspace.v1',JSON.stringify({schema:'qcb-workspace-draft',schemaVersion:1,modelContent:{text:'A legacy attributed quote.',attribution:'Legacy source',_workspace:{attributionDecision:'',paletteDecision:'neutral'}}})));
 const legacyNamedPage=await legacyNamedContext.newPage();
 await legacyNamedPage.goto(base);
 const legacyNamedFrame=legacyNamedPage.frames().find(candidate=>candidate.url().endsWith('/workspace'));
 await legacyNamedFrame.locator('#text').waitFor();
 await wait(2300);
 assert.equal(await legacyNamedFrame.locator('#attributionDecision').inputValue(),'named','legacy attribution text remains named');
 assert.equal(await legacyNamedFrame.locator('#attribution').inputValue(),'Legacy source');

 const namedBlankContext=await browser.newContext({viewport:{width:1000,height:760}});
 await namedBlankContext.addInitScript(()=>localStorage.setItem('quote-card-builder.workspace.v1',JSON.stringify({schema:'qcb-workspace-draft',schemaVersion:1,modelContent:{text:'A named attribution still needs a value.',attribution:'',_workspace:{attributionDecision:'named',paletteDecision:'neutral'}}})));
 const namedBlankPage=await namedBlankContext.newPage();
 await namedBlankPage.goto(base);
 const namedBlankFrame=namedBlankPage.frames().find(candidate=>candidate.url().endsWith('/workspace'));
 await namedBlankFrame.locator('#text').waitFor();
 await wait(2300);
 assert.equal(await namedBlankFrame.locator('#attributionDecision').inputValue(),'named','explicit named decision is preserved even when blank');
 assert.equal(await namedBlankFrame.locator('#produce').isDisabled(),true,'restored named attribution with no value stays invalid');
 const markedContext=await browser.newContext({viewport:{width:1000,height:760}});
 await markedContext.addInitScript(()=>localStorage.setItem('quote-card-builder.workspace.v1',JSON.stringify({schema:'qcb-workspace-draft',schemaVersion:1,modelContent:{text:'Le idee migliori\nmeritano\ndi essere\ncondivise.',attribution:'',_workspace:{attributionDecision:'none',paletteDecision:'neutral',demoExample:true}}})));
 const markedPage=await markedContext.newPage();
 await markedPage.goto(base);
 const markedFrame=markedPage.frames().find(candidate=>candidate.url().endsWith('/workspace'));
 await markedFrame.locator('#text').waitFor();
 assert.equal(await markedFrame.locator('#demoHelper').isVisible(),true,'restored marked demo keeps its helper');
 assert.equal(await markedFrame.locator('#demoNoneOption').innerText(),'Scelta demo: nessuna attribuzione');
 assert.equal(await markedFrame.locator('#demoNeutralOption').innerText(),'Palette neutra demo');
 assert.equal(await restoredPage.evaluate(()=>messages.length),0,'remote workspace did not send any chat message');
 assert.equal(await page.evaluate(()=>messages.length),0,'download clicks did not send any chat message');
 assert.deepEqual(pageErrors,[],'browser reported no uncaught JavaScript errors');

 await page.screenshot({path:path.join(out,'remote-smoke.png'),fullPage:true});
 const evidence={
   host:'simulated MCP Apps host',backend:'deployed Quote Card Builder Streamable HTTP MCP endpoint',
   remoteMcpEndpoint:remoteEndpoint.remote_mcp_url,workspaceResource:remoteEndpoint.workspace_resource,
   browser:'real Chrome via Playwright',simulatedHostOnly:true,realChatGPTChatVerified:false,
   example:'Le idee migliori\nmeritano\ndi essere\ncondivise.',editedQuote,linesOnlyEditorText:linesEditorText,linesOnlyModelText:linesContext.text,
   canonicalSvgFontSize:{fourLineDemo:demoFontSize,priorSingleLine:singleLineFontSize},
   iframeSandbox:'allow-scripts allow-same-origin; downloads prohibited',
   failedThenSuccessfulPublishAttempts:await countCalls('quote_card_builder_publish_png'),productionCalls:await countCalls('produce_quote_card'),
   publishedFilename:publishedContent.filename,publishedSha256:publishedContent.sha256,
   downloadedBytes:browserPng.length,downloadUrl:firstOpenLink.url,
   browserDownloadSha256:hash(browserPng),fetchedHttpSha256:hash(remoteBytes),editedPngSha256:hash(editedPng),
   openLinkRequests:await page.evaluate(()=>openLinks.map(item=>item.url)),chatMessages:await page.evaluate(()=>messages.length),
   checks:['four-line Italian demo appears only after alias grace','editor and canonical SVG show bold, italic, and highlight styling','canonical fitted font size exceeds prior one-line sample','desktop, mobile, and renderer screenshots captured','formatting and whitespace edits retain demo marker/helper/neutral palette','editor caret survives preview hydration after formatting','named attribution without a value remains blocked after render','typing a changed demo quote preserves no-attribution and neutral defaults','New Card and attr-less input default to no attribution and neutral palette','legacy empty decisions map to none/neutral and legacy author text maps to named','explicit restored named-but-empty attribution remains invalid','user-selected author and custom palette survive editing the demo quote','one Download PNG click produces and starts a real remote PNG download','failed publication stays retryable and reuses production','unchanged click reuses PNG and publication','edited quote triggers fresh production and publication','browser PNG SHA256 matches the deployed publish result','download bytes match the public HTTPS endpoint','same-text unmarked restored draft remains personal','marked restored demo keeps its helper','immediate explicit input suppresses demo seeding','late explicit input replaces untouched demo','late explicit input and deployed tool result hydrate real editor content','follow-up chat edit uses full assistant-visible snapshot and current revision','tool-input replay alone leaves the mounted editor unchanged','tagged chat update changes only its explicit fields and preserves author/palette','lines-only chat update keeps canonical line breaks in editor and model context through automatic preview','replayed update cannot overwrite a later manual edit','fresh widget seeds from a tagged update result','restored local draft takes precedence over an older chat result','375px layout has no horizontal overflow','keyboard focus on Download PNG stays visible','no ui/message or chat send call occurred'],
 };
 fs.writeFileSync(path.join(out,'remote-browser-results.json'),JSON.stringify(evidence,null,2)+'\n');
 console.log(JSON.stringify(evidence,null,2));
 await updateRestoredContext.close();await seededContext.close();await namedBlankContext.close();await legacyNamedContext.close();await legacyContext.close();await markedContext.close();await restoredContext.close();await choiceContext.close();await lateInputContext.close();await inputContext.close();await context.close();await browser.close();
})().catch(error=>{console.error(error);process.exit(1)});
