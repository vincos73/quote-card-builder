(() => {
  'use strict';

  const $ = (selector) => document.querySelector(selector);
  const $$ = (selector) => [...document.querySelectorAll(selector)];
  const params = new URLSearchParams(location.search);
  const storageKey = `quote-card-editor:${params.get('token') || 'local'}`;
  const clone = (value) => JSON.parse(JSON.stringify(value));
  const normalize = (value) => String(value || '').trim().replace(/\s+/g, ' ');
  const normalizeScale = (value) => {
    const numeric = Number(value);
    return Math.min(1, Math.max(0.8, Number.isFinite(numeric) ? numeric : 1));
  };
  const normalizeFormats = (formats) => clone(formats || []).map((format) => ({
    ...format,
    text_scale: normalizeScale(format.text_scale),
  }));
  const STYLE_TYPES = new Set(['bold', 'italic', 'underline', 'highlight']);
  const TRANSFORMATION_LABELS = {
    VERBATIM: 'Letterale', EDITED: 'Modificata', PARAPHRASE: 'Parafrasi', AI_GENERATED: 'Generata',
  };
  const EVIDENCE_LABELS = {
    VERIFIED: 'Verificata', USER_SUPPLIED: 'Fornita dall’utente', UNVERIFIED: 'Non verificata', CONFLICT: 'In conflitto',
  };
  const STYLE_LABELS = {
    bold: 'Grassetto', italic: 'Corsivo', underline: 'Sottolineato', highlight: 'Evidenziato',
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
  };

  const els = {
    quote: $('#approved-quote'), attribution: $('#attribution'), source: $('#source'), brand: $('#brand'),
    transformation: $('#transformation'), evidence: $('#evidence-status'), note: $('#integrity-note'),
    revision: $('#revision'), session: $('#session-state'), dot: $('#status-dot'),
    lines: $('#visual-text-editor'), formatToolbar: $('#format-toolbar'), formattingState: $('#formatting-state'),
    fontSupport: $('#font-support-note'),
    scale: $('#scale'), scaleValue: $('#scale-value'), scaleFitNote: $('#scale-fit-note'),
    textIntegrityHint: $('#text-integrity-hint'),
    attributionLabel: $('#attribution-label'), attributionRole: $('#attribution-role'),
    quotes: $('#quotation-marks'), quotesRule: $('#quotes-rule'), preview: $('#preview-content'),
    shell: $('#preview-shell'), stage: $('#preview-stage'), message: $('#preview-message'),
    warningList: $('#warnings'), warningCount: $('#qa-count'), qaLabel: $('#qa-label'), draftState: $('#draft-state'),
    actionMessage: $('#action-message'), zoom: $('#zoom-output'), safeToggle: $('#safe-toggle'),
    backLink: $('#back-link'), returnText: $('#return-text'), feedback: $('#feedback'), approve: $('#approve'),
  };

  const api = async (path, options = {}) => {
    const response = await fetch(`/api${path}?token=${encodeURIComponent(params.get('token') || '')}`, {
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
    els.feedback.disabled = state.controlsLocked;
    els.approve.disabled = state.controlsLocked;
  };

  const setButtonsDisabled = (disabled) => {
    state.controlsLocked = disabled;
    syncActionButtons();
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
      localStorage.setItem(storageKey, JSON.stringify({ revision: state.baseRevision, draft: state.draft }));
      els.draftState.textContent = 'Bozza locale salvata';
    } catch (_) {
      els.draftState.textContent = 'Bozza in memoria';
    }
  };

  const balancedLines = (text, requested) => {
    const words = normalize(text).split(' ').filter(Boolean);
    const count = Math.max(1, Math.min(6, requested || 1, words.length));
    if (count === 1) return [words.join(' ')];
    const lines = [];
    let cursor = 0;
    for (let line = 0; line < count; line += 1) {
      const remainingWords = words.length - cursor;
      const remainingLines = count - line;
      const target = Math.max(1, Math.ceil(remainingWords / remainingLines));
      lines.push(words.slice(cursor, cursor + target).join(' '));
      cursor += target;
    }
    return lines.filter(Boolean);
  };

  const pointLength = (value) => Array.from(String(value || '')).length;

  const normalizeStyleRanges = (styles) => {
    const grouped = new Map();
    (Array.isArray(styles) ? styles : []).forEach((item) => {
      if (!item || !STYLE_TYPES.has(item.type) || !Number.isInteger(item.start) || !Number.isInteger(item.end) || item.start >= item.end) return;
      if (!grouped.has(item.type)) grouped.set(item.type, []);
      grouped.get(item.type).push({ start: item.start, end: item.end, type: item.type });
    });
    const merged = [];
    grouped.forEach((ranges, type) => {
      ranges.sort((first, second) => first.start - second.start || first.end - second.end);
      ranges.forEach((range) => {
        const previous = merged.at(-1);
        if (previous?.type === type && range.start <= previous.end) previous.end = Math.max(previous.end, range.end);
        else merged.push({ ...range });
      });
    });
    return merged.sort((first, second) => first.start - second.start || first.end - second.end || first.type.localeCompare(second.type));
  };

  const initialStyles = (content) => {
    const existing = normalizeStyleRanges(content.styles || []);
    if (existing.length || !content.emphasis) return existing;
    const index = content.text.indexOf(content.emphasis);
    if (index < 0) return [];
    const start = pointLength(content.text.slice(0, index));
    return [{ start, end: start + pointLength(content.emphasis), type: 'bold' }];
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
    const prefixRange = document.createRange();
    prefixRange.selectNodeContents(els.lines);
    prefixRange.setEnd(range.startContainer, range.startOffset);
    const prefix = prefixRange.toString();
    const selected = range.toString();
    let start = pointLength(normalize(prefix));
    if (start && /\s$/.test(prefix) && selected && !/^\s/.test(selected)) start += 1;
    const end = pointLength(normalize(prefix + selected));
    const limit = pointLength(state.draft.text);
    return start < end ? { start: Math.min(start, limit), end: Math.min(end, limit) } : null;
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
    state.draft.styles = normalizeStyleRanges([...others, ...next]);
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
    const applied = toggleStyleRange(type, offsets.start, offsets.end);
    renderVisualEditor();
    els.formattingState.textContent = `${STYLE_LABELS[type]} ${applied ? 'applicato' : 'rimosso'}`;
    schedulePreview();
  };

  const updateActiveFormat = () => {
    const format = currentFormat();
    if (!format) return;
    const nextLines = editorLines();
    const nextText = normalize(nextLines.join(' '));
    const previousText = normalize(state.draft.text);
    format.lines = nextLines;
    if (nextText && nextText !== previousText) {
      state.draft.text = nextText;
      state.draft.formats.forEach((item) => {
        if (item.id !== format.id) item.lines = balancedLines(nextText, item.lines.filter(Boolean).length);
      });
      if (state.draft.styles.length) {
        state.draft.styles = [];
        els.formattingState.textContent = 'Formattazione rimossa dopo la modifica delle parole';
      }
    }
    format.text_scale = Number((Number(els.scale.value) / 100).toFixed(2));
    format.vertical_position = $('#position-control .is-active')?.dataset.position || 'center';
  };

  const syncFormatControls = () => {
    const format = currentFormat();
    if (!format) return;
    renderVisualEditor();
    const percent = Math.round(normalizeScale(format.text_scale) * 100);
    els.scale.value = String(percent);
    els.scaleValue.value = `${percent}%`;
    els.scaleValue.textContent = els.scaleValue.value;
    activate($('#position-control'), 'position', format.vertical_position);
  };

  const initialDraft = (manifest) => ({
    text: manifest.content.text,
    transformation: manifest.content.transformation,
    evidence_status: manifest.content.evidence_status,
    attribution: clone(manifest.content.attribution || { label: '', role: 'none' }),
    use_quotation_marks: Boolean(manifest.content.use_quotation_marks),
    direction: manifest.direction,
    styles: initialStyles(manifest.content),
    presentation: {
      logo_mode: 'auto',
      show_quotation_marks: Boolean(manifest.content.use_quotation_marks),
      graphic_mode: 'auto',
      output_mode: 'all',
      ...clone(manifest.presentation || {}),
    },
    formats: normalizeFormats(manifest.formats),
  });

  const loadSavedDraft = (manifest) => {
    try {
      const saved = JSON.parse(localStorage.getItem(storageKey) || 'null');
      if (saved?.revision === manifest.revision && typeof saved.draft?.text === 'string' && saved.draft?.formats?.length === manifest.formats.length) {
        const initial = initialDraft(manifest);
        const restored = {
          ...initial,
          ...saved.draft,
          evidence_status: saved.draft.evidence_status || manifest.content.evidence_status,
          attribution: clone(saved.draft.attribution || manifest.content.attribution || { label: '', role: 'none' }),
          presentation: {
            ...initial.presentation,
            ...clone(saved.draft.presentation || {}),
          },
          use_quotation_marks: typeof saved.draft.use_quotation_marks === 'boolean'
            ? saved.draft.use_quotation_marks
            : Boolean(saved.draft.presentation?.show_quotation_marks),
        };
        restored.formats = normalizeFormats(saved.draft.formats);
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
    els.quote.textContent = content.text;
    els.attribution.textContent = content.attribution?.label || 'Nessuna attribuzione';
    els.source.textContent = manifest.source?.title || manifest.source?.label || manifest.source?.locator || 'Fonte non disponibile';
    els.brand.textContent = manifest.brand?.name || 'Profilo non risolto';
    els.transformation.textContent = TRANSFORMATION_LABELS[content.transformation] || content.transformation;
    els.evidence.textContent = EVIDENCE_LABELS[content.evidence_status] || content.evidence_status;
    els.note.textContent = 'La provenienza osservata resta visibile; testo, attribuzione e dichiarazioni sono modificabili.';
    els.revision.textContent = manifest.revision;
    els.session.textContent = 'Prova visuale pronta';
    els.dot.classList.remove('is-error');
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
    els.textIntegrityHint.textContent = 'Tipo di formulazione e verifica restano nel riepilogo inferiore.';
    syncActionButtons();
  };

  const renderDraftControls = () => {
    const draft = state.draft;
    els.quotes.checked = Boolean(draft.use_quotation_marks);
    els.quotes.disabled = false;
    els.quotesRule.textContent = 'Segno distintivo di ED';
    els.quotes.closest('.check-row').classList.remove('is-locked');
    els.quotes.closest('.quotes-section').hidden = draft.direction !== 'editorial';
    els.attributionLabel.value = draft.attribution?.label || '';
    els.attributionRole.value = draft.attribution?.role || 'none';
    activate($('#logo-control'), 'logo', draft.presentation.logo_mode);
    activate($('#graphic-control'), 'graphic', draft.presentation.graphic_mode || 'auto');
    activate($('#output-control'), 'output', draft.presentation.output_mode || 'all');
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
    state.baseline = initialDraft(manifest);
    state.baseRevision = manifest.revision;
    state.draft = loadSavedDraft(manifest);
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
  };

  const validateDraft = () => {
    updateActiveFormat();
    const errors = [];
    const sourceText = normalize(state.draft.text);
    state.draft.formats.forEach((format) => {
      if (!Array.isArray(format.lines) || format.lines.length < 1 || format.lines.length > 6 || !format.lines.some((line) => normalize(line))) {
        errors.push(`${format.id}: usa da 1 a 6 righe.`);
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
    if (!['speaker', 'author', 'publisher', 'none'].includes(state.draft.attribution?.role)) errors.push('Scegli un ruolo di attribuzione valido.');
    if (state.draft.attribution?.role !== 'none' && !normalize(state.draft.attribution?.label)) errors.push('Inserisci l’attribuzione per il ruolo scelto.');
    if (!['all', '4x5', '1x1', '9x16'].includes(state.draft.presentation?.output_mode)) errors.push('Scegli i formati del pacchetto finale.');
    return errors;
  };

  const payload = (action) => {
    updateActiveFormat();
    const value = {
      base_revision: state.baseRevision,
      text: state.draft.text,
      transformation: state.draft.transformation,
      evidence_status: state.draft.evidence_status,
      attribution: clone(state.draft.attribution),
      use_quotation_marks: state.draft.use_quotation_marks,
      styles: clone(state.draft.styles),
      direction: state.draft.direction,
      emphasis: '',
      presentation: clone(state.draft.presentation),
      formats: clone(state.draft.formats),
    };
    if (action) {
      value.action = action;
      value.overall_note = '';
    }
    return value;
  };

  const renderWarnings = (warnings, qa = null) => {
    const passedChecks = !warnings.length && qa?.checks?.length ? qa.checks.length : 0;
    els.warningCount.textContent = warnings.length ? warnings.length : passedChecks;
    els.qaLabel.textContent = warnings.length
      ? `${warnings.length === 1 ? 'avviso da risolvere' : 'avvisi da risolvere'}`
      : passedChecks
        ? 'controlli superati'
        : 'vincoli locali validi';
    els.dot.classList.toggle('is-error', Boolean(warnings.length));
    els.warningList.replaceChildren();
    if (!warnings.length) {
      const item = document.createElement('li');
      item.className = 'empty-warning';
      item.textContent = qa?.checks?.length
        ? `${qa.checks.length} controlli superati: struttura, contrasto, fitting, area sicura, SVG e asset.`
        : 'Validazione dei vincoli superata; QA visuale in aggiornamento.';
      els.warningList.append(item);
      return;
    }
    warnings.forEach((warning) => {
      const item = document.createElement('li');
      item.textContent = typeof warning === 'string' ? warning : warning.message || warning.code || 'Avviso di qualità';
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
  };

  const preview = async () => {
    if (!state.manifest || state.awaitingApply) return;
    const errors = validateDraft();
    if (errors.length) {
      renderWarnings(errors);
      els.message.textContent = 'Correggi la composizione per aggiornare la prova.';
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
    updateActiveFormat();
    state.draft.use_quotation_marks = els.quotes.checked;
    state.draft.presentation.show_quotation_marks = els.quotes.checked;
    state.draft.attribution = {
      label: els.attributionLabel.value.trim(),
      role: els.attributionRole.value,
    };
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

  const setZoom = (value) => {
    state.zoom = Math.max(70, Math.min(130, value));
    els.shell.style.setProperty('--preview-zoom', state.zoom / 100);
    els.zoom.value = `${state.zoom}%`;
    els.zoom.textContent = `${state.zoom}%`;
  };

  const submit = async (action) => {
    if (state.submitting || state.awaitingApply) return;
    const errors = validateDraft();
    if (errors.length) {
      renderWarnings(errors);
      setMessage('Correggi gli avvisi prima di inviare.', true);
      return;
    }
    storeDraft();
    state.submitting = true;
    setButtonsDisabled(true);
    setMessage(action === 'approve' ? 'Invio della richiesta di approvazione…' : 'Invio delle modifiche…');
    try {
      const checked = await api('/preview', { method: 'POST', body: JSON.stringify(payload()) });
      applyPreview(checked);
      if (action === 'approve' && checked.qa && !checked.qa.passed) {
        setButtonsDisabled(false);
        setMessage('Approvazione bloccata: risolvi gli avvisi del quality gate.', true);
        return;
      }
      const submitted = await api('/submit', { method: 'POST', body: JSON.stringify(payload(action)) });
      if (submitted.applied) {
        state.awaitingApply = false;
        localStorage.removeItem(storageKey);
        initializeSession(await api('/session'));
        setButtonsDisabled(false);
        setMessage(action === 'approve'
          ? 'Richiesta di approvazione registrata. La prova resta disponibile per il controllo finale.'
          : 'Modifiche applicate. La prova usa già la nuova revisione.');
        await preview();
      } else {
        state.awaitingApply = true;
        els.session.textContent = action === 'approve' ? 'Approvazione in registrazione' : 'Feedback in elaborazione';
        setMessage(action === 'approve'
          ? 'Richiesta inviata. La sessione attende la registrazione dell’approvazione.'
          : 'Modifiche inviate. La prova si aggiornerà dopo l’applicazione atomica.');
      }
    } catch (error) {
      setButtonsDisabled(false);
      setMessage(`Invio non riuscito: ${error.message}`, true);
    } finally {
      state.submitting = false;
    }
  };

  const refreshStatus = async () => {
    if (!state.manifest) return;
    try {
      const status = await api('/status');
      if (status.feedback_pending) {
        els.session.textContent = 'Feedback in elaborazione';
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
          setMessage('Modifiche applicate: la prova usa la nuova revisione.');
          await preview();
        } else {
          setMessage('La revisione è cambiata sul server. Ripristina la sessione prima di inviare.', true);
          setButtonsDisabled(true);
        }
        return;
      }
      if (state.awaitingApply && status.last_feedback_id && status.last_feedback_id === status.applied_feedback_id) {
        state.awaitingApply = false;
        localStorage.removeItem(storageKey);
        initializeSession(await api('/session'));
        setButtonsDisabled(false);
        setMessage('Richiesta registrata. La prova resta pronta per la revisione.');
        await preview();
      }
    } catch (_) {
      // Preview and submission remain authoritative if the lightweight status check is temporarily unavailable.
    }
  };

  const resetDraft = () => {
    state.draft = clone(state.baseline);
    localStorage.removeItem(storageKey);
    renderDraftControls();
    preview();
    setMessage('Bozza ripristinata dalla revisione corrente.');
  };

  const load = async () => {
    try {
      initializeSession(await api('/session'), false);
      setZoom(state.zoom);
      await Promise.all([preview(), refreshStatus()]);
    } catch (error) {
      els.session.textContent = 'Sessione non disponibile';
      els.dot.classList.add('is-error');
      els.preview.textContent = 'Non è stato possibile aprire la sessione.';
      els.message.textContent = error.message;
      setMessage('La sessione non è disponibile. Riprova quando il server è attivo.', true);
    }
  };

  $$('.format-tab').forEach((button) => button.addEventListener('click', () => setFormat(button.dataset.format)));
  $$('.directions button').forEach((button) => button.addEventListener('click', () => {
    state.draft.direction = button.dataset.direction;
    activate($('.directions'), 'direction', state.draft.direction);
    els.quotes.closest('.quotes-section').hidden = state.draft.direction !== 'editorial';
    schedulePreview();
  }));
  els.formatToolbar.addEventListener('pointerdown', (event) => {
    if (event.target.closest('button[data-style]')) event.preventDefault();
  });
  els.formatToolbar.addEventListener('click', (event) => {
    const button = event.target.closest('button[data-style]');
    if (button) applyTextStyle(button.dataset.style);
  });
  els.lines.addEventListener('input', schedulePreview);
  els.lines.addEventListener('keydown', (event) => {
    const modifier = event.metaKey || event.ctrlKey;
    const style = modifier && !event.shiftKey && ['b', 'i', 'u'].includes(event.key.toLowerCase())
      ? ({ b: 'bold', i: 'italic', u: 'underline' })[event.key.toLowerCase()]
      : modifier && event.shiftKey && event.key.toLowerCase() === 'h' ? 'highlight' : null;
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
  [els.scale, els.quotes, els.attributionLabel, els.attributionRole].forEach((input) => input.addEventListener('input', () => {
    if (input === els.scale) {
      const value = Number(input.value);
      els.scaleValue.value = `${value}%`;
      els.scaleValue.textContent = els.scaleValue.value;
    }
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
      activate(group, 'graphic', button.dataset.graphic);
      state.draft.presentation.graphic_mode = button.dataset.graphic;
    } else {
      activate(group, 'output', button.dataset.output);
      state.draft.presentation.output_mode = button.dataset.output;
    }
    schedulePreview();
  }));
  $('#zoom-in').addEventListener('click', () => setZoom(state.zoom + 10));
  $('#zoom-out').addEventListener('click', () => setZoom(state.zoom - 10));
  els.safeToggle.addEventListener('click', () => {
    state.safeArea = !state.safeArea;
    els.safeToggle.setAttribute('aria-pressed', String(state.safeArea));
    els.shell.classList.toggle('hide-safe-area', !state.safeArea);
    showActivePreview();
  });
  els.feedback.addEventListener('click', () => submit('feedback'));
  els.approve.addEventListener('click', () => submit('approve'));
  $('#reset').addEventListener('click', resetDraft);
  els.backLink.addEventListener('click', (event) => {
    event.preventDefault();
    setMessage('Seleziona il testo per applicare grassetto, corsivo, sottolineatura o evidenziazione.');
    $('#editorial-fields').scrollIntoView({ behavior: 'smooth', block: 'start' });
  });

  setInterval(refreshStatus, 1500);
  load();
})();
