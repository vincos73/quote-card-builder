import assert from "node:assert/strict";
import test from "node:test";
import worker from "../src/worker.mjs";

async function withFetch(mock, callback) {
  const original = globalThis.fetch;
  globalThis.fetch = mock;
  try {
    await callback();
  } finally {
    globalThis.fetch = original;
  }
}

test("serves the private pilot page", async () => {
  const response = await worker.fetch(new Request("https://pilot.example/"));
  assert.equal(response.status, 200);
  assert.match(await response.text(), /Sites MCP pilot/);
});

test("proxies modern server discovery directly and preserves the JSON-RPC body and safe headers", async () => {
  const requestBody = JSON.stringify({
    jsonrpc: "2.0",
    id: 1,
    method: "server/discover",
    params: { _meta: { "openai/subject": "preserve-this-extension" }, capability: "tools" },
  });
  let observed;
  await withFetch(async (url, options) => {
    observed = { url: String(url), options, body: await new Response(options.body).text() };
    return new Response('{"jsonrpc":"2.0","id":1,"result":{"tools":[]}}', {
      status: 200,
      headers: {
        "content-type": "application/json",
        "cache-control": "no-store",
        "mcp-protocol-version": "2026-07-28",
        "set-cookie": "backend=secret",
        "x-internal-debug": "private",
      },
    });
  }, async () => {
    const response = await worker.fetch(new Request("https://pilot.example/mcp?source=chatgpt", {
      method: "POST",
      headers: {
        accept: "application/json, text/event-stream",
        "content-type": "application/json",
        "mcp-protocol-version": "2025-06-18",
        "last-event-id": "event-7",
        authorization: "Bearer site-token",
        cookie: "session=site-cookie",
        "x-forwarded-user": "site-identity",
        "x-unrelated": "must-not-pass",
      },
      body: requestBody,
    }));

    assert.equal(response.status, 200);
    assert.equal(observed.url, "https://quote-card-builder-mcp-960066178304.europe-west8.run.app/mcp?source=chatgpt");
    assert.equal(observed.options.method, "POST");
    assert.equal(observed.body, requestBody);
    assert.deepEqual([...observed.options.headers.keys()].sort(), [
      "accept", "content-type", "last-event-id", "mcp-protocol-version",
    ]);
    assert.equal(observed.options.headers.get("mcp-protocol-version"), "2025-06-18");
    assert.equal(response.headers.get("set-cookie"), null);
    assert.equal(response.headers.get("mcp-protocol-version"), "2026-07-28");
    assert.equal(response.headers.get("x-internal-debug"), null);
    assert.equal(response.headers.get("x-qcb-sites-pilot"), "proxy-v2");
    assert.match(await response.text(), /"tools":\[\]/);
  });
});

test("proxies legacy tool calls directly through /api/mcp without a session handshake", async () => {
  const requestBody = JSON.stringify({
    jsonrpc: "2.0",
    id: 22,
    method: "tools/call",
    params: { name: "render_quote_card", arguments: { quote: "Ciao", _meta: { trace: "abc" } } },
  });
  let observed;
  await withFetch(async (url, options) => {
    observed = { url: String(url), options, body: await new Response(options.body).text() };
    return new Response('{"jsonrpc":"2.0","id":22,"result":{"content":[]}}', {
      headers: { "content-type": "application/json" },
    });
  }, async () => {
    const response = await worker.fetch(new Request("https://pilot.example/api/mcp", {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "mcp-session-id": "stale-client-session",
        cookie: "private=1",
      },
      body: requestBody,
    }));

    assert.equal(response.status, 200);
    assert.equal(observed.url, "https://quote-card-builder-mcp-960066178304.europe-west8.run.app/mcp");
    assert.equal(observed.options.method, "POST");
    assert.equal(observed.body, requestBody);
    assert.equal(observed.options.headers.has("mcp-session-id"), false);
    assert.equal(observed.options.headers.has("cookie"), false);
    assert.equal(observed.options.headers.has("authorization"), false);
  });
});

test("passes upstream MCP errors through with status and body while filtering headers", async () => {
  await withFetch(async () => new Response('{"error":"unsupported method"}', {
    status: 400,
    headers: { "content-type": "application/json", "retry-after": "3", "www-authenticate": "secret" },
  }), async () => {
    const response = await worker.fetch(new Request("https://pilot.example/mcp", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: '{"jsonrpc":"2.0","id":3,"method":"tools/list"}',
    }));
    assert.equal(response.status, 400);
    assert.equal(response.headers.get("retry-after"), "3");
    assert.equal(response.headers.get("www-authenticate"), null);
    assert.equal(await response.text(), '{"error":"unsupported method"}');
  });
});

test("returns a gateway error when the renderer cannot be reached", async () => {
  await withFetch(async () => { throw new Error("network unavailable"); }, async () => {
    const response = await worker.fetch(new Request("https://pilot.example/mcp", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: '{"jsonrpc":"2.0","id":4,"method":"tools/list"}',
    }));
    assert.equal(response.status, 502);
    assert.match(await response.text(), /renderer unavailable/);
  });
});

test("does not expose other upstream paths", async () => {
  const response = await worker.fetch(new Request("https://pilot.example/admin"));
  assert.equal(response.status, 404);
});
