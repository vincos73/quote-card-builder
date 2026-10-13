const RENDERER_ORIGIN = "https://quote-card-builder-mcp-960066178304.europe-west8.run.app";

// Forward only MCP transport headers. Site cookies, credentials, identity and
// unrelated forwarding headers must never reach the renderer.
const REQUEST_HEADERS = [
  "accept",
  "content-type",
  "mcp-protocol-version",
  "last-event-id",
];

const RESPONSE_HEADERS = [
  "content-type",
  "mcp-protocol-version",
  "cache-control",
  "retry-after",
];

function html() {
  return new Response(`<!doctype html>
<html lang="it"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Quote Card Builder · Sites MCP pilot</title>
<style>body{font:16px/1.5 system-ui,sans-serif;max-width:42rem;margin:10vh auto;padding:0 1.5rem;color:#072743;background:#fefdfb}h1{font-size:2rem}code{background:#e3f4ff;padding:.15rem .35rem}</style>
<h1>Quote Card Builder · Sites MCP pilot</h1>
<p>Questa istanza privata verifica il trasporto MCP tramite Sites. Il rendering della card è eseguito dal servizio canonico Quote Card Builder.</p>
<p>Endpoint MCP: <code>/mcp</code></p></html>`, {
    headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" },
  });
}

async function proxy(request, targetPath) {
  const incoming = new URL(request.url);
  const target = new URL(targetPath + incoming.search, RENDERER_ORIGIN);
  const headers = new Headers();
  for (const name of REQUEST_HEADERS) {
    const value = request.headers.get(name);
    if (value !== null) headers.set(name, value);
  }

  let upstream;
  try {
    upstream = await fetch(target, {
      method: request.method,
      headers,
      body: request.method === "GET" || request.method === "HEAD" ? undefined : request.body,
      redirect: "manual",
    });
  } catch {
    return new Response("MCP renderer unavailable", {
      status: 502,
      headers: { "content-type": "text/plain; charset=utf-8", "cache-control": "no-store" },
    });
  }

  const responseHeaders = new Headers();
  for (const name of RESPONSE_HEADERS) {
    const value = upstream.headers.get(name);
    if (value !== null) responseHeaders.set(name, value);
  }
  responseHeaders.set("x-qcb-sites-pilot", "proxy-v2");
  return new Response(upstream.body, { status: upstream.status, headers: responseHeaders });
}

export default {
  async fetch(request) {
    const { pathname } = new URL(request.url);
    if (pathname === "/" && request.method === "GET") return html();
    if (pathname === "/health" && request.method === "GET") return proxy(request, "/health");
    if (pathname === "/mcp" || pathname === "/api/mcp") return proxy(request, "/mcp");
    return new Response("Not found", { status: 404 });
  },
};
