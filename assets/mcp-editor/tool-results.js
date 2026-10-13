/* Read portable MCP results and ChatGPT's compatibility envelope. */
(function (root) {
  "use strict";
  const envelopeKeys = ["call_tool_result", "mcp_tool_result", "result", "params", "toolResult", "tool_result", "output"];

  function read(message, metadata) {
    const visited = new Set();
    function visit(value) {
      if (!value || typeof value !== "object" || visited.has(value)) return null;
      visited.add(value);
      const structured = value.structuredContent || value.structured_content;
      if (structured && typeof structured === "object") {
        return { ...structured, ...(typeof value._meta?.quoteCard?.svg === "string" ? { svg:value._meta.quoteCard.svg } : {}) };
      }
      for (const key of envelopeKeys) {
        const result = visit(value[key]);
        if (result) return result;
      }
      if (typeof value.valid === "boolean" && typeof value.rendered === "boolean") return { ...value };
      for (const item of value.content || []) {
        if (item?.type !== "text" || typeof item.text !== "string") continue;
        try { const result = visit(JSON.parse(item.text)); if (result) return result; } catch (_) { /* not structured JSON */ }
      }
      return null;
    }
    // Metadata retains the complete result on ChatGPT when toolOutput is compact.
    const result = visit(metadata) || visit(message);
    if (!result) return null;
    return result;
  }
  root.QcbToolResults = { read };
})(typeof window !== "undefined" ? window : globalThis);
