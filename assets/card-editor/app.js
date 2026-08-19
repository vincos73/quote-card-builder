(() => {
  'use strict';

  const $ = (selector) => document.querySelector(selector);
  const $$ = (selector) => [...document.querySelectorAll(selector)];
  const params = new URLSearchParams(location.search);
  const storageKey = `quote-card-editor:${params.get('token') || 'local'}`;
  const clone = (value) => JSON.parse(JSON.stringify(value));
  const formatting = window.QcbFormatting;
  if (!formatting) throw new Error('Motore di formattazione non disponibile');
  const {
    DIRECTION_EMPHASIS_TYPE, FILL_CYCLE, FILL_STYLE_TYPES, STYLE_TYPES, canonicalLineStart,
    clampStyleRanges, clearFillRanges, defaultEmphasisSpan, fillTypeAt, nextFillType,
    normalizeStyleRanges, normalizeText: normalize, pointLength, remapStyleRanges,
    suggestBalancedLines,
  } = formatting;
  const normalizeScale = (value) => {
    const numeric = Number(value);
    return Math.min(1, Math.max(0.8, Number.isFinite(numeric) ? numeric : 1));
  };
  const normalizeFormats = (formats) => clone(formats || []).map((format) => ({
    ...format,
    text_scale: normalizeScale(format.text_scale),
  }));
  const GRAPHIC_VARIANTS = {
    editorial: {
      style: 'Editorial',
      default: { value: 'default', label: 'Contours', icon: 'contours' },
      alternate: { value: 'rhythm_lines', label: 'Rhythm Lines', icon: 'rhythm' },
    },
    statement: {
      style: 'Poster',
      default: { value: 'default', label: 'Echo Rings', icon: 'rings' },
      alternate: { value: 'modules', label: 'Modules', icon: 'modules' },
    },
    contextual: {
      style: 'Frame',
      default: { value: 'default', label: 'Dot Grid', icon: 'dots' },
      alternate: { value: 'route_map', label: 'Route Map', icon: 'routes' },
    },
  };
  const MOTIF_ICONS = {
    contours: '<path d="M12 1c-4 3-4 6 0 8s4 5 1 8M18 1c-4 3-4 6 0 8s4 5 1 8M24 1c-4 3-4 6 0 8s4 5 1 8"/>',
    rhythm: '<path d="M8 3h18M6 7h20M4 11h22M2 15h24"/>',
    rings: '<circle cx="24" cy="4" r="4"/><circle cx="24" cy="4" r="8"/><circle cx="24" cy="4" r="12"/>',
    modules: '<g class="motif-fill"><rect x="18" y="1" width="4" height="5"/><rect x="24" y="1" width="5" height="5"/><rect x="18" y="8" width="4" height="4"/><rect x="24" y="8" width="5" height="8"/></g>',
    dots: '<g class="motif-fill"><circle cx="17" cy="4" r="1.2"/><circle cx="22" cy="4" r="1.2"/><circle cx="27" cy="4" r="1.2"/><circle cx="17" cy="9" r="1.2"/><circle cx="22" cy="9" r="1.2"/><circle cx="27" cy="9" r="1.2"/><circle cx="17" cy="14" r="1.2"/><circle cx="22" cy="14" r="1.2"/><circle cx="27" cy="14" r="1.2"/></g>',
    routes: '<path d="M2 13h8V5h7v7h9M10 13v4M17 5V1"/><g class="motif-fill"><circle cx="10" cy="13" r="1.5"/><circle cx="10" cy="5" r="1.5"/><circle cx="17" cy="5" r="1.5"/><circle cx="17" cy="12" r="1.5"/></g>',
  };
  const normalizeGraphicVariant = (direction, value) => {
    const config = GRAPHIC_VARIANTS[direction] || GRAPHIC_VARIANTS.editorial;
    return [config.default.value, config.alternate.value].includes(value) ? value : config.default.value;
  };
  // With no explicit choice, deliver only the format the user is actually
  // looking at (the first/active one) rather than all three -- "all" was a
  // silent default nobody asked for, and most edits are aimed at a single
  // aspect ratio.
  const normalizePresentation = (presentation = {}, fallbackMode = 'all', direction = 'editorial') => ({
    logo_mode: presentation.logo_mode || 'auto',
    graphic_mode: presentation.graphic_mode || 'auto',
    graphic_variant: normalizeGraphicVariant(direction, presentation.graphic_variant || 'default'),
    output_mode: presentation.output_mode || fallbackMode,
  });
  const defaultOutputMode = (manifest) => manifest.formats?.[0]?.id || 'all';
  const baselineSignature = (manifest) => JSON.stringify({
    text: manifest.content?.text || '',
    direction: manifest.direction || '',
    attribution: manifest.content?.attribution || {},
    presentation: normalizePresentation(manifest.presentation || {}, defaultOutputMode(manifest), manifest.direction),
    formats: manifest.formats || [],
  });
  const TRANSFORMATION_LABELS = {
    VERBATIM: 'Letterale', EDITED: 'Modificata', PARAPHRASE: 'Parafrasi', AI_GENERATED: 'Generata',
  };
  const EVIDENCE_LABELS = {
    VERIFIED: 'Verificata', USER_SUPPLIED: 'Fornita dall’utente', UNVERIFIED: 'Non verificata', CONFLICT: 'In conflitto',
  };
  const STYLE_LABELS = {
    bold: 'Grassetto', italic: 'Corsivo', underline: 'Sottolineato', highlight: 'Evidenziato',
    accent: 'Colore accento', outline: 'Contorno',
  };
  const FILL_LABELS = {
    none: 'nessuno', accent: 'accento', highlight: 'evidenziato', outline: 'contorno',
  };
  const CARD_COLOR_META = {
    primary: { label: 'Primario', usage: 'campo e moduli della card' },
    accent: { label: 'Accento', usage: 'testo e trattamenti in accento' },
    background: { label: 'Sfondo', usage: 'area di lettura della card' },
    text: { label: 'Testo', usage: 'citazione e attribuzione' },
  };
  const escapeHtml = (value) => String(value).replace(/[&<>"']/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  })[char]);

  const state = {
    manifest: null,
    baseline: null,
    draft: null,
    baseRevision: null,
    activeFormat: '4x5',
    previews: new Map(),
    zoom: 100,
    safeArea: true,
    timer: null,
    requestId: 0,
    qa: null,
    submitting: false,
    awaitingApply: false,
    controlsLocked: false,
    chatbotRequestId: null,
    chatbotPollTimer: null,
    graphicVariants: {},
    generatePhase: 'idle',
    dismissedGenerationRevision: null,
    renderedGenerationSignature: null,
    profiles: [],
    activeProfileId: null,
    returnUrl: '',
    resetRecovery: null,
    resetRecoveryTimer: null,
  };

  const els = {
    transformation: $('#transformation'), evidence: $('#evidence-status'),
    revision: $('#revision'), session: $('#session-state'), dot: $('#status-dot'),
    lines: $('#visual-text-editor'), formatToolbar: $('#format-toolbar'), formattingState: $('#formatting-state'),
    fillControl: $('#fill-control'), rebalance: $('#rebalance-lines'),
    colors: $('#brand-colors'), colorPaletteSubtitle: $('#color-palette-subtitle'), colorPaletteHelp: $('#color-palette-help'),
    palettePreview: $('#palette-preview'),
    profileSaveState: $('#profile-save-state'), profileSaveToggle: $('#profile-save-toggle'),
    profileExport: $('#profile-export'),
    profileSaveForm: $('#profile-save-form'), profileName: $('#profile-name'),
    profileSaveCancel: $('#profile-save-cancel'), profileSaveConfirm: $('#profile-save-confirm'),
    profileSaveFeedback: $('#profile-save-feedback'),
    fontSupport: $('#font-support-note'),
    scale: $('#scale'), scaleValue: $('#scale-value'), scaleFitNote: $('#scale-fit-note'),
    textIntegrityHint: $('#text-integrity-hint'),
    attributionLabel: $('#attribution-label'), altTextLabel: $('#alt-text-label'), altTextState: $('#alt-text-state'),
    preview: $('#preview-content'),
    shell: $('#preview-shell'), stage: $('#preview-stage'), message: $('#preview-message'),
    warningCount: $('#qa-count'), qaLabel: $('#qa-label'), draftState: $('#draft-state'),
    scoreTotal: $('#score-total'), scoreBreakdown: $('#score-breakdown'),
    actionMessage: $('#action-message'), zoom: $('#zoom-output'), safeToggle: $('#safe-toggle'),
    cvdMode: $('#cvd-mode'),
    backLink: $('#back-link'), generate: $('#generate'),
    generateLabel: $('#generate-label'), generatedOutput: $('#generated-output'),
    qaDetails: $('#qa-details'), warningList: $('#warning-list'), warningState: $('#qa-mini-state'),
    reset: $('#reset'),
  };

  const api = async (path, options = {}) => {
    const separator = path.includes('?') ? '&' : '?';
    const response = await fetch(`/api${path}${separator}token=${encodeURIComponent(params.get('token') || '')}`, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.message || body.error || `Errore ${response.status}`);
    return body;
  };

  const setMessage = (message, error = false) => {
    els.actionMessage.textContent = message;
    els.actionMessage.classList.toggle('is-error', error);
  };

  const syncActionButtons = () => {
    els.generate.disabled = state.controlsLocked;
  };

  const setButtonsDisabled = (disabled) => {
    state.controlsLocked = disabled;
    syncActionButtons();
  };

  const setGenerateState = (phase = 'idle') => {
    const processing = phase === 'preparing' || phase === 'running';
    const completedLabel = state.returnUrl ? 'Torna alla chat' : 'Chiudi editor';
    const labels = {
      idle: 'Genera',
      preparing: 'Preparo…',
      running: 'Creo PNG…',
      completed: completedLabel,
      failed: 'Riprova',
    };
    state.generatePhase = phase;
    els.generateLabel.textContent = labels[phase] || labels.idle;
    els.generate.classList.toggle('is-processing', processing);
    els.generate.classList.toggle('is-complete', phase === 'completed');
    els.generate.classList.toggle('is-failed', phase === 'failed');
    els.generate.setAttribute('aria-busy', String(processing));
    els.generate.setAttribute('aria-label', labels[phase] || labels.idle);
  };

  const currentFormat = () => state.draft?.formats.find((item) => item.id === state.activeFormat);

  const activate = (container, datasetKey, value) => {
    container.querySelectorAll('button').forEach((button) => {
      const active = button.dataset[datasetKey] === value;
      button.classList.toggle('is-active', active);
      button.setAttribute('aria-pressed', String(active));
    });
  };

  const storeDraft = () => {
    if (!state.draft) return;
    try {
      localStorage.setItem(storageKey, JSON.stringify({
        revision: state.baseRevision,
        baseline_signature: baselineSignature(state.manifest),
        draft: state.draft,
      }));
      els.draftState.textContent = 'Bozza locale salvata';
    } catch (_) {
      els.draftState.textContent = 'Bozza in memoria';
    }
  };

  const initialStyles = (content, direction) => {
    const existing = normalizeStyleRanges(content.styles || []);
    if (existing.length) return existing;
    if (content.emphasis) {
      const index = content.text.indexOf(content.emphasis);
      if (index < 0) return [];
      const start = pointLength(content.text.slice(0, index));
      return [{ start, end: start + pointLength(content.emphasis), type: 'bold' }];
    }
    // No explicit styles and no legacy emphasis: the renderer still applies
    // an automatic first-run cue (default_emphasis_span in
    // render_quote_card.py). Seed the same span here as an explicit,
    // editable style so it shows in the toolbar and the user can remove it.
    const span = defaultEmphasisSpan(content.text);
    if (!span) return [];
    const type = DIRECTION_EMPHASIS_TYPE[direction] || 'bold';
    return [{ start: span.start, end: span.end, type }];
  };

  const styleSupportedByDirection = () => true;

  const sanitizeDirectionStyles = (draft) => {
    const before = normalizeStyleRanges(draft.styles || []);
    const after = before.filter((style) => styleSupportedByDirection(style.type, draft.direction));
    draft.styles = after;
    if (after.length !== before.length) draft.styles_customized = true;
    return before.length - after.length;
  };

  const editorMarkup = (lines, styles) => {
    let cursor = 0;
    let hasText = false;
    return lines.map((line) => {
      const characters = Array.from(line);
      if (!characters.length) return '<div class="visual-line is-spacer"><br></div>';
      if (hasText) cursor += 1;
      const lineStart = cursor;
      const lineEnd = lineStart + characters.length;
      const boundaries = new Set([0, characters.length]);
      styles.forEach((style) => {
        if (style.end <= lineStart || style.start >= lineEnd) return;
        boundaries.add(Math.max(0, style.start - lineStart));
        boundaries.add(Math.min(characters.length, style.end - lineStart));
      });
      const points = [...boundaries].sort((first, second) => first - second);
      const fragments = [];
      for (let index = 0; index < points.length - 1; index += 1) {
        const localStart = points[index];
        const localEnd = points[index + 1];
        const globalStart = lineStart + localStart;
        const globalEnd = lineStart + localEnd;
        const active = styles
          .filter((style) => style.start <= globalStart && style.end >= globalEnd)
          .map((style) => `style-${style.type}`);
        const className = active.length ? ` class="${active.join(' ')}"` : '';
        fragments.push(`<span data-start="${globalStart}" data-end="${globalEnd}"${className}>${escapeHtml(characters.slice(localStart, localEnd).join(''))}</span>`);
      }
      cursor = lineEnd;
      hasText = true;
      return `<div class="visual-line">${fragments.join('')}</div>`;
    }).join('');
  };

  const renderVisualEditor = () => {
    const format = currentFormat();
    if (!format) return;
    els.lines.innerHTML = editorMarkup(format.lines, state.draft.styles);
  };

  const editorLines = () => {
    const nodes = [...els.lines.childNodes];
    const hasBlockMarkup = nodes.some((node) => node.nodeType === Node.ELEMENT_NODE);
    const values = hasBlockMarkup
      ? nodes.flatMap((node) => {
        if (node.nodeType === Node.TEXT_NODE) return String(node.textContent || '').split('\n');
        if (node.nodeName === 'BR') return [''];
        return String(node.textContent || '').split('\n');
      })
      : els.lines.innerText.replace(/\r/g, '').split('\n');
    return values.map((line) => line.replace(/\u00a0/g, ' ').trim());
  };

  const selectionOffsets = () => {
    const selection = window.getSelection();
    if (!selection || selection.rangeCount !== 1 || selection.isCollapsed) return null;
    const range = selection.getRangeAt(0);
    const startNode = range.startContainer.nodeType === Node.ELEMENT_NODE ? range.startContainer : range.startContainer.parentElement;
    const endNode = range.endContainer.nodeType === Node.ELEMENT_NODE ? range.endContainer : range.endContainer.parentElement;
    if (!els.lines.contains(startNode) || !els.lines.contains(endNode)) return null;
    const limit = pointLength(state.draft.text);
    const lines = editorLines();
    const boundaryOffset = (container, offset) => {
      if (container === els.lines) {
        if (offset <= 0) return 0;
        if (offset >= els.lines.childNodes.length) return limit;
      }
      const element = container.nodeType === Node.ELEMENT_NODE ? container : container.parentElement;
      const span = element?.closest?.('span[data-start]');
      if (span && els.lines.contains(span)) {
        const prefixRange = document.createRange();
        prefixRange.selectNodeContents(span);
        prefixRange.setEnd(container, offset);
        return Number(span.dataset.start) + pointLength(prefixRange.toString());
      }
      const visualLine = element?.closest?.('.visual-line');
      if (visualLine && els.lines.contains(visualLine)) {
        const visualLines = [...els.lines.querySelectorAll(':scope > .visual-line')];
        const index = visualLines.indexOf(visualLine);
        const prefixRange = document.createRange();
        prefixRange.selectNodeContents(visualLine);
        prefixRange.setEnd(container, offset);
        return canonicalLineStart(lines, index) + pointLength(normalize(prefixRange.toString()));
      }
      const prefixRange = document.createRange();
      prefixRange.selectNodeContents(els.lines);
      prefixRange.setEnd(container, offset);
      return pointLength(normalize(prefixRange.toString()));
    };
    const start = Math.min(boundaryOffset(range.startContainer, range.startOffset), limit);
    const end = Math.min(boundaryOffset(range.endContainer, range.endOffset), limit);
    return start < end ? { start, end } : null;
  };

  // The inverse of selectionOffsets: find the DOM position a canonical
  // offset sits at. Offsets on a boundary belong to two spans at once, so a
  // range start leans into the following span and a range end into the
  // preceding one -- otherwise a restored selection collapses at every seam.
  const domPoint = (offset, leading) => {
    const candidates = [...els.lines.querySelectorAll('span[data-start]')].filter(
      (span) => Number(span.dataset.start) <= offset && offset <= Number(span.dataset.end),
    );
    if (!candidates.length) return null;
    const span = leading
      ? candidates.find((item) => offset < Number(item.dataset.end)) || candidates.at(-1)
      : candidates.filter((item) => offset > Number(item.dataset.start)).at(-1) || candidates[0];
    const node = span.firstChild;
    if (!node) return { node: span, offset: 0 };
    const text = String(node.textContent || '');
    const local = offset - Number(span.dataset.start);
    // Offsets count code points; a DOM offset counts UTF-16 units.
    return { node, offset: Math.min(Array.from(text).slice(0, local).join('').length, text.length) };
  };

  // renderVisualEditor() rebuilds the editor's markup from scratch, which
  // drops the selection with it. Re-anchoring on the canonical offsets lets a
  // second treatment land on the same words without reselecting them.
  const restoreSelection = (start, end) => {
    const from = domPoint(start, true);
    const to = domPoint(end, false);
    const selection = window.getSelection();
    if (!from || !to || !selection) return false;
    try {
      const range = document.createRange();
      range.setStart(from.node, from.offset);
      range.setEnd(to.node, to.offset);
      if (document.activeElement !== els.lines) els.lines.focus({ preventScroll: true });
      selection.removeAllRanges();
      selection.addRange(range);
      return true;
    } catch (_) {
      return false;
    }
  };

  // The editor owns undo for its own content. Rebuilding innerHTML on every
  // treatment already wipes the browser's native history, so leaving Cmd+Z to
  // the browser lost typed text and could never recover a style at all.
  const HISTORY_LIMIT = 60;
  const history = { entries: [], index: -1, timer: null };

  const historySnapshot = () => ({
    text: state.draft.text,
    lines: [...(currentFormat()?.lines || [])],
    styles: clone(state.draft.styles),
    styles_customized: Boolean(state.draft.styles_customized),
    selection: selectionOffsets(),
  });

  const commitHistory = () => {
    clearTimeout(history.timer);
    history.timer = null;
    if (!state.draft) return;
    updateActiveFormat();
    const entry = historySnapshot();
    const current = history.entries[history.index];
    // Selection alone is not a change worth an undo step.
    if (current
      && current.text === entry.text
      && JSON.stringify(current.lines) === JSON.stringify(entry.lines)
      && JSON.stringify(current.styles) === JSON.stringify(entry.styles)) return;
    history.entries = [...history.entries.slice(0, history.index + 1), entry].slice(-HISTORY_LIMIT);
    history.index = history.entries.length - 1;
  };

  // Coalesce a burst of typing into one undo step, the way a text field does.
  const scheduleHistoryCommit = () => {
    clearTimeout(history.timer);
    history.timer = setTimeout(commitHistory, 500);
  };

  const resetHistory = () => {
    clearTimeout(history.timer);
    history.timer = null;
    history.entries = state.draft ? [historySnapshot()] : [];
    history.index = history.entries.length - 1;
  };

  const restoreHistory = (step) => {
    // Commit whatever is still pending first, so the step lands on the state
    // before the current edit rather than skipping over it.
    commitHistory();
    const target = history.index + step;
    if (target < 0 || target >= history.entries.length) {
      els.formattingState.textContent = step < 0 ? 'Niente da annullare' : 'Niente da ripristinare';
      return false;
    }
    history.index = target;
    const entry = history.entries[target];
    state.draft.text = entry.text;
    state.draft.styles = clone(entry.styles);
    state.draft.styles_customized = entry.styles_customized;
    state.draft.formats.forEach((format) => { format.lines = [...entry.lines]; });
    renderVisualEditor();
    if (entry.selection) restoreSelection(entry.selection.start, entry.selection.end);
    syncFillControl();
    els.formattingState.textContent = step < 0 ? 'Annullato' : 'Ripristinato';
    schedulePreview();
    return true;
  };

  const toggleStyleRange = (type, start, end) => {
    const normalized = normalizeStyleRanges(state.draft.styles);
    const own = normalized.filter((item) => item.type === type);
    const others = normalized.filter((item) => item.type !== type);
    let cursor = start;
    own.forEach((item) => {
      if (item.end <= cursor || item.start > cursor) return;
      cursor = Math.max(cursor, item.end);
    });
    const fullyCovered = cursor >= end;
    const next = [];
    own.forEach((item) => {
      if (!fullyCovered || item.end <= start || item.start >= end) next.push(item);
      else {
        if (item.start < start) next.push({ start: item.start, end: start, type });
        if (item.end > end) next.push({ start: end, end: item.end, type });
      }
    });
    if (!fullyCovered) next.push({ start, end, type });
    const merged = normalizeStyleRanges([...others, ...next]);
    // A fill applied over another fill replaces it instead of stacking:
    // otherwise the renderer's own precedence, not the click the user just
    // made, would decide which of the two actually shows on the card.
    state.draft.styles = !fullyCovered && FILL_STYLE_TYPES.has(type)
      ? clearFillRanges(merged, start, end, type)
      : merged;
    return !fullyCovered;
  };

  const applyTextStyle = (type) => {
    const control = els.formatToolbar.querySelector(`button[data-style="${type}"]`);
    if (control?.getAttribute('aria-disabled') === 'true') {
      els.formattingState.textContent = control.dataset.blockedReason || `${STYLE_LABELS[type]} non disponibile`;
      return;
    }
    updateActiveFormat();
    const offsets = selectionOffsets();
    if (!offsets) {
      els.formattingState.textContent = 'Seleziona una porzione di testo';
      return;
    }
    // Commit the pending text edit before the treatment, so typing and
    // formatting stay two separate undo steps instead of collapsing into one.
    commitHistory();
    const applied = toggleStyleRange(type, offsets.start, offsets.end);
    // From here on an empty styles list means "user removed everything",
    // never "untouched" -- stop the renderer's own auto-signature fallback
    // from silently reapplying a default once the user has acted at all.
    state.draft.styles_customized = true;
    renderVisualEditor();
    restoreSelection(offsets.start, offsets.end);
    syncFillControl();
    commitHistory();
    els.formattingState.textContent = `${STYLE_LABELS[type]} ${applied ? 'applicato' : 'rimosso'}`;
    schedulePreview();
  };

  const selectionFill = () => {
    const offsets = selectionOffsets();
    return offsets ? fillTypeAt(state.draft?.styles || [], offsets.start, offsets.end) : null;
  };

  const syncFillControl = () => {
    if (!els.fillControl || !state.draft) return;
    const fill = selectionFill() || 'none';
    els.fillControl.dataset.fill = fill;
    els.fillControl.setAttribute('aria-label', `Riempimento del testo: ${FILL_LABELS[fill]}`);
    els.fillControl.title = `Riempimento del testo — ${FILL_LABELS[fill]}. `
      + 'Clic per il trattamento successivo; ⌘⇧A accento, ⌘⇧H evidenziato, ⌘⇧O contorno.';
  };

  const cycleFill = () => {
    const offsets = selectionOffsets();
    if (!offsets) {
      els.formattingState.textContent = 'Seleziona una porzione di testo';
      return;
    }
    const current = fillTypeAt(state.draft.styles, offsets.start, offsets.end);
    // Stepping off the last state removes the treatment rather than adding a
    // fourth one: the cycle always has a way back to plain text. Re-applying
    // the current type is exactly the toggle-off path applyTextStyle has.
    applyTextStyle(nextFillType(current) || current || FILL_CYCLE[0]);
  };

  // Line breaks are the one editorial decision the editor can genuinely help
  // with: balancing them by eye across a re-flow is tedious, and the measure
  // that matters is visual word length, not character count. The suggestion
  // is offered on demand and never applied behind the user's back -- one
  // press, undoable, and every newline they type afterwards stays put.
  const rebalanceLines = () => {
    const format = currentFormat();
    if (!format) return;
    updateActiveFormat();
    const text = normalize(state.draft.text);
    if (!text) {
      els.formattingState.textContent = 'Nessun testo da riequilibrare';
      return;
    }
    // The current count is a weak preference, not a constraint: a better
    // split with one row more or less is allowed to win.
    const preferred = format.lines.filter((line) => normalize(line)).length;
    const suggested = suggestBalancedLines(text, preferred || null);
    if (!suggested.length || JSON.stringify(suggested) === JSON.stringify(format.lines)) {
      els.formattingState.textContent = 'Gli a capo sono già equilibrati';
      return;
    }
    // Same words in the same order, so every style offset stays valid: only
    // the breaks move, and blank spacer rows are absorbed by the re-flow.
    const selection = selectionOffsets();
    commitHistory();
    state.draft.formats.forEach((item) => { item.lines = [...suggested]; });
    renderVisualEditor();
    if (selection) restoreSelection(selection.start, selection.end);
    syncFillControl();
    commitHistory();
    els.formattingState.textContent = `A capo riequilibrati su ${suggested.length} righe`;
    schedulePreview();
  };

  const updateActiveFormat = () => {
    const format = currentFormat();
    if (!format) return;
    const nextLines = editorLines();
    const nextText = normalize(nextLines.join(' '));
    const previousText = normalize(state.draft.text);
    // Lines (including manual breaks) are shared across every format --
    // what the user types is what every aspect ratio shows, unchanged.
    // Only the fitted font size differs per format.
    state.draft.formats.forEach((item) => { item.lines = [...nextLines]; });
    if (nextText && nextText !== previousText) {
      state.draft.text = nextText;
      if (state.draft.styles.length) {
        state.draft.styles = clampStyleRanges(
          remapStyleRanges(state.draft.styles, previousText, nextText),
          pointLength(nextText),
        );
        els.formattingState.textContent = state.draft.styles.length
          ? 'Formattazione conservata e riallineata al testo'
          : 'Formattazione rimossa perché il testo associato non esiste più';
      }
    }
    format.text_scale = Number((Number(els.scale.value) / 100).toFixed(2));
    format.vertical_position = $('#position-control .is-active')?.dataset.position || 'center';
  };

  const syncFormatControls = () => {
    const format = currentFormat();
    if (!format) return;
    renderVisualEditor();
    syncFillControl();
    const percent = Math.round(normalizeScale(format.text_scale) * 100);
    els.scale.value = String(percent);
    els.scaleValue.value = `${percent}%`;
    els.scaleValue.textContent = els.scaleValue.value;
    activate($('#position-control'), 'position', format.vertical_position);
  };

  const initialDraft = (manifest) => {
    const draft = {
      text: manifest.content.text,
      transformation: manifest.content.transformation,
      evidence_status: manifest.content.evidence_status,
      attribution: clone(manifest.content.attribution || { label: '', role: 'none' }),
      alt_text: manifest.content.alt_text || '',
      direction: manifest.direction,
      styles: initialStyles(manifest.content, manifest.direction),
      styles_customized: Boolean(manifest.content.styles_customized),
      presentation: normalizePresentation(manifest.presentation || {}, defaultOutputMode(manifest), manifest.direction),
      formats: normalizeFormats(manifest.formats),
    };
    sanitizeDirectionStyles(draft);
    return draft;
  };

  const loadSavedDraft = (manifest) => {
    try {
      const saved = JSON.parse(localStorage.getItem(storageKey) || 'null');
      if (saved?.revision === manifest.revision
        && saved?.baseline_signature === baselineSignature(manifest)
        && typeof saved.draft?.text === 'string'
        && saved.draft?.formats?.length === manifest.formats.length) {
        const initial = initialDraft(manifest);
        const restored = {
          ...initial,
          ...saved.draft,
          evidence_status: saved.draft.evidence_status || manifest.content.evidence_status,
          attribution: clone(saved.draft.attribution || manifest.content.attribution || { label: '', role: 'none' }),
          presentation: normalizePresentation(
            saved.draft.presentation || initial.presentation,
            defaultOutputMode(manifest),
            saved.draft.direction || initial.direction,
          ),
        };
        restored.formats = normalizeFormats(saved.draft.formats);
        sanitizeDirectionStyles(restored);
        return restored;
      }
    } catch (_) {
      localStorage.removeItem(storageKey);
    }
    return initialDraft(manifest);
  };

  const renderReadonlyModel = () => {
    const manifest = state.manifest;
    const content = manifest.content;
    els.transformation.textContent = TRANSFORMATION_LABELS[content.transformation] || content.transformation;
    els.evidence.textContent = EVIDENCE_LABELS[content.evidence_status] || content.evidence_status;
    els.revision.textContent = manifest.revision;
    els.session.textContent = 'Prova visuale pronta';
    els.dot.classList.remove('is-error');
  };

  const renderCardColors = () => {
    const brand = state.manifest?.brand || {};
    const colors = brand.colors || {};
    const orderedKeys = ['primary', 'accent', 'background', 'text'];
    const entries = orderedKeys.filter((key) => typeof colors[key] === 'string')
      .map((key) => ({ key, value: colors[key], ...CARD_COLOR_META[key] }));
    const brandName = normalize(brand.name) || 'Profilo della card';
    els.colorPaletteSubtitle.textContent = `${brandName} · colori applicati alla card`;
    els.colorPaletteHelp.textContent = 'Colori e asset protetti.';
    els.colors.setAttribute('aria-label', `Colori applicati alla card: ${brandName}`);
    els.palettePreview.innerHTML = entries.map(({ label, value }) => (
      `<span class="palette-preview-swatch" style="--swatch-color:${value}" title="${label}: ${value}"></span>`
    )).join('');
    els.colors.innerHTML = entries.map(({ label, value, usage }) => {
      const swatchStyle = ` style="--swatch-color:${value}"`;
      return `<div class="brand-color" role="listitem">
        <span class="brand-color-swatch"${swatchStyle} aria-hidden="true"></span>
        <span class="brand-color-copy"><strong>${label}</strong><small>${usage}</small></span>
        <code>${value}</code>
      </div>`;
    }).join('') || '<p class="palette-empty">Nessun colore disponibile nel profilo della card.</p>';
  };

  const setProfileFeedback = (message = '', isError = false) => {
    els.profileSaveFeedback.textContent = message;
    els.profileSaveFeedback.classList.toggle('is-error', isError);
    els.profileSaveFeedback.hidden = !message;
  };

  const activeProfile = () => state.profiles.find((profile) => profile.id === state.activeProfileId) || null;

  const renderProfileState = () => {
    const brandName = normalize(state.manifest?.brand?.name) || 'Profilo corrente';
    const saved = activeProfile();
    if (saved) {
      els.profileSaveState.textContent = saved.name;
      els.profileSaveToggle.textContent = 'Aggiorna';
      els.profileName.value = saved.name;
      els.profileExport.hidden = false;
      els.profileExport.disabled = false;
      return;
    }
    els.profileSaveState.textContent = state.profiles.length
      ? `${brandName} · ${state.profiles.length} ${state.profiles.length === 1 ? 'profilo salvato' : 'profili salvati'}`
      : `${brandName} · non salvato`;
    els.profileSaveToggle.textContent = 'Salva';
    els.profileExport.hidden = true;
    els.profileExport.disabled = true;
    if (!els.profileName.value) els.profileName.value = brandName;
  };

  const loadProfiles = async () => {
    try {
      const catalog = await api('/profiles');
      state.profiles = Array.isArray(catalog.profiles) ? catalog.profiles : [];
      state.activeProfileId = catalog.active_profile_id || null;
      els.profileSaveToggle.disabled = false;
      renderProfileState();
    } catch (error) {
      els.profileSaveState.textContent = 'Archivio non disponibile';
      els.profileSaveToggle.disabled = true;
      els.profileExport.hidden = true;
      els.profileExport.disabled = true;
      setProfileFeedback(error.message, true);
    }
  };

  const toggleProfileForm = (open) => {
    els.profileSaveForm.hidden = !open;
    els.profileSaveToggle.setAttribute('aria-expanded', String(open));
    if (open) {
      const saved = activeProfile();
      els.profileName.value = saved?.name || normalize(state.manifest?.brand?.name) || '';
      setProfileFeedback();
      els.profileName.focus();
    }
  };

  const saveCurrentProfile = async () => {
    const name = normalize(els.profileName.value);
    if (!name) {
      setProfileFeedback('Inserisci un nome per il profilo.', true);
      els.profileName.focus();
      return;
    }
    els.profileSaveConfirm.disabled = true;
    els.profileSaveConfirm.textContent = 'Salvo…';
    try {
      const result = await api('/profiles', { method: 'POST', body: JSON.stringify({ name }) });
      state.profiles = Array.isArray(result.profiles) ? result.profiles : [];
      state.activeProfileId = result.profile?.id || null;
      renderProfileState();
      toggleProfileForm(false);
      setProfileFeedback(`Profilo “${result.profile?.name || name}” disponibile per i prossimi lavori.`);
    } catch (error) {
      setProfileFeedback(error.message, true);
    } finally {
      els.profileSaveConfirm.disabled = false;
      els.profileSaveConfirm.textContent = 'Salva';
    }
  };

  const exportActiveProfile = async () => {
    const profile = activeProfile();
    if (!profile) {
      setProfileFeedback('Salva prima il profilo da esportare.', true);
      return;
    }
    els.profileExport.disabled = true;
    els.profileExport.textContent = 'Esporto…';
    try {
      const token = encodeURIComponent(params.get('token') || '');
      const profileId = encodeURIComponent(profile.id);
      const response = await fetch(`/api/profiles/export?profile_id=${profileId}&token=${token}`);
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.message || body.error || `Errore ${response.status}`);
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = profile.export_filename || 'quote-card-brand.json';
      document.body.append(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setProfileFeedback(`Profilo “${profile.name}” esportato in JSON.`);
    } catch (error) {
      setProfileFeedback(error.message, true);
    } finally {
      els.profileExport.disabled = false;
      els.profileExport.textContent = 'Esporta JSON';
    }
  };

  const renderAltTextState = () => {
    const custom = Boolean(els.altTextLabel.value.trim());
    els.altTextState.textContent = custom ? 'Personalizzato' : 'Alt text automatico ✓';
  };

  const renderFontSupport = () => {
    const support = state.manifest?.font_capabilities;
    const family = support?.family || state.manifest?.brand?.font?.family || 'font del brand';
    const unavailable = [];
    const simulated = [];
    ['bold', 'italic'].forEach((type) => {
      const capability = support?.styles?.[type];
      const control = els.formatToolbar.querySelector(`button[data-style="${type}"]`);
      if (!control) return;
      const available = capability?.available !== false;
      control.setAttribute('aria-disabled', String(!available));
      if (!available) {
        unavailable.push(STYLE_LABELS[type].toLowerCase());
        control.dataset.blockedReason = `${STYLE_LABELS[type]} non disponibile: manca il relativo file del font ${family}`;
        control.title = control.dataset.blockedReason;
      } else {
        delete control.dataset.blockedReason;
        if (capability && capability.exact === false) {
          simulated.push(STYLE_LABELS[type].toLowerCase());
          control.title = `${STYLE_LABELS[type]} con resa simulata: manca il file dedicato del font ${family}`;
        } else control.title = STYLE_LABELS[type];
      }
    });
    if (!unavailable.length && !simulated.length) {
      els.fontSupport.hidden = true;
      els.fontSupport.textContent = '';
      return;
    }
    const facts = [];
    if (unavailable.length) facts.push(`Non disponibile: ${unavailable.join(' e ')}`);
    if (simulated.length) facts.push(`Resa simulata: ${simulated.join(' e ')}`);
    els.fontSupport.textContent = `Font ${family} incompleto. ${facts.join('. ')}. Fornisci i file mancanti o approva un font sostitutivo.`;
    els.fontSupport.hidden = false;
  };

  const renderDeclarationState = (serverDeclaration = null) => {
    const transformation = serverDeclaration?.transformation || state.draft.transformation;
    const evidence = serverDeclaration?.evidence_status || state.draft.evidence_status;
    els.transformation.textContent = TRANSFORMATION_LABELS[transformation] || transformation;
    els.evidence.textContent = EVIDENCE_LABELS[evidence] || evidence;
    els.session.textContent = 'Responsabilità utente';
    els.textIntegrityHint.textContent = 'Tipo di formulazione e verifica nel riepilogo inferiore.';
    if (serverDeclaration?.alt_text_suggestion) els.altTextLabel.placeholder = serverDeclaration.alt_text_suggestion;
    renderAltTextState();
    syncActionButtons();
  };

  const SCORE_CATEGORY_LABELS = { contrast: 'Contrasto', fit: 'Adattamento', structure: 'Struttura' };

  const renderScore = (score = null) => {
    if (!score) {
      els.scoreTotal.textContent = '—';
      els.scoreBreakdown.textContent = '—';
      return;
    }
    els.scoreTotal.textContent = score.overall;
    els.scoreBreakdown.textContent = Object.entries(score.categories)
      .map(([key, value]) => `${SCORE_CATEGORY_LABELS[key] || key} ${value}`)
      .join(' · ');
  };

  const renderGraphicControl = () => {
    const control = $('#graphic-control');
    const help = $('#graphic-help');
    const direction = state.draft.direction;
    const config = GRAPHIC_VARIANTS[direction] || GRAPHIC_VARIANTS.editorial;
    const variant = normalizeGraphicVariant(direction, state.draft.presentation.graphic_variant);
    state.draft.presentation.graphic_variant = variant;
    state.graphicVariants[direction] = variant;
    ['default', 'alternate'].forEach((choice) => {
      const button = control.querySelector(`[data-graphic-choice="${choice}"]`);
      const option = config[choice];
      button.querySelector('.motif-label').textContent = option.label;
      button.querySelector('.motif-swatch').innerHTML = MOTIF_ICONS[option.icon];
      button.setAttribute('aria-label', `${config.style}: ${option.label}`);
    });
    const activeChoice = state.draft.presentation.graphic_mode === 'hidden'
      ? 'hidden'
      : variant === config.alternate.value ? 'alternate' : 'default';
    activate(control, 'graphicChoice', activeChoice);
    control.setAttribute('aria-label', `Motivo per ${config.style}`);
    help.textContent = `${config.style}: scegli il motivo oppure nascondilo.`;
  };

  const renderDraftControls = () => {
    const draft = state.draft;
    els.attributionLabel.value = draft.attribution?.label || '';
    els.altTextLabel.value = draft.alt_text || '';
    renderAltTextState();
    activate($('#logo-control'), 'logo', draft.presentation.logo_mode);
    renderGraphicControl();
    activate($('#output-control'), 'output', draft.presentation.output_mode || 'all');
    syncPreviewToSelectedOutput(false);
    $$('.directions button').forEach((button) => {
      const active = button.dataset.direction === draft.direction;
      button.classList.toggle('is-active', active);
      button.setAttribute('aria-pressed', String(active));
    });
    syncFormatControls();
    renderDeclarationState();
    storeDraft();
  };

  const initializeSession = (manifest, preserveFormat = true) => {
    const previousFormat = state.activeFormat;
    state.manifest = manifest;
    state.returnUrl = /^codex:\/\/threads\/[0-9a-f-]+$/i.test(manifest.return_url || '')
      ? manifest.return_url
      : '';
    renderCardColors();
    state.baseline = initialDraft(manifest);
    state.baseRevision = manifest.revision;
    state.draft = loadSavedDraft(manifest);
    state.graphicVariants[state.draft.direction] = state.draft.presentation.graphic_variant;
    state.activeFormat = preserveFormat && manifest.formats.some((item) => item.id === previousFormat)
      ? previousFormat
      : manifest.formats[0].id;
    $$('.format-tab').forEach((button) => {
      const available = manifest.formats.some((item) => item.id === button.dataset.format);
      button.disabled = !available;
      button.setAttribute('aria-disabled', String(!available));
    });
    renderReadonlyModel();
    renderFontSupport();
    setFormat(state.activeFormat, false);
    renderDraftControls();
    resetHistory();
  };

  const validateDraft = () => {
    updateActiveFormat();
    const errors = [];
    const sourceText = normalize(state.draft.text);
    state.draft.formats.forEach((format) => {
      if (!Array.isArray(format.lines) || format.lines.length < 1 || format.lines.length > 40 || !format.lines.some((line) => normalize(line))) {
        errors.push(`${format.id}: usa da 1 a 40 righe.`);
      } else if (!format.lines.every((line) => typeof line === 'string')) {
        errors.push(`${format.id}: ogni riga deve essere testuale.`);
      } else if (normalize(format.lines.join(' ')) !== sourceText) {
        errors.push(`${format.id}: gli a capo devono ricostruire esattamente il testo corrente.`);
      }
      if (format.text_scale < 0.80 || format.text_scale > 1.00) errors.push(`${format.id}: usa una scala compresa fra 80% e 100% del massimo sicuro.`);
    });
    const textLength = pointLength(state.draft.text);
    if (!Array.isArray(state.draft.styles) || state.draft.styles.length > 64 || state.draft.styles.some((style) => (
      !STYLE_TYPES.has(style.type) || !Number.isInteger(style.start) || !Number.isInteger(style.end)
      || style.start < 0 || style.start >= style.end || style.end > textLength
    ))) errors.push('La formattazione contiene una selezione non valida.');
    if (!['VERBATIM', 'EDITED', 'PARAPHRASE', 'AI_GENERATED'].includes(state.draft.transformation)) errors.push('Scegli un trattamento valido.');
    if (!['VERIFIED', 'USER_SUPPLIED', 'UNVERIFIED', 'CONFLICT'].includes(state.draft.evidence_status)) errors.push('Scegli uno stato della prova valido.');
    if (!['all', '4x5', '1x1', '9x16'].includes(state.draft.presentation?.output_mode)) errors.push('Scegli i formati del pacchetto finale.');
    if (normalizeGraphicVariant(state.draft.direction, state.draft.presentation?.graphic_variant) !== state.draft.presentation?.graphic_variant) {
      errors.push('Scegli un motivo disponibile per lo stile corrente.');
    }
    return errors;
  };

  const payload = () => {
    updateActiveFormat();
    return {
      base_revision: state.baseRevision,
      text: state.draft.text,
      transformation: state.draft.transformation,
      evidence_status: state.draft.evidence_status,
      attribution: clone(state.draft.attribution),
      alt_text: state.draft.alt_text || '',
      styles: clone(state.draft.styles),
      styles_customized: Boolean(state.draft.styles_customized),
      direction: state.draft.direction,
      emphasis: '',
      presentation: normalizePresentation(state.draft.presentation, defaultOutputMode(state.manifest), state.draft.direction),
      formats: clone(state.draft.formats),
    };
  };

  const clearGeneratedOutputs = () => {
    els.generatedOutput.replaceChildren();
    els.generatedOutput.hidden = true;
    state.renderedGenerationSignature = null;
  };

  const generationSignature = (outputs = []) => JSON.stringify(outputs.map((output) => ({
    kind: output.kind || '',
    format: output.format || '',
    filename: output.filename || '',
    url: output.url || '',
    absolute_path: output.absolute_path || '',
  })));

  const outputFolderLabel = (value = '') => {
    const parts = String(value).replace(/\\/g, '/').split('/').filter(Boolean);
    const folders = parts.slice(0, -1);
    if (!folders.length) return 'Download disponibile';
    const tail = folders.slice(-2).join(' / ');
    return `Cartella: ${folders.length > 2 ? `… / ${tail}` : tail}`;
  };

  const renderGeneratedOutputs = (outputs = []) => {
    clearGeneratedOutputs();
    if (!outputs.length) return;

    const head = document.createElement('div');
    head.className = 'generated-output-head';
    const heading = document.createElement('div');
    const title = document.createElement('strong');
    title.textContent = 'Output pronti';
    const count = document.createElement('span');
    count.textContent = `${outputs.length} file`;
    heading.append(title, count);
    const dismiss = document.createElement('button');
    dismiss.type = 'button';
    dismiss.className = 'generated-dismiss';
    dismiss.textContent = '×';
    dismiss.setAttribute('aria-label', 'Nascondi il riepilogo degli output');
    head.append(heading, dismiss);
    els.generatedOutput.append(head);

    outputs.forEach((output) => {
      const item = document.createElement('div');
      item.className = 'generated-output-item';
      const status = document.createElement('strong');
      status.className = 'generated-status';
      const formatLabel = { '4x5': '4:5', '1x1': '1:1', '9x16': '9:16' }[output.format] || output.format;
      status.textContent = output.kind === 'zip' ? 'Pacchetto pronto ✓' : `${formatLabel} pronto ✓`;

      const location = document.createElement('span');
      location.className = 'generated-location';
      const filename = document.createElement('code');
      filename.textContent = output.filename;
      filename.title = output.absolute_path || output.filename;
      const folder = document.createElement('span');
      folder.className = 'generated-folder';
      folder.textContent = outputFolderLabel(output.absolute_path || output.filename);
      location.append(filename, folder);

      const itemActions = document.createElement('span');
      itemActions.className = 'generated-item-actions';
      const copy = document.createElement('button');
      copy.type = 'button';
      copy.className = 'generated-copy';
      copy.textContent = 'Copia percorso';
      copy.dataset.copyPath = output.absolute_path || output.filename;
      copy.setAttribute('aria-label', `Copia il percorso di ${output.filename}`);

      const link = document.createElement('a');
      link.className = 'generated-link';
      link.href = output.url;
      link.download = output.filename;
      link.textContent = output.kind === 'zip' ? 'Scarica ZIP' : `Scarica ${formatLabel}`;
      link.title = `Scarica ${output.filename}`;
      link.setAttribute('aria-label', output.kind === 'zip' ? `Scarica il pacchetto ${output.filename}` : `Scarica il formato ${output.format}`);
      itemActions.append(copy, link);
      item.append(status, location, itemActions);
      els.generatedOutput.append(item);
    });
    state.renderedGenerationSignature = generationSignature(outputs);
    els.generatedOutput.hidden = false;
  };

  const renderWarnings = (warnings, qa = null) => {
    const items = Array.isArray(warnings) ? warnings : [];
    const passedChecks = !items.length && qa?.checks?.length ? qa.checks.length : 0;
    els.warningCount.textContent = items.length ? items.length : passedChecks;
    els.qaLabel.textContent = items.length
      ? `${items.length === 1 ? 'avviso da risolvere' : 'avvisi da risolvere'}`
      : passedChecks
        ? 'controlli superati'
        : 'vincoli locali validi';
    els.dot.classList.toggle('is-error', Boolean(items.length));

    els.warningList.replaceChildren();
    els.qaDetails.hidden = !items.length;
    els.warningState.textContent = items.length ? `${items.length} ${items.length === 1 ? 'intervento' : 'interventi'}` : '';
    items.forEach((warning, index) => {
      const source = typeof warning === 'string' ? { message: warning } : (warning || {});
      const formatMatch = String(source.message || '').match(/^(4x5|1x1|9x16):\s*/i);
      const format = source.format && source.format !== 'all' ? source.format : formatMatch?.[1] || '';
      const message = String(source.message || 'Controllo non superato.').replace(/^(4x5|1x1|9x16):\s*/i, '');
      const code = String(source.code || '').toLowerCase();
      const searchable = `${code} ${message}`.toLowerCase();
      let action = { target: '#visual-text-editor', label: 'Correggi testo', category: 'Testo' };
      if (/output|formati del pacchetto/.test(searchable)) action = { target: '#output-control', label: 'Scegli formato', category: 'Output' };
      else if (/decoration|motivo|graphic/.test(searchable)) action = { target: '#graphic-control', label: 'Cambia motivo', category: 'Motivo' };
      else if (/safe_area|attribuzione|attribution/.test(searchable)) action = { target: '#position-control', label: 'Cambia posizione', category: 'Spazi' };
      else if (/text_fit|text_outside|outline_too_small|scala|massimo sicuro/.test(searchable)) action = { target: '#scale', label: 'Regola scala', category: 'Ingombro' };
      else if (/contrast|contrasto/.test(searchable)) action = { target: '.directions', label: 'Cambia stile', category: 'Contrasto' };
      else if (/svg_|geometria svg|anteprima svg/.test(searchable)) action = { target: 'preview', label: 'Riprova', category: 'Anteprima' };

      const item = document.createElement('li');
      const copy = document.createElement('div');
      copy.className = 'warning-copy';
      const meta = document.createElement('strong');
      const formatLabel = { '4x5': '4:5', '1x1': '1:1', '9x16': '9:16' }[format] || 'Tutti i formati';
      meta.textContent = `${formatLabel} · ${action.category}`;
      const detail = document.createElement('span');
      detail.textContent = message;
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'warning-action';
      button.textContent = action.label;
      button.dataset.warningTarget = action.target;
      button.dataset.warningFormat = format;
      button.setAttribute('aria-label', `${action.label}: avviso ${index + 1}, ${formatLabel}`);
      copy.append(meta, detail);
      item.append(copy, button);
      els.warningList.append(item);
    });
  };

  const showActivePreview = () => {
    const preview = state.previews.get(state.activeFormat);
    if (!preview?.svg) {
      els.preview.replaceChildren();
      els.message.textContent = 'Nessuna anteprima restituita per questo formato.';
      els.scaleFitNote.hidden = true;
      els.scaleFitNote.textContent = '';
      return;
    }
    els.preview.innerHTML = preview.svg;
    els.message.textContent = state.safeArea ? 'Area tratteggiata: margine di sicurezza' : 'Margine di sicurezza nascosto';
    const percent = Math.round(normalizeScale(preview.text_scale) * 100);
    els.scaleFitNote.hidden = false;
    els.scaleFitNote.textContent = preview.auto_fitted
      ? 'La scala precedente è stata limitata al massimo sicuro per questo formato.'
      : percent < 100
        ? `Max-fit attivo: ${percent}% della dimensione massima sicura per questo formato.`
        : 'Max-fit attivo: dimensione massima entro guide e aree riservate.';
  };

  const applyPreview = (result) => {
    state.previews = new Map((result.previews || []).map((item) => [item.format, item]));
    state.qa = result.qa || null;
    showActivePreview();
    renderWarnings(result.warnings || [], result.qa || null);
    renderDeclarationState(result.declaration || null);
    renderScore(result.score || null);
  };

  const preview = async () => {
    if (!state.manifest || state.awaitingApply) return;
    const errors = validateDraft();
    if (errors.length) {
      renderWarnings(errors);
      const detail = errors[0];
      els.message.textContent = `Anteprima non aggiornata: ${detail}`;
      setMessage(detail, true);
      return;
    }
    storeDraft();
    state.qa = null;
    const call = ++state.requestId;
    els.stage.classList.add('is-loading');
    els.stage.setAttribute('aria-busy', 'true');
    try {
      const result = await api('/preview', { method: 'POST', body: JSON.stringify(payload()) });
      if (call === state.requestId) applyPreview(result);
    } catch (error) {
      if (call === state.requestId) {
        els.message.textContent = `Anteprima non aggiornata: ${error.message}`;
        setMessage('Controlla la composizione o la sessione: la bozza locale è conservata.', true);
      }
    } finally {
      if (call === state.requestId) {
        els.stage.classList.remove('is-loading');
        els.stage.setAttribute('aria-busy', 'false');
      }
    }
  };

  const schedulePreview = () => {
    clearTimeout(state.timer);
    if (state.generatePhase === 'completed') state.dismissedGenerationRevision = String(state.baseRevision);
    clearGeneratedOutputs();
    if (!state.submitting && !state.chatbotRequestId) setGenerateState('idle');
    updateActiveFormat();
    const attributionLabel = els.attributionLabel.value.trim();
    state.draft.attribution = {
      label: attributionLabel,
      role: attributionLabel ? 'author' : 'none',
    };
    state.draft.alt_text = els.altTextLabel.value.trim();
    renderDeclarationState();
    storeDraft();
    state.timer = setTimeout(preview, 360);
  };

  const setFormat = (format, collect = true) => {
    if (collect && state.draft) updateActiveFormat();
    state.activeFormat = format;
    els.shell.className = `preview-shell format-${format.replace('x', '-')}${state.safeArea ? '' : ' hide-safe-area'}`;
    $$('.format-tab').forEach((button) => {
      const active = button.dataset.format === format;
      button.classList.toggle('is-active', active);
      button.setAttribute('aria-pressed', String(active));
    });
    if (state.draft) syncFormatControls();
    showActivePreview();
    storeDraft();
  };

  const syncPreviewToSelectedOutput = (announce = false) => {
    const output = state.draft?.presentation?.output_mode;
    if (!output || output === 'all' || !state.draft.formats.some((item) => item.id === output)) return false;
    const changed = state.activeFormat !== output;
    if (changed) setFormat(output);
    if (changed && announce) {
      const label = { '4x5': '4:5', '1x1': '1:1', '9x16': '9:16' }[output] || output;
      setMessage(`Anteprima sincronizzata con l’output ${label}.`);
    }
    return changed;
  };

  const setZoom = (value) => {
    state.zoom = Math.max(70, Math.min(130, value));
    els.shell.style.setProperty('--preview-zoom', state.zoom / 100);
    els.zoom.value = `${state.zoom}%`;
    els.zoom.textContent = `${state.zoom}%`;
  };

  const watchChatbot = (chatbot) => {
    const requestId = chatbot?.request_id;
    if (!requestId || chatbot.status === 'unavailable' || chatbot.status === 'failed') {
      if (chatbot?.message) setMessage(chatbot.message, chatbot.status === 'failed');
      setButtonsDisabled(false);
      setGenerateState(chatbot?.status === 'failed' ? 'failed' : 'completed');
      return;
    }
    state.chatbotRequestId = requestId;
    setGenerateState('running');
    clearTimeout(state.chatbotPollTimer);
    const poll = async () => {
      try {
        const status = await api(`/agent-status?request_id=${encodeURIComponent(requestId)}`);
        if (status.status === 'completed') {
          setButtonsDisabled(false);
          setMessage(status.message || 'Chatbot completato: PNG pronti.');
          state.chatbotRequestId = null;
          setGenerateState('completed');
          return;
        }
        if (status.status === 'failed' || status.status === 'unavailable') {
          setButtonsDisabled(false);
          setMessage(status.message || 'Il chatbot non ha completato la generazione.', true);
          state.chatbotRequestId = null;
          setGenerateState(status.status === 'failed' ? 'failed' : 'completed');
          return;
        }
        setMessage('Chatbot in esecuzione: sta creando i PNG…');
        state.chatbotPollTimer = setTimeout(poll, 1200);
      } catch (error) {
        setMessage(`Stato chatbot non disponibile: ${error.message}`, true);
        setButtonsDisabled(false);
        state.chatbotRequestId = null;
        setGenerateState('failed');
      }
    };
    poll();
  };

  const returnToChat = () => {
    if (state.returnUrl) {
      setMessage('Output salvato. Torno alla chat…');
      window.location.assign(state.returnUrl);
      return;
    }
    setMessage('Output salvato. Provo a chiudere l’editor…');
    window.close();
    window.setTimeout(() => {
      if (document.visibilityState !== 'hidden') {
        setMessage('Output salvato. Chiudi questa scheda per tornare alla chat. Il percorso resta visibile qui sopra.');
      }
    }, 250);
  };

  const generate = async () => {
    if (state.submitting || state.awaitingApply) return;
    const errors = validateDraft();
    if (errors.length) {
      renderWarnings(errors);
      setMessage('Correggi gli avvisi prima di generare.', true);
      return;
    }
    storeDraft();
    state.submitting = true;
    setButtonsDisabled(true);
    setGenerateState('preparing');
    clearGeneratedOutputs();
    setMessage('Validazione e generazione degli output…');
    try {
      const checked = await api('/preview', { method: 'POST', body: JSON.stringify(payload()) });
      applyPreview(checked);
      if (checked.qa && !checked.qa.passed) {
        setButtonsDisabled(false);
        setMessage('Generazione bloccata: risolvi gli avvisi del quality gate.', true);
        return;
      }
      const submitted = await api('/generate', { method: 'POST', body: JSON.stringify(payload()) });
      if (submitted.applied) {
        state.awaitingApply = false;
        state.dismissedGenerationRevision = null;
        localStorage.removeItem(storageKey);
        initializeSession(await api('/session'));
        const outputs = submitted.generation?.outputs || [];
        renderGeneratedOutputs(outputs);
        const formats = outputs.map((output) => output.format).join(' · ');
        const chatbot = submitted.chatbot;
        if (chatbot?.status === 'running' || chatbot?.status === 'queued') {
          setButtonsDisabled(true);
          setMessage(formats ? `Output locali pronti (${formats}). Chatbot in esecuzione…` : 'Chatbot in esecuzione…');
          watchChatbot(chatbot);
        } else {
          setButtonsDisabled(false);
          setGenerateState('completed');
          setMessage(formats ? `Output pronti: ${formats}.` : 'Generazione completata.');
        }
        await preview();
      }
    } catch (error) {
      setButtonsDisabled(false);
      setGenerateState('failed');
      setMessage(`Generazione non riuscita: ${error.message}`, true);
    } finally {
      state.submitting = false;
      if (!state.chatbotRequestId && !els.generate.classList.contains('is-complete') && !els.generate.classList.contains('is-failed')) {
        setGenerateState('idle');
      }
    }
  };

  const refreshStatus = async () => {
    // A generate request already in flight is itself about to move
    // revision/feedback state forward; polling status in the middle of
    // that window previously read revision as changed out from under
    // baseRevision "unexpectedly" and locked the controls, racing the
    // request's own resync at its completion.
    if (!state.manifest || state.submitting) return;
    try {
      const status = await api('/status');
      const persistedOutputs = status.last_generation?.outputs || [];
      const persistedRevision = String(status.last_generation?.revision ?? '');
      const showPersistedGeneration = persistedOutputs.length
        && state.dismissedGenerationRevision !== persistedRevision;
      const persistedSignature = generationSignature(persistedOutputs);
      const hasNewPersistedGeneration = showPersistedGeneration
        && state.renderedGenerationSignature !== persistedSignature;
      if (hasNewPersistedGeneration) {
        renderGeneratedOutputs(persistedOutputs);
      }
      if (status.chatbot_generation?.status === 'running' || status.chatbot_generation?.status === 'queued') {
        state.chatbotRequestId = status.chatbot_generation.request_id;
        setButtonsDisabled(true);
        setGenerateState('running');
        watchChatbot(status.chatbot_generation);
      } else if (status.chatbot_generation?.status === 'completed' && hasNewPersistedGeneration) {
        setButtonsDisabled(false);
        setGenerateState('completed');
        setMessage(status.chatbot_generation.message || 'Chatbot completato: PNG pronti.');
      }
      if (status.feedback_pending) {
        els.session.textContent = 'Generazione in elaborazione';
        state.awaitingApply = true;
        setButtonsDisabled(true);
        return;
      }
      if (String(status.revision) !== String(state.baseRevision)) {
        if (state.awaitingApply) {
          localStorage.removeItem(storageKey);
          initializeSession(await api('/session'));
          state.awaitingApply = false;
          setButtonsDisabled(false);
          setMessage('Generazione completata: la prova usa la nuova revisione.');
          await preview();
        } else {
          setMessage('La revisione è cambiata sul server. Ripristina la sessione prima di generare.', true);
          setButtonsDisabled(true);
        }
        return;
      }
      if (state.awaitingApply && status.last_feedback_id && status.last_feedback_id === status.applied_feedback_id) {
        state.awaitingApply = false;
        localStorage.removeItem(storageKey);
        initializeSession(await api('/session'));
        setButtonsDisabled(false);
        setMessage('Generazione registrata. La prova resta pronta per la revisione.');
        await preview();
      }
    } catch (_) {
      // Preview and submission remain authoritative if the lightweight status check is temporarily unavailable.
    }
  };

  const clearResetRecovery = () => {
    clearTimeout(state.resetRecoveryTimer);
    state.resetRecoveryTimer = null;
    state.resetRecovery = null;
    els.reset.textContent = 'Ripristina';
    els.reset.setAttribute('aria-label', 'Ripristina la bozza');
    els.reset.title = 'Ripristina la bozza';
  };

  const armResetRecovery = (draft, activeFormat) => {
    clearTimeout(state.resetRecoveryTimer);
    state.resetRecovery = { draft, activeFormat };
    els.reset.textContent = 'Annulla ripristino';
    els.reset.setAttribute('aria-label', 'Annulla il ripristino della bozza');
    els.reset.title = 'Annulla il ripristino della bozza';
    state.resetRecoveryTimer = setTimeout(clearResetRecovery, 10000);
  };

  const restoreResetDraft = () => {
    const recovery = state.resetRecovery;
    if (!recovery) return false;
    clearResetRecovery();
    state.draft = clone(recovery.draft);
    state.activeFormat = recovery.activeFormat;
    clearGeneratedOutputs();
    setGenerateState('idle');
    setFormat(state.activeFormat, false);
    renderDraftControls();
    resetHistory();
    preview();
    setMessage('Ripristino annullato: la bozza precedente è di nuovo disponibile.');
    return true;
  };

  const resetDraft = () => {
    if (restoreResetDraft()) return;
    updateActiveFormat();
    state.draft.attribution = {
      label: els.attributionLabel.value.trim(),
      role: els.attributionLabel.value.trim() ? 'author' : 'none',
    };
    state.draft.alt_text = els.altTextLabel.value.trim();
    if (JSON.stringify(state.draft) === JSON.stringify(state.baseline)) {
      setMessage('La bozza coincide già con la revisione corrente.');
      return;
    }
    if (!window.confirm('Ripristinare la bozza? Le modifiche correnti verranno sostituite.')) return;
    const recoveryDraft = clone(state.draft);
    const recoveryFormat = state.activeFormat;
    state.draft = clone(state.baseline);
    localStorage.removeItem(storageKey);
    clearGeneratedOutputs();
    setGenerateState('idle');
    renderDraftControls();
    resetHistory();
    preview();
    armResetRecovery(recoveryDraft, recoveryFormat);
    setMessage('Bozza ripristinata. Puoi annullare dal pulsante per 10 secondi.');
  };

  const load = async () => {
    try {
      initializeSession(await api('/session'), false);
      setZoom(state.zoom);
      await Promise.all([preview(), refreshStatus(), loadProfiles()]);
    } catch (error) {
      els.session.textContent = 'Sessione non disponibile';
      els.dot.classList.add('is-error');
      els.preview.textContent = 'Non è stato possibile aprire la sessione.';
      els.message.textContent = error.message;
      setMessage('La sessione non è disponibile. Riprova quando il server è attivo.', true);
    }
  };

  $$('.format-tab').forEach((button) => button.addEventListener('click', () => {
    const format = button.dataset.format;
    if (state.draft.presentation.output_mode !== 'all') {
      state.draft.presentation.output_mode = format;
      activate($('#output-control'), 'output', format);
      setFormat(format);
      schedulePreview();
      const label = { '4x5': '4:5', '1x1': '1:1', '9x16': '9:16' }[format] || format;
      setMessage(`Anteprima e output impostati su ${label}.`);
      return;
    }
    setFormat(format);
    const label = { '4x5': '4:5', '1x1': '1:1', '9x16': '9:16' }[format] || format;
    setMessage(`Anteprima ${label}. Output: tutti i formati.`);
  }));
  $$('.directions button').forEach((button) => button.addEventListener('click', () => {
    state.graphicVariants[state.draft.direction] = normalizeGraphicVariant(
      state.draft.direction,
      state.draft.presentation.graphic_variant,
    );
    state.draft.direction = button.dataset.direction;
    state.draft.presentation.graphic_variant = normalizeGraphicVariant(
      state.draft.direction,
      state.graphicVariants[state.draft.direction] || 'default',
    );
    sanitizeDirectionStyles(state.draft);
    activate($('.directions'), 'direction', state.draft.direction);
    renderGraphicControl();
    schedulePreview();
  }));
  // Keep the caret where it is: a toolbar press must not steal the selection
  // the treatment is about to be applied to.
  els.formatToolbar.addEventListener('pointerdown', (event) => {
    if (event.target.closest('button')) event.preventDefault();
  });
  els.formatToolbar.addEventListener('click', (event) => {
    const button = event.target.closest('button');
    if (!button) return;
    if (button === els.fillControl) cycleFill();
    else if (button.dataset.style) applyTextStyle(button.dataset.style);
  });
  els.rebalance.addEventListener('pointerdown', (event) => event.preventDefault());
  els.rebalance.addEventListener('click', rebalanceLines);
  els.lines.addEventListener('input', () => {
    scheduleHistoryCommit();
    schedulePreview();
  });
  document.addEventListener('selectionchange', () => {
    if (document.activeElement === els.lines) syncFillControl();
  });
  els.lines.addEventListener('keydown', (event) => {
    const modifier = event.metaKey || event.ctrlKey;
    if (!modifier) return;
    const key = event.key.toLowerCase();
    if (key === 'z' || key === 'y') {
      event.preventDefault();
      restoreHistory(key === 'y' || event.shiftKey ? 1 : -1);
      return;
    }
    if (event.key === 'Enter') {
      event.preventDefault();
      rebalanceLines();
      return;
    }
    const style = event.shiftKey
      ? ({ h: 'highlight', a: 'accent', o: 'outline' })[key]
      : ({ b: 'bold', i: 'italic', u: 'underline' })[key];
    if (style) {
      event.preventDefault();
      applyTextStyle(style);
    }
  });
  els.lines.addEventListener('paste', (event) => {
    event.preventDefault();
    const text = event.clipboardData?.getData('text/plain') || '';
    const selection = window.getSelection();
    if (!selection || !selection.rangeCount) return;
    const range = selection.getRangeAt(0);
    range.deleteContents();
    const node = document.createTextNode(text);
    range.insertNode(node);
    range.setStartAfter(node);
    range.collapse(true);
    selection.removeAllRanges();
    selection.addRange(range);
    els.lines.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertFromPaste', data: text }));
  });
  [els.scale, els.attributionLabel, els.altTextLabel].forEach((input) => input.addEventListener('input', () => {
    if (input === els.scale) {
      const value = Number(input.value);
      els.scaleValue.value = `${value}%`;
      els.scaleValue.textContent = els.scaleValue.value;
    }
    if (input === els.altTextLabel) renderAltTextState();
    schedulePreview();
  }));
  [$('#position-control'), $('#logo-control'), $('#graphic-control'), $('#output-control')].forEach((group) => group.addEventListener('click', (event) => {
    const button = event.target.closest('button');
    if (!button) return;
    if (group.id === 'position-control') activate(group, 'position', button.dataset.position);
    else if (group.id === 'logo-control') {
      activate(group, 'logo', button.dataset.logo);
      state.draft.presentation.logo_mode = button.dataset.logo;
    } else if (group.id === 'graphic-control') {
      const config = GRAPHIC_VARIANTS[state.draft.direction] || GRAPHIC_VARIANTS.editorial;
      const choice = button.dataset.graphicChoice;
      if (choice === 'hidden') {
        state.draft.presentation.graphic_mode = 'hidden';
      } else {
        state.draft.presentation.graphic_mode = 'auto';
        state.draft.presentation.graphic_variant = config[choice].value;
        state.graphicVariants[state.draft.direction] = config[choice].value;
      }
      renderGraphicControl();
    } else {
      activate(group, 'output', button.dataset.output);
      state.draft.presentation.output_mode = button.dataset.output;
      syncPreviewToSelectedOutput(true);
    }
    schedulePreview();
  }));
  els.warningList.addEventListener('click', (event) => {
    const button = event.target.closest('.warning-action');
    if (!button) return;
    const format = button.dataset.warningFormat;
    if (format && state.draft.formats.some((item) => item.id === format)) setFormat(format);
    if (button.dataset.warningTarget === 'preview') {
      preview();
      setMessage('Nuovo controllo dell’anteprima in corso.');
      return;
    }
    const target = $(button.dataset.warningTarget);
    if (!target) return;
    target.scrollIntoView({ behavior: 'smooth', block: 'center' });
    const focusTarget = target.matches('button, input, textarea, select, [contenteditable="true"]')
      ? target
      : target.querySelector('.is-active, button, input, textarea, select, [contenteditable="true"]');
    focusTarget?.focus({ preventScroll: true });
    setMessage('Controllo aperto: applica la correzione indicata e ricontrolla l’anteprima.');
  });
  els.generatedOutput.addEventListener('click', async (event) => {
    const dismiss = event.target.closest('.generated-dismiss');
    if (dismiss) {
      state.dismissedGenerationRevision = String(state.baseRevision);
      clearGeneratedOutputs();
      setMessage('Riepilogo chiuso. Il pulsante principale torna alla chat.');
      return;
    }
    const copy = event.target.closest('.generated-copy');
    if (!copy) return;
    const path = copy.dataset.copyPath || '';
    try {
      if (navigator.clipboard?.writeText) await navigator.clipboard.writeText(path);
      else {
        const temporary = document.createElement('textarea');
        try {
          temporary.value = path;
          temporary.setAttribute('readonly', '');
          temporary.style.position = 'fixed';
          temporary.style.opacity = '0';
          document.body.append(temporary);
          temporary.select();
          if (!document.execCommand('copy')) throw new Error('Copia non disponibile');
        } finally {
          temporary.remove();
        }
      }
      copy.textContent = 'Copiato ✓';
      copy.setAttribute('aria-label', 'Percorso copiato');
      setMessage('Percorso copiato negli appunti.');
      window.setTimeout(() => {
        if (!copy.isConnected) return;
        copy.textContent = 'Copia percorso';
        copy.setAttribute('aria-label', `Copia il percorso di ${path.split(/[\\/]/).pop() || 'output'}`);
      }, 1800);
    } catch (_) {
      setMessage('Non riesco a copiare automaticamente il percorso. Usa il nome file mostrato nel riepilogo.', true);
    }
  });
  els.profileSaveToggle.addEventListener('click', () => toggleProfileForm(els.profileSaveForm.hidden));
  els.profileExport.addEventListener('click', exportActiveProfile);
  els.profileSaveCancel.addEventListener('click', () => toggleProfileForm(false));
  els.profileSaveForm.addEventListener('submit', (event) => {
    event.preventDefault();
    saveCurrentProfile();
  });
  $('#zoom-in').addEventListener('click', () => setZoom(state.zoom + 10));
  $('#zoom-out').addEventListener('click', () => setZoom(state.zoom - 10));
  els.cvdMode.addEventListener('change', () => {
    els.preview.style.filter = els.cvdMode.value === 'normal' ? '' : `url(#cvd-${els.cvdMode.value})`;
  });
  els.safeToggle.addEventListener('click', () => {
    state.safeArea = !state.safeArea;
    els.safeToggle.setAttribute('aria-pressed', String(state.safeArea));
    els.shell.classList.toggle('hide-safe-area', !state.safeArea);
    showActivePreview();
  });
  els.generate.addEventListener('click', () => {
    if (state.generatePhase === 'completed') returnToChat();
    else generate();
  });
  els.reset.addEventListener('click', resetDraft);
  els.backLink.addEventListener('click', (event) => {
    event.preventDefault();
    setMessage('Seleziona il testo per applicare grassetto, corsivo, sottolineatura o evidenziazione.');
    $('#editorial-fields').scrollIntoView({ behavior: 'smooth', block: 'start' });
  });

  setInterval(refreshStatus, 1500);
  load();
})();
