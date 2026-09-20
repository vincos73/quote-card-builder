/*
 * Small, dependency-free bridge for Quote Card Builder's host state.
 *
 * The editor owns the live draft.  This helper only provides the optional
 * MCP Apps persistence/context plumbing around it, so a missing host bridge
 * is a supported mode rather than an error.
 */
(function installQcbHostContext(globalObject, factory) {
  const api = factory(globalObject);
  if (typeof module === "object" && module.exports) module.exports = api;
  if (globalObject) globalObject.QcbHostContext = api;
})(typeof globalThis === "object" ? globalThis : this, function createQcbHostContextFactory(root) {
  "use strict";

  const SCHEMA_VERSION = 1;
  const STATE_SCHEMA = "qcb-editor-state";
  const DEFAULT_DEBOUNCE_MS = 160;

  function isObject(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
  }

  function clone(value) {
    if (value === undefined) return undefined;
    if (typeof structuredClone === "function") {
      try { return structuredClone(value); } catch (_) { /* use JSON below */ }
    }
    try { return JSON.parse(JSON.stringify(value)); } catch (_) { return value; }
  }

  function ownObject(value) {
    return isObject(value) ? value : {};
  }

  function meaningfulContent(value) {
    if (typeof value === "string") return value.trim().length > 0;
    return isObject(value) && Object.keys(value).length > 0;
  }

  function contentFrom(value) {
    if (!isObject(value)) return null;
    if (isObject(value.modelContent)) return value.modelContent;
    if (isObject(value.editor_state)) return value.editor_state;
    if (isObject(value.arguments)) return value.arguments;
    // A result envelope is not a draft.  Avoid accidentally putting SVG or
    // validation metadata in widgetState when a caller passes a full result.
    if ("valid" in value || "rendered" in value || "produced" in value || "svg" in value) return null;
    return value;
  }

  function normalizeImageIds(value) {
    if (!Array.isArray(value)) return [];
    return value.filter((item) => typeof item === "string" && item.trim()).map((item) => item.trim());
  }

  function extractHostContext(value) {
    if (!value) return null;
    if (isObject(value.hostContext)) return value.hostContext;
    if (isObject(value.params) && isObject(value.params.hostContext)) return value.params.hostContext;
    if (isObject(value.params) && (value.params.styles || value.params.theme)) return value.params;
    if (isObject(value.detail) && isObject(value.detail.hostContext)) return value.detail.hostContext;
    if (isObject(value.detail) && (value.detail.styles || value.detail.theme)) return value.detail;
    return isObject(value) ? value : null;
  }

  class QcbHostContext {
    constructor(options) {
      const config = ownObject(options);
      this.options = config;
      this.root = config.root || root || {};
      this.document = config.document || this.root.document;
      this.bridge = config.openai !== undefined ? config.openai : this.root.openai;
      this.request = typeof config.request === "function" ? config.request : null;
      this._getWidgetState = typeof config.getWidgetState === "function" ? config.getWidgetState : null;
      this._setWidgetState = typeof config.setWidgetState === "function" ? config.setWidgetState : null;
      this.onRestore = typeof config.onRestore === "function" ? config.onRestore : function noop() {};
      this.onAuthoritativeResult = typeof config.onAuthoritativeResult === "function" ? config.onAuthoritativeResult : function noop() {};
      this.onThemeChange = typeof config.onThemeChange === "function" ? config.onThemeChange : function noop() {};
      this.debounceMs = Number.isFinite(config.debounceMs) ? Math.max(0, config.debounceMs) : DEFAULT_DEBOUNCE_MS;
      this._setTimeout = config.setTimeout || (typeof this.root.setTimeout === "function" ? this.root.setTimeout.bind(this.root) : setTimeout);
      this._clearTimeout = config.clearTimeout || (typeof this.root.clearTimeout === "function" ? this.root.clearTimeout.bind(this.root) : clearTimeout);
      this._persistTimer = null;
      this._contextTimer = null;
      this._initialized = false;
      this._restored = false;
      this._hostContext = null;
      this._appliedHostVariables = new Set();
      this._authoritativeResult = null;
      this._draft = {};
      this._privateContent = {};
      this._imageIds = [];
      this._hostContextHandler = (event) => {
        if (event && this.root.parent && event.source !== this.root.parent) return;
        const message = event && event.data ? event.data : event;
        if (message && message.method && message.method !== "ui/notifications/host-context-changed") return;
        if (message && message.jsonrpc !== "2.0") return;
        const context = extractHostContext(message);
        if (context) this.applyHostContext(context);
      };
      this._listenForHostContext();
    }

    _listenForHostContext() {
      if (this.root && typeof this.root.addEventListener === "function") {
        this.root.addEventListener("message", this._hostContextHandler);
      }
    }

    _readWidgetState() {
      let value;
      if (this._getWidgetState) {
        try { value = this._getWidgetState(); } catch (_) { value = undefined; }
      } else if (Object.prototype.hasOwnProperty.call(this.options || {}, "widgetState")) value = this.options.widgetState;
      else {
        try { value = this.bridge && this.bridge.widgetState; } catch (_) { value = undefined; }
      }
      if (!isObject(value) || value.schemaVersion !== SCHEMA_VERSION || value.schema !== STATE_SCHEMA) return null;
      if (!meaningfulContent(value.modelContent)) return null;
      return {
        schema: STATE_SCHEMA,
        schemaVersion: SCHEMA_VERSION,
        modelContent: clone(value.modelContent),
        privateContent: clone(ownObject(value.privateContent)),
        imageIds: normalizeImageIds(value.imageIds),
      };
    }

    _writeWidgetState() {
      const writer = this._setWidgetState || (this.bridge && this.bridge.setWidgetState);
      if (typeof writer !== "function") return false;
      const state = this.getState();
      try {
        // The Apps SDK documents this as synchronous.  Ignore a thenable too:
        // hosts that implement it asynchronously still receive the snapshot.
        writer.call(this.bridge, state);
        return true;
      } catch (_) {
        return false;
      }
    }

    _schedule(kind, callback) {
      const timerName = kind === "persist" ? "_persistTimer" : "_contextTimer";
      if (this[timerName] !== null) this._clearTimeout(this[timerName]);
      const timer = this._setTimeout(() => {
        this[timerName] = null;
        try {
          const result = callback();
          if (result && typeof result.catch === "function") result.catch(() => null);
        } catch (_) { /* an unavailable host must not break editor input */ }
      }, this.debounceMs);
      // Node's timers otherwise keep small unit-test processes alive.  Browsers
      // do not expose unref, so this remains a harmless feature detection.
      if (timer && typeof timer.unref === "function") timer.unref();
      this[timerName] = timer;
    }

    _sendRequest(method, params) {
      if (this.request) {
        try { return Promise.resolve(this.request(method, params)); } catch (error) { return Promise.reject(error); }
      }
      if (method === "ui/update-model-context" && this.bridge && typeof this.bridge.updateModelContext === "function") {
        try { return Promise.resolve(this.bridge.updateModelContext(params)); } catch (error) { return Promise.reject(error); }
      }
      if (!this.root || !this.root.parent || typeof this.root.parent.postMessage !== "function") return Promise.resolve(null);
      const id = `qcb-${Date.now()}-${Math.random().toString(36).slice(2)}`;
      try {
        this.root.parent.postMessage({ jsonrpc: "2.0", id, method, params }, "*");
      } catch (error) {
        return Promise.reject(error);
      }
      return Promise.resolve(null);
    }

    _sendModelContext() {
      const modelContent = clone(this._draft);
      if (!meaningfulContent(modelContent)) return Promise.resolve(null);
      const payload = {
        schema: STATE_SCHEMA,
        schemaVersion: SCHEMA_VERSION,
        modelContent,
      };
      return this._sendRequest("ui/update-model-context", {
        structuredContent: payload,
        content: [{ type: "text", text: JSON.stringify(payload) }],
      }).catch(() => null);
    }

    applyHostContext(context) {
      const supplied = extractHostContext(context) || {};
      const previous = ownObject(this._hostContext);
      const next = { ...previous, ...clone(supplied) };
      if (previous.styles || supplied.styles) {
        next.styles = { ...ownObject(previous.styles), ...ownObject(supplied.styles) };
        next.styles.variables = { ...ownObject(previous.styles && previous.styles.variables), ...ownObject(supplied.styles && supplied.styles.variables) };
      }
      this._hostContext = clone(next);
      const variables = ownObject(next.styles && next.styles.variables);
      const style = this.document && this.document.documentElement && this.document.documentElement.style;
      if (style && typeof style.setProperty === "function") {
        this._appliedHostVariables.forEach((name) => {
          if (!Object.prototype.hasOwnProperty.call(variables, name) && typeof style.removeProperty === "function") style.removeProperty(name);
        });
        Object.keys(variables).forEach((name) => {
          if (!name.startsWith("--")) return;
          const value = variables[name];
          if (value === undefined || value === null) return;
          style.setProperty(name, String(value));
          this._appliedHostVariables.add(name);
        });
      }
      const theme = next.theme === "dark" || next.theme === "light" ? next.theme : null;
      if (this.document && this.document.documentElement && typeof this.document.documentElement.setAttribute === "function" && theme) {
        this.document.documentElement.setAttribute("data-theme", theme);
      }
      try { this.onThemeChange(clone(next), theme); } catch (_) { /* callbacks are optional */ }
      return clone(next);
    }

    initialize(payload) {
      const input = ownObject(payload);
      if (input.hostContext) this.applyHostContext(input.hostContext);
      else if (input.styles || input.theme) this.applyHostContext(input);
      const restored = this._readWidgetState();
      if (restored) {
        this._draft = clone(restored.modelContent);
        this._privateContent = clone(restored.privateContent);
        this._imageIds = normalizeImageIds(restored.imageIds);
        this._restored = true;
        try { this.onRestore(clone(this._draft), this.getState()); } catch (_) { /* callbacks are optional */ }
      }
      this._initialized = true;
      // Initial tool data is only a seed.  A persisted draft wins over it.
      if (!this._restored && input.initialInput !== undefined) this.receiveToolInput(input.initialInput, { initial: true });
      if (input.initialResult !== undefined) this.receiveToolResult(input.initialResult, { initial: true });
      return this.snapshot();
    }

    restore() {
      return this.initialize({});
    }

    receiveToolInput(value, options) {
      const config = ownObject(options);
      if (this._restored && !config.force) return false;
      const content = contentFrom(value);
      if (!meaningfulContent(content)) return false;
      this._draft = clone(content);
      if (config.force) this._restored = false;
      if (config.persist) this.persistNow();
      if (config.context) this._sendModelContext().catch(() => null);
      return true;
    }

    // Use this for an approved, current request after a restored draft.  It is
    // deliberately separate from receiveToolInput so initial notifications
    // cannot silently replace a user's persisted work.
    acceptToolInput(value) {
      return this.receiveToolInput(value, { force: true, persist: true, context: true });
    }

    handleToolInput(value, options) { return this.receiveToolInput(value, options); }

    receiveToolResult(result) {
      this._authoritativeResult = clone(result);
      try { this.onAuthoritativeResult(clone(this._authoritativeResult)); } catch (_) { /* callbacks are optional */ }
      return clone(this._authoritativeResult);
    }

    handleToolResult(result) { return this.receiveToolResult(result); }
    handleHostContextChanged(context) { return this.applyHostContext(context); }

    setDraft(value, options) {
      const config = ownObject(options);
      const content = contentFrom(value);
      if (!meaningfulContent(content)) return this.getDraft();
      this._draft = config.replace === false ? { ...this._draft, ...clone(content) } : clone(content);
      if (config.privateContent !== undefined) this.setPrivateContent(config.privateContent, { persist: false });
      if (config.imageIds !== undefined) this.setImageIds(config.imageIds, { persist: false });
      if (config.persist !== false) this.persistNow();
      if (config.context !== false) this._schedule("context", () => this._sendModelContext());
      return this.getDraft();
    }

    setModelContent(value, options) {
      return this.setDraft(value, options);
    }

    setPrivateContent(value, options) {
      const config = ownObject(options);
      if (!isObject(value)) return this.getPrivateContent();
      this._privateContent = config.replace === false ? { ...this._privateContent, ...clone(value) } : clone(value);
      if (config.persist !== false) this.persistNow();
      return this.getPrivateContent();
    }

    setImageIds(value, options) {
      const config = ownObject(options);
      if (value !== undefined && !Array.isArray(value)) return this.getImageIds();
      this._imageIds = normalizeImageIds(value);
      if (config.persist !== false) this.persistNow();
      return this.getImageIds();
    }

    persistNow() {
      if (this._persistTimer !== null) {
        this._clearTimeout(this._persistTimer);
        this._persistTimer = null;
      }
      return this._writeWidgetState();
    }

    saveState() { return this.persistNow(); }

    flush() {
      if (this._contextTimer !== null) {
        this._clearTimeout(this._contextTimer);
        this._contextTimer = null;
        this._sendModelContext();
      }
      this.persistNow();
      return this.snapshot();
    }

    getState() {
      return {
        schema: STATE_SCHEMA,
        schemaVersion: SCHEMA_VERSION,
        modelContent: clone(this._draft),
        privateContent: clone(this._privateContent),
        imageIds: normalizeImageIds(this._imageIds),
      };
    }

    snapshot() {
      return {
        ...this.getState(),
        restored: this._restored,
        initialized: this._initialized,
        hostContext: clone(this._hostContext),
        authoritativeResult: clone(this._authoritativeResult),
      };
    }

    getDraft() { return clone(this._draft); }
    getPrivateContent() { return clone(this._privateContent); }
    getImageIds() { return normalizeImageIds(this._imageIds); }
    getAuthoritativeResult() { return clone(this._authoritativeResult); }
    hasRestoredDraft() { return this._restored; }
    getHostContext() { return clone(this._hostContext); }

    destroy() {
      if (this._persistTimer !== null) this._clearTimeout(this._persistTimer);
      if (this._contextTimer !== null) this._clearTimeout(this._contextTimer);
      this._persistTimer = null;
      this._contextTimer = null;
      if (this.root && typeof this.root.removeEventListener === "function") this.root.removeEventListener("message", this._hostContextHandler);
    }
  }

  QcbHostContext.SCHEMA_VERSION = SCHEMA_VERSION;
  QcbHostContext.STATE_SCHEMA = STATE_SCHEMA;
  QcbHostContext.create = (options) => new QcbHostContext(options);
  return QcbHostContext;
});
