"""Browser verification host: emulates MCP Apps messages, not the Codex client."""
import asyncio
import base64
import json
import os
from pathlib import Path
import sys
from unittest import mock
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'work/extensions-verification'
OUTPUT.mkdir(parents=True, exist_ok=True)
PORT = int(os.environ.get('QCB_TEST_PORT', '8766'))
sys.path.insert(0, str(ROOT / "scripts"))
import mcp_app
import mcp_server
from mcp import Client
from mcp.client import advertise

async def call_tool(name, arguments, local=False):
    with mock.patch.object(mcp_server, "LOCAL_FILE_DELIVERY", local), mock.patch.object(Path, "home", return_value=OUTPUT / "local-home"):
        return await _call_tool(name, arguments)

async def _call_tool(name, arguments):
    async with Client(mcp_server.mcp, extensions=[advertise("io.modelcontextprotocol/ui", {"mimeTypes": ["text/html;profile=mcp-app"]})]) as client:
        result = await client.call_tool(name, arguments)
        return result.model_dump(mode="json", by_alias=True, exclude_none=True)

PAGE = '''<!doctype html><html><head><style>html,body{margin:0;height:100%;}iframe{border:0;width:100%;height:100%;display:block}</style></head><body><iframe id="app" src="/ui"></iframe><script>
window.calls=[];window.contexts=[];window.downloads=[];window.messages=[];window.openedFiles=[];
const frame=document.querySelector('iframe');
window.sendHost=(params)=>frame.contentWindow.postMessage({jsonrpc:'2.0',method:'ui/notifications/host-context-changed',params},location.origin);
addEventListener('message',async event=>{
 if(event.source!==frame.contentWindow)return;
 const m=event.data;if(!m||m.jsonrpc!=='2.0')return;
 if(m.method==='ui/notifications/initialized'&&location.pathname==='/inline'){
  const result=await fetch(location.pathname==='/local'?'/call-local':'/call',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:'quote_card_builder_open_editor',arguments:{text:'Inline compatibility remains intact.',attribution:'Test',profile_mode:'neutral'}})}).then(r=>r.json());
  frame.contentWindow.postMessage({jsonrpc:'2.0',method:'ui/notifications/tool-result',params:result},location.origin);
 }
 if(m.id===undefined)return;
 try{let result={};
 if(m.method==='ui/initialize'){const chatFallback=['/chat','/local'].includes(location.pathname);result={protocolVersion:'2026-01-26',hostInfo:{name:'qcb-test-host',version:'26.1011.11113'},hostCapabilities:chatFallback?{message:{resource:{},image:{}},updateModelContext:{structuredContent:{},text:{}},experimental:{'openai/modelContext':{},'openai/files':{}}}:{downloadFile:{},updateModelContext:{structuredContent:{},text:{}},experimental:{'openai/modelContext':{}}},hostContext:{theme:'light',displayMode:'fullscreen',availableDisplayModes:['inline','fullscreen'],styles:{variables:{'--font-sans':'Arial, sans-serif'}}}};}
 else if(m.method==='tools/call'){window.calls.push(m.params);result=await fetch(location.pathname==='/local'?'/call-local':'/call',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(m.params)}).then(r=>r.json());}
 else if(m.method==='ui/update-model-context'){window.contexts.push(m.params);result={_meta:{'openai/modelContext':{updateId:String(window.contexts.length)}}};}
 else if(m.method==='ui/download-file'){window.downloads.push(m.params);const item=await fetch('/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(m.params)}).then(r=>r.json());const link=document.createElement('a');link.href='/download';link.download=item.filename;link.click();}
 else if(m.method==='openai/files/open'){window.openedFiles.push(m.params);result={};}
 else if(m.method==='ui/message'){window.messages.push(m.params);result={};}
 frame.contentWindow.postMessage({jsonrpc:'2.0',id:m.id,result},location.origin);
 }catch(e){frame.contentWindow.postMessage({jsonrpc:'2.0',id:m.id,error:{code:-32603,message:String(e)}},location.origin);}
});
</script></body></html>'''

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass
    def respond(self, body, mime='application/json'):
        if not isinstance(body, bytes): body=body.encode()
        self.send_response(200);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    def do_GET(self):
        if self.path=='/ui': self.respond(mcp_app.quote_card_preview_html(workspace=True),'text/html')
        elif self.path=='/inline-ui': self.respond(mcp_app.quote_card_preview_html(),'text/html')
        elif self.path=='/local': self.respond(PAGE.replace('<iframe id="app"', '<iframe sandbox="allow-scripts allow-same-origin" id="app"'),'text/html')
        elif self.path=='/inline': self.respond(PAGE.replace('src="/ui"','src="/inline-ui"'),'text/html')
        elif self.path=='/download': self.respond((OUTPUT/'generated.png').read_bytes(),'image/png')
        else: self.respond(PAGE,'text/html')
    def do_POST(self):
        data=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        if self.path=='/save':
            resource=data['contents'][0]['resource'];(OUTPUT/'generated.png').write_bytes(base64.b64decode(resource['blob']))
            result={'filename':'quote-card-browser-proof.png'}
        else:
            result=asyncio.run(call_tool(data['name'],data.get('arguments',{}),local=self.path=='/call-local'))
        self.respond(json.dumps(result))

server=ThreadingHTTPServer(('127.0.0.1',PORT),Handler)
print(f'http://127.0.0.1:{PORT}',flush=True)
server.serve_forever()
