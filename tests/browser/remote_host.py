"""Simulated UI host for a real remote Quote Card Builder MCP endpoint."""
import asyncio
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "work/remote-mcp/browser"
OUTPUT.mkdir(parents=True, exist_ok=True)
REMOTE_URL = os.environ.get("QCB_REMOTE_MCP_URL", "").strip()
PORT = int(os.environ.get("QCB_REMOTE_TEST_PORT", "8776"))
FAIL_FIRST_PUBLISH = os.environ.get("QCB_REMOTE_TEST_FAIL_FIRST_PUBLISH", "1") == "1"
publish_attempts = 0
if not REMOTE_URL:
    raise SystemExit("Set QCB_REMOTE_MCP_URL to the deployed Streamable HTTP MCP endpoint (for example https://host/mcp).")
if urlsplit(REMOTE_URL).scheme not in {"http", "https"} or not urlsplit(REMOTE_URL).netloc:
    raise SystemExit("QCB_REMOTE_MCP_URL must be an HTTP or HTTPS MCP endpoint URL.")

from mcp import Client
from mcp.client import advertise

EXTENSIONS = [advertise("io.modelcontextprotocol/ui", {"mimeTypes": ["text/html;profile=mcp-app"]})]


async def remote_call(name, arguments):
    async with Client(REMOTE_URL, mode="auto", extensions=EXTENSIONS) as client:
        result = await client.call_tool(name, arguments)
        return result.model_dump(mode="json", by_alias=True, exclude_none=True)


async def load_workspace_html():
    async with Client(REMOTE_URL, mode="auto", extensions=EXTENSIONS) as client:
        resources = await client.list_resources()
        workspace = next(
            (str(item.uri) for item in resources.resources if "/workspace/" in str(item.uri)),
            None,
        )
        if not workspace:
            raise RuntimeError("The deployed MCP endpoint does not advertise a workspace editor resource.")
        contents = await client.read_resource(workspace)
        if not contents.contents or not getattr(contents.contents[0], "text", None):
            raise RuntimeError("The deployed workspace editor resource was empty.")
        return contents.contents[0].text, workspace


WORKSPACE_HTML, WORKSPACE_URI = asyncio.run(load_workspace_html())

PAGE = r'''<!doctype html><html><head><meta charset="utf-8"><style>html,body{margin:0;height:100%;}iframe{border:0;width:100%;height:100%;display:block}</style></head><body><iframe sandbox="allow-scripts allow-same-origin" id="app" src="/workspace"></iframe><script>
window.calls=[];window.messages=[];window.contexts=[];window.toolResults=[];window.openLinks=[];window.notifications=[];
const frame=document.querySelector('iframe');
addEventListener('message',async event=>{
 if(event.source!==frame.contentWindow)return;
 const m=event.data;if(!m||m.jsonrpc!=='2.0')return;
 if(m.id===undefined){if(typeof m.method==='string'&&m.method.startsWith('ui/notifications/'))window.notifications.push(m);return;}
 try{let result={};
 if(m.method==='ui/initialize')result={protocolVersion:'2026-01-26',hostInfo:{name:'qcb-remote-browser-host',version:'1.0'},hostCapabilities:{updateModelContext:{structuredContent:{},text:{}},experimental:{'openai/modelContext':{}}},hostContext:{theme:'dark',displayMode:'fullscreen',availableDisplayModes:['inline','fullscreen']}};
 else if(m.method==='tools/call'){window.calls.push(m.params);result=await fetch('/call',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(m.params)}).then(r=>r.json());window.toolResults.push({name:m.params.name,result});}
 else if(m.method==='ui/update-model-context'){window.contexts.push(m.params);result={_meta:{'openai/modelContext':{updateId:String(window.contexts.length)}}};}
 else if(m.method==='ui/message'){window.messages.push(m.params);result={};}
 else if(m.method==='ui/open-link'){window.openLinks.push(m.params);const link=document.createElement('a');link.href=m.params.url;link.rel='noopener';document.body.append(link);link.click();link.remove();result={};}
 frame.contentWindow.postMessage({jsonrpc:'2.0',id:m.id,result},location.origin);
 }catch(e){frame.contentWindow.postMessage({jsonrpc:'2.0',id:m.id,error:{code:-32603,message:String(e)}},location.origin);}
});
</script></body></html>'''


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def respond(self, body, mime="application/json"):
        if not isinstance(body, bytes):
            body = body.encode()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/workspace":
            self.respond(WORKSPACE_HTML, "text/html;profile=mcp-app")
        elif self.path == "/health":
            self.respond(json.dumps({"status": "ok", "workspace_resource": WORKSPACE_URI, "remote_mcp_url": REMOTE_URL, "fail_first_publish": FAIL_FIRST_PUBLISH, "publish_attempts": publish_attempts}))
        else:
            self.respond(PAGE, "text/html")

    def do_POST(self):
        global publish_attempts
        try:
            data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
            if self.path == "/reset":
                publish_attempts = 0
                self.respond(json.dumps({"status": "ok", "publish_attempts": publish_attempts, "fail_first_publish": FAIL_FIRST_PUBLISH}))
                return
            if self.path != "/call":
                self.send_error(404)
                return
            if data.get("name") == "quote_card_builder_publish_png":
                publish_attempts += 1
                if FAIL_FIRST_PUBLISH and publish_attempts == 1:
                    self.respond(json.dumps({
                        "isError": True,
                        "content": [{"type": "text", "text": "Temporary download service failure. Retry the download."}],
                    }))
                    return
            result = asyncio.run(remote_call(data["name"], data.get("arguments", {})))
            self.respond(json.dumps(result))
        except Exception as error:
            self.send_error(502, explain=str(error))


server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
print(f"http://127.0.0.1:{PORT} (simulated host; remote MCP: {REMOTE_URL})", flush=True)
server.serve_forever()
