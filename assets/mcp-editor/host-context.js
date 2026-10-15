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
  const WORKSPACE_SCHEMA = "qcb-workspace-draft";
  const WORKSPACE_STORAGE_KEY = "quote-card-builder.workspace.v1";
  const BASES_STORAGE_KEY = "quote-card-builder.bases.v1";
  const PROJECT_SCHEMA = "qcb-card-project";
  const BASE_SCHEMA = "qcb-personal-base";
  const BASE_FIELDS = ["format", "profile_mode", "direction", "graphic_mode", "graphic_variant", "logo_mode", "graphic_seed", "text_scale", "vertical_position", "palette", "visual_grammar", "composition", "quote_font_size", "author_font_size", "brand_kit"];
  const EDITOR_FIELDS = ["text", "format", "attribution", "profile_mode", "transformation", "evidence_status", "direction", "graphic_mode", "graphic_variant", "logo_mode", "graphic_seed", "text_scale", "vertical_position", "palette", "lines", "styles", "alt_text", "visual_grammar", "composition", "composition_candidates", "proposal_source", "quote_font_size", "author_font_size", "brand_kit"];
  const MODEL_FIELDS = EDITOR_FIELDS.filter((key) => key !== "brand_kit");
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

  function cardSnapshot(value) {
    const source = ownObject(value);
    return clone(Object.fromEntries(EDITOR_FIELDS.filter((key) => Object.prototype.hasOwnProperty.call(source, key)).map((key) => [key, source[key]])));
  }

  function modelSnapshot(value) {
    const source = ownObject(value);
    const snapshot = clone(Object.fromEntries(MODEL_FIELDS.filter((key) => Object.prototype.hasOwnProperty.call(source, key)).map((key) => [key, source[key]])));
    for (const key of ["_editor_revision", "_editor_update_status", "_workspace"]) {
      if (Object.prototype.hasOwnProperty.call(source, key)) snapshot[key] = clone(source[key]);
    }
    if (typeof source.brand_kit_attached === "boolean") snapshot.brand_kit_attached = source.brand_kit_attached;
    if (isObject(source.brand_summary)) snapshot.brand_summary = clone(source.brand_summary);
    if (isObject(source.brand_kit)) {
      snapshot.brand_kit_attached = true;
      const summary = {};
      if (typeof source.brand_kit.name === "string") summary.name = source.brand_kit.name;
      if (typeof source.brand_kit.font?.family === "string") summary.font_family = source.brand_kit.font.family;
      summary.logo_present = isObject(source.brand_kit.logo) && typeof source.brand_kit.logo.data_base64 === "string";
      snapshot.brand_summary = summary;
    }
    return snapshot;
  }

  function projectFromDraft(value, name = "Quote card") {
    return { schema:PROJECT_SCHEMA, schemaVersion:1, name:String(name || "Quote card").slice(0, 80), draft:cardSnapshot(value) };
  }

  function baseFromDraft(value, name = "Personal base") {
    const source = ownObject(value);
    const design = clone(Object.fromEntries(BASE_FIELDS.filter((key) => Object.prototype.hasOwnProperty.call(source, key)).map((key) => [key, source[key]])));
    return {schema:BASE_SCHEMA, schemaVersion:2, name:String(name || "Personal base").slice(0, 80), design};
  }

  function normalizeBase(value) {
    if (!isObject(value)) throw new Error("Use a Quote Card Builder personal base JSON.");
    if (value.schema !== undefined) {
      if (value.schema !== BASE_SCHEMA || value.schemaVersion !== 2 || !isObject(value.design)) throw new Error("Use a supported Quote Card Builder personal base JSON.");
      const design = Object.fromEntries(BASE_FIELDS.filter((key) => Object.prototype.hasOwnProperty.call(value.design, key)).map((key) => [key, value.design[key]]));
      return {schema:BASE_SCHEMA, schemaVersion:2, name:String(value.name || "Personal base").slice(0, 80), design:clone(design)};
    }
    // Stored v1 bases contained the full draft. Keep their identity/name while
    // dropping quote content as they are read.
    if (isObject(value.draft)) return {schema:BASE_SCHEMA, schemaVersion:2, name:String(value.name || "Personal base").slice(0, 80), design:baseFromDraft(value.draft).design};
    // Older editor callers passed the saved draft directly to reuseBase.
    if (typeof value.text === "string") return baseFromDraft(value);
    throw new Error("Use a Quote Card Builder personal base JSON.");
  }

  function draftFromBase(value, text = "", attribution = "") {
    const base = normalizeBase(value);
    return {...clone(base.design), text:String(text || ""), attribution:String(attribution || ""), lines:String(text || "").includes("\n") ? String(text).split("\n") : null, styles:[], alt_text:"", transformation:"VERBATIM", evidence_status:"USER_SUPPLIED", quote_font_size:null};
  }

  function exportBase(value) { return JSON.stringify(normalizeBase(value), null, 2); }
  function importBase(value) {
    let parsed = value;
    if (typeof value === "string") { try { parsed = JSON.parse(value); } catch (_) { throw new Error("Use a valid personal base JSON file."); } }
    if (!isObject(parsed) || parsed.schema !== BASE_SCHEMA || parsed.schemaVersion !== 2 || !isObject(parsed.design)) throw new Error("Use a supported Quote Card Builder personal base JSON.");
    return normalizeBase(parsed);
  }

  function draftFromProject(value) {
    if (!isObject(value) || value.schema !== PROJECT_SCHEMA || value.schemaVersion !== 1 || !isObject(value.draft) || typeof value.draft.text !== "string") throw new Error("Use a Quote Card Builder project JSON exported from this editor.");
    return cardSnapshot(value.draft);
  }

  function reuseBase(value, text, attribution, mode = "card", currentDraft) {
    const base = normalizeBase(value);
    const sourceDraft = isObject(currentDraft) ? currentDraft : (isObject(value) && isObject(value.draft) ? value.draft : (isObject(value) && typeof value.text === "string" ? value : null));
    const source = sourceDraft || {};
    const previous = String(source.text || "");
    const next = String(text || "");
    const sameWords = previous.replace(/\s+/gu, " ").trim() === next.replace(/\s+/gu, " ").trim();
    const draft = {...clone(base.design), text:previous, lines:source.lines, styles:clone(source.styles || []), alt_text:source.alt_text || "", transformation:source.transformation || "VERBATIM", evidence_status:source.evidence_status || "USER_SUPPLIED"};
    if (sameWords && JSON.stringify(source.composition) === JSON.stringify(base.design.composition)) {
      if (Object.prototype.hasOwnProperty.call(source, "proposal_source")) draft.proposal_source = source.proposal_source;
      if (Object.prototype.hasOwnProperty.call(source, "composition_candidates")) draft.composition_candidates = clone(source.composition_candidates);
    }
    draft.text = next;
    draft.lines = next.includes("\n") ? next.split("\n") : null;
    draft.attribution = attribution !== undefined && attribution !== null ? String(attribution) : (sameWords ? String(source.attribution || "") : "");
    if (!sameWords) {
      draft.styles = [];
      draft.quote_font_size = null;
      draft.transformation = "VERBATIM";
      draft.evidence_status = "USER_SUPPLIED";
      draft.alt_text = "";
    } else if (previous !== next) {
      const before = Array.from(previous).map((char, index) => ({char, index})).filter((item) => !/\s/u.test(item.char));
      const after = Array.from(next).map((char, index) => ({char, index})).filter((item) => !/\s/u.test(item.char));
      draft.styles = (draft.styles || []).flatMap((style) => {
        const indices = before.map((item, ordinal) => ({...item, ordinal})).filter((item) => item.index >= style.start && item.index < style.end);
        return indices.length ? [{...style, start:after[indices[0].ordinal].index, end:after[indices.at(-1).ordinal].index + 1}] : [];
      });
    }
    const reuseComposition = mode === "style" ? clone(draft.composition) : null;
    if (mode === "style") {
      draft.composition = null;
      draft.composition_candidates = [];
      draft.proposal_source = "demo";
      draft.graphic_seed = ((Number(draft.graphic_seed) || 0) + 1) % 1000000;
    }
    return {draft, reuse_composition:reuseComposition};
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
    if (isObject(value.params)) return value.params;
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
      this.workspace = config.workspace === true;
      this.storageKey = typeof config.storageKey === "string" && config.storageKey ? config.storageKey : WORKSPACE_STORAGE_KEY;
      this.storage = config.storage !== undefined ? config.storage : null;
      this.request = typeof config.request === "function" ? config.request : null;
      this._getWidgetState = typeof config.getWidgetState === "function" ? config.getWidgetState : null;
      this._setWidgetState = typeof config.setWidgetState === "function" ? config.setWidgetState : null;
      this.onRestore = typeof config.onRestore === "function" ? config.onRestore : function noop() {};
      this.onAuthoritativeResult = typeof config.onAuthoritativeResult === "function" ? config.onAuthoritativeResult : function noop() {};
      this.onThemeChange = typeof config.onThemeChange === "function" ? config.onThemeChange : function noop() {};
      this.onPersistenceStatus = typeof config.onPersistenceStatus === "function" ? config.onPersistenceStatus : function noop() {};
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
      this._modelContextUpdateId = null;
      this._persistenceAvailable = !this.workspace;
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
        // Attachments are a live host selection.  Never restore an old file
        // reference after the host removes or remounts the app.
        imageIds: [],
      };
    }

    _workspaceStorage() {
      if (!this.workspace) return null;
      if (this.storage) return this.storage;
      try { return this.root && this.root.localStorage ? this.root.localStorage : null; }
      catch (_) { return null; }
    }

    _baseStorage() {
      if (this.storage) return this.storage;
      try { return this.root && this.root.localStorage ? this.root.localStorage : null; }
      catch (_) { return null; }
    }

    _readBaseStore() {
      const value = JSON.parse(this._baseStorage()?.getItem(BASES_STORAGE_KEY) || "null");
      if (!isObject(value) || value.schema !== "qcb-card-bases" || value.schemaVersion !== 1 || !Array.isArray(value.bases)) return null;
      const sourceBases = value.bases.filter((item) => isObject(item) && typeof item.id === "string" && typeof item.name === "string" && (isObject(item.design) || isObject(item.draft)));
      const bases = sourceBases.map((item) => ({id:item.id, ...normalizeBase(item)}));
      const archivedProjects = Array.isArray(value.archivedProjects) ? clone(value.archivedProjects) : [];
      const archivedIds = new Set(archivedProjects.filter(isObject).map((item) => item.id).filter((id) => typeof id === "string"));
      for (const item of sourceBases) {
        if (isObject(item.draft) && !archivedIds.has(item.id)) {
          archivedProjects.push({...projectFromDraft(item.draft, item.name), id:item.id});
          archivedIds.add(item.id);
        }
      }
      return {bases, archivedProjects, needsMigration:sourceBases.some((item) => isObject(item.draft))};
    }

    _persistBaseStore(store) {
      this._baseStorage()?.setItem(BASES_STORAGE_KEY, JSON.stringify({schema:"qcb-card-bases", schemaVersion:1, bases:store.bases, archivedProjects:store.archivedProjects}));
    }

    listBases() {
      try {
        const store = this._readBaseStore();
        if (!store) return [];
        if (store.needsMigration) { try { this._persistBaseStore(store); } catch (_) { /* old storage remains intact; return the migrated view */ } }
        return store.bases;
      } catch (_) { return []; }
    }

    listArchivedProjects() {
      try {
        const store = this._readBaseStore();
        if (!store) return [];
        if (store.needsMigration) { try { this._persistBaseStore(store); } catch (_) { /* archive remains available in this read */ } }
        return clone(store.archivedProjects);
      } catch (_) { return []; }
    }

    saveBase(name, value) {
      const label = String(name || "").trim();
      if (!label || label.length > 80) throw new Error("Name the base using 1–80 characters.");
      const base = normalizeBase(isObject(value) && value.schema === BASE_SCHEMA ? {...value, name:label} : baseFromDraft(value, label));
      if (base.design.visual_grammar && (!["ribbons", "urban"].includes(base.design.visual_grammar) || !base.design.composition)) throw new Error("Choose a composition before saving a personal base.");
      const storage = this._baseStorage();
      if (!storage || typeof storage.setItem !== "function") throw new Error("This host cannot save bases on the device. The project JSON remains available.");
      const store = this._readBaseStore() || {bases:[], archivedProjects:[], needsMigration:false};
      const bases = store.bases;
      const previous = bases.find((item) => item.name === label);
      const item = {id:previous?.id || `base-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`, ...base};
      const next = previous ? bases.map((base) => base.id === previous.id ? item : base) : [...bases, item];
      this._persistBaseStore({...store, bases:next.slice(-50)});
      return clone(item);
    }

    _reportPersistence(available, message) {
      this._persistenceAvailable = Boolean(available);
      try { this.onPersistenceStatus({ available:this._persistenceAvailable, message:String(message || "") }); }
      catch (_) { /* status reporting must not break the editor */ }
    }

    _readWorkspaceState() {
      const storage = this._workspaceStorage();
      if (!storage || typeof storage.getItem !== "function") {
        this._reportPersistence(false, "Draft recovery is unavailable in this host.");
        return null;
      }
      try {
        const raw = storage.getItem(this.storageKey);
        this._reportPersistence(true, raw ? "Saved draft found." : "Drafts are saved on this device.");
        if (!raw) return null;
        const value = JSON.parse(raw);
        if (!isObject(value) || value.schema !== WORKSPACE_SCHEMA || value.schemaVersion !== SCHEMA_VERSION) return null;
        if (!meaningfulContent(value.modelContent)) return null;
        return {
          schema: STATE_SCHEMA,
          schemaVersion: SCHEMA_VERSION,
          modelContent: clone(value.modelContent),
          privateContent: {},
          imageIds: [],
        };
      } catch (_) {
        this._reportPersistence(false, "Draft recovery is unavailable in this host.");
        return null;
      }
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

    _writeWorkspaceState() {
      const storage = this._workspaceStorage();
      if (!storage || typeof storage.setItem !== "function") {
        this._reportPersistence(false, "Changes stay open, but cannot be recovered after closing.");
        return false;
      }
      try {
        if (!meaningfulContent(this._draft)) {
          if (typeof storage.removeItem === "function") storage.removeItem(this.storageKey);
          this._reportPersistence(true, "No local draft saved yet.");
          return true;
        }
        storage.setItem(this.storageKey, JSON.stringify({
          schema: WORKSPACE_SCHEMA,
          schemaVersion: SCHEMA_VERSION,
          modelContent: clone(this._draft),
        }));
        this._reportPersistence(true, "Draft saved on this device.");
        return true;
      } catch (_) {
        this._reportPersistence(false, "Changes stay open, but cannot be recovered after closing.");
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
      const modelContent = modelSnapshot(this._draft);
      const payload = {
        schema: STATE_SCHEMA,
        schemaVersion: SCHEMA_VERSION,
        modelContent,
      };
      const params = {
        structuredContent: payload,
        content: meaningfulContent(modelContent) ? [{
          type: "text",
          text: this._modelContextSummary(modelContent),
          annotations: { audience:["assistant"] },
        }] : [],
      };
      return this._sendRequest("ui/update-model-context", params).then((result) => {
        const resultModelContext = isObject(result) && isObject(result._meta)
          ? result._meta["openai/modelContext"]
          : null;
        if (isObject(resultModelContext) && typeof resultModelContext.updateId === "string" && resultModelContext.updateId) {
          this._modelContextUpdateId = resultModelContext.updateId;
        }
        return result;
      }).catch(() => null);
    }

    _modelContextSummary(modelContent) {
      const workspace = ownObject(modelContent._workspace);
      const textStatus = typeof modelContent.text === "string" && modelContent.text.trim() ? "quote supplied" : "quote missing";
      const attribution = workspace.attributionDecision === "none" ? "no attribution" :
        (typeof modelContent.attribution === "string" && modelContent.attribution.trim() ? "attribution supplied" : "attribution undecided");
      const palette = workspace.paletteDecision === "neutral" ? "neutral palette selected" :
        (workspace.paletteDecision === "custom" ? "custom palette selected" : "palette undecided");
      const format = typeof modelContent.format === "string" ? `format ${modelContent.format}` : "format undecided";
      const editorFields = MODEL_FIELDS;
      const snapshot = Object.fromEntries(editorFields.filter((key) => Object.prototype.hasOwnProperty.call(modelContent, key)).map((key) => [key, modelContent[key]]));
      if (modelContent.brand_kit_attached === true) snapshot.brand_kit_attached = true;
      if (isObject(modelContent.brand_summary)) snapshot.brand_summary = clone(modelContent.brand_summary);
      const revision = Number.isSafeInteger(modelContent._editor_revision) ? modelContent._editor_revision : 0;
      const updateStatus = typeof modelContent._editor_update_status === "string" && modelContent._editor_update_status ? ` Update status: ${modelContent._editor_update_status}.` : "";
      return `Quote Card Builder draft: ${textStatus}; ${attribution}; ${palette}; ${format}. Current editor_revision=${revision}. Current editor snapshot: ${JSON.stringify(snapshot)}.${updateStatus} For an explicit follow-up edit, copy this snapshot unchanged as base_snapshot, use this revision as base_revision, and include only requested changes in patch.`;
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
      const suppliedModelContext = Object.prototype.hasOwnProperty.call(supplied, "modelContext")
        ? supplied.modelContext
        : supplied["openai/modelContext"];
      if (suppliedModelContext === null) {
        this._imageIds = [];
        this._privateContent = {};
        this.persistNow();
      } else if (isObject(suppliedModelContext) && typeof suppliedModelContext.updateId === "string") {
        this._modelContextUpdateId = suppliedModelContext.updateId;
      }
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
        const safeArea = ownObject(next.safeAreaInsets);
        for (const edge of ["top", "right", "bottom", "left"]) {
          const suppliedValue = safeArea[edge];
          const value = typeof suppliedValue === "number" ? `${Math.max(0, suppliedValue)}px` :
            (typeof suppliedValue === "string" && suppliedValue.trim() ? suppliedValue.trim() : "0px");
          style.setProperty(`--qcb-safe-area-${edge}`, value);
        }
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
      const restored = this.workspace ? this._readWorkspaceState() : this._readWidgetState();
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
      return this.workspace ? this._writeWorkspaceState() : this._writeWidgetState();
    }

    clearDraft() {
      if (this._persistTimer !== null) this._clearTimeout(this._persistTimer);
      if (this._contextTimer !== null) this._clearTimeout(this._contextTimer);
      this._persistTimer = null;
      this._contextTimer = null;
      this._draft = {};
      this._privateContent = {};
      this._imageIds = [];
      this._authoritativeResult = null;
      this._restored = false;
      this._sendModelContext().catch(() => null);
      if (!this.workspace) return this._writeWidgetState();
      const storage = this._workspaceStorage();
      if (!storage || typeof storage.removeItem !== "function") {
        this._reportPersistence(false, "The saved draft could not be cleared in this host.");
        return false;
      }
      try {
        storage.removeItem(this.storageKey);
        this._reportPersistence(true, "New card started. The previous local draft was cleared.");
        return true;
      } catch (_) {
        this._reportPersistence(false, "The saved draft could not be cleared in this host.");
        return false;
      }
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
        persistenceAvailable: this._persistenceAvailable,
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
  QcbHostContext.WORKSPACE_SCHEMA = WORKSPACE_SCHEMA;
  QcbHostContext.WORKSPACE_STORAGE_KEY = WORKSPACE_STORAGE_KEY;
  QcbHostContext.BASES_STORAGE_KEY = BASES_STORAGE_KEY;
  QcbHostContext.BASE_SCHEMA = BASE_SCHEMA;
  QcbHostContext.EDITOR_FIELDS = EDITOR_FIELDS;
  QcbHostContext.MODEL_FIELDS = MODEL_FIELDS;
  QcbHostContext.cardSnapshot = cardSnapshot;
  QcbHostContext.modelSnapshot = modelSnapshot;
  QcbHostContext.projectFromDraft = projectFromDraft;
  QcbHostContext.draftFromProject = draftFromProject;
  QcbHostContext.baseFromDraft = baseFromDraft;
  QcbHostContext.draftFromBase = draftFromBase;
  QcbHostContext.importBase = importBase;
  QcbHostContext.exportBase = exportBase;
  QcbHostContext.reuseBase = reuseBase;
  QcbHostContext.create = (options) => new QcbHostContext(options);
  return QcbHostContext;
});
