"""Run a read-only MCP handshake against the owner-private Site."""

import json
import subprocess
import sys


if sys.stdin.isatty():
    import termios

    original_terminal = termios.tcgetattr(sys.stdin.fileno())
    hidden_terminal = termios.tcgetattr(sys.stdin.fileno())
    hidden_terminal[3] &= ~termios.ECHO
    termios.tcsetattr(sys.stdin.fileno(), termios.TCSANOW, hidden_terminal)
else:
    original_terminal = None
try:
    config = json.loads(sys.stdin.readline())
finally:
    if original_terminal is not None:
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSANOW, original_terminal)
url = config["url"].rstrip("/") + config.get("mcp_path", "/api/mcp")
token = config["token"]


def call(payload, session_id=None):
    args = [
        "curl", "--config", "-", "--silent", "--show-error",
        "--max-time", "30", "--dump-header", "-", "--request", "POST",
        "--header", "Content-Type: application/json",
        "--header", "Accept: application/json, text/event-stream",
        "--header", "MCP-Protocol-Version: 2025-06-18",
    ]
    if session_id:
        args += ["--header", "Mcp-Session-Id: " + session_id]
    args += ["--data-binary", json.dumps(payload, separators=(",", ":")), url]
    result = subprocess.run(
        args,
        input='header = "OAI-Sites-Authorization: Bearer ' + token + '"\n',
        capture_output=True,
        text=True,
        timeout=35,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip())
    headers, separator, body = result.stdout.partition("\r\n\r\n")
    if not separator:
        headers, _, body = result.stdout.partition("\n\n")
    status = headers.splitlines()[0].strip() if headers else "missing status"
    session = next(
        (line.split(":", 1)[1].strip() for line in headers.splitlines()
         if line.lower().startswith("mcp-session-id:")),
        None,
    )
    print(status, "session=" + str(bool(session)), "response_bytes=" + str(len(body)))
    event = next((line[6:] for line in body.splitlines() if line.startswith("data: ")), None)
    if not status.endswith(" 200") or not event:
        raise RuntimeError("MCP response was not a successful SSE message")
    return session, json.loads(event)


session, _ = call({
    "jsonrpc": "2.0", "id": 1, "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "qcb-sites-pilot", "version": "0.1.0"},
    },
})
_, listing = call({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
                  None if config.get("omit_session") else session)
tools = listing.get("result", {}).get("tools", [])
names = [tool.get("name") for tool in tools]
print("tools:", names)
assert "quote_card_builder_open_editor" in names
editor = next(tool for tool in tools if tool.get("name") == "quote_card_builder_open_editor")
resource_uri = editor.get("_meta", {}).get("ui", {}).get("resourceUri")
assert resource_uri and resource_uri.startswith("ui://")
print("editor resource:", resource_uri)
_, resource = call({
    "jsonrpc": "2.0", "id": 3, "method": "resources/read",
    "params": {"uri": resource_uri},
}, None if config.get("omit_session") else session)
contents = resource.get("result", {}).get("contents", [])
assert any(content.get("mimeType", "").startswith("text/html") and content.get("text") for content in contents)
print("UI resource: readable HTML")

if config.get("test_tool_call"):
    _, tool_result = call({
        "jsonrpc": "2.0", "id": 4, "method": "tools/call",
        "params": {
            "name": "quote_card_builder_open_editor",
            "arguments": {
                "text": "Pilot tecnico Sites MCP.",
                "attribution": "Test interno",
                "profile_mode": "neutral",
            },
        },
    }, None if config.get("omit_session") else session)
    result = tool_result.get("result", {})
    assert result and not result.get("isError"), tool_result.get("error", "MCP tool failed")
    print("read-only editor tool: successful with synthetic test text")
