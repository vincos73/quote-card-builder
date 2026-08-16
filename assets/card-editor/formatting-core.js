(function exposeFormattingCore(root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.QcbFormatting = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, () => {
  'use strict';

  const STYLE_TYPES = new Set(['bold', 'italic', 'underline', 'highlight', 'accent']);
  const pointLength = (value) => Array.from(String(value || '')).length;
  const normalizeText = (value) => String(value || '').trim().replace(/\s+/g, ' ');

  const normalizeStyleRanges = (styles) => {
    const grouped = new Map();
    (Array.isArray(styles) ? styles : []).forEach((item) => {
      if (!item || !STYLE_TYPES.has(item.type) || !Number.isInteger(item.start)
        || !Number.isInteger(item.end) || item.start >= item.end) return;
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

  const commonChange = (before, after) => {
    const previous = Array.from(String(before || ''));
    const next = Array.from(String(after || ''));
    let start = 0;
    while (start < previous.length && start < next.length && previous[start] === next[start]) start += 1;
    let suffix = 0;
    while (
      suffix < previous.length - start
      && suffix < next.length - start
      && previous[previous.length - 1 - suffix] === next[next.length - 1 - suffix]
    ) suffix += 1;
    return { oldStart: start, oldEnd: previous.length - suffix, newEnd: next.length - suffix };
  };

  const remapStyleRanges = (styles, before, after) => {
    const normalized = normalizeStyleRanges(styles);
    if (!normalized.length || before === after) return normalized;
    const change = commonChange(before, after);
    const inserted = change.oldStart === change.oldEnd;
    const delta = change.newEnd - change.oldEnd;
    const mapped = normalized.map((style) => {
      if (inserted) {
        if (style.end <= change.oldStart) return { ...style };
        if (style.start >= change.oldStart) {
          return { ...style, start: style.start + delta, end: style.end + delta };
        }
        return { ...style, end: style.end + delta };
      }
      const mapStart = (position) => {
        if (position <= change.oldStart) return position;
        if (position >= change.oldEnd) return position + delta;
        return change.oldStart;
      };
      const mapEnd = (position) => {
        if (position <= change.oldStart) return position;
        if (position >= change.oldEnd) return position + delta;
        return change.newEnd;
      };
      return { ...style, start: mapStart(style.start), end: mapEnd(style.end) };
    }).filter((style) => style.start < style.end);
    return normalizeStyleRanges(mapped);
  };

  const clampStyleRanges = (styles, textLength) => {
    const limit = Math.max(0, Number.isInteger(textLength) ? textLength : 0);
    return normalizeStyleRanges((Array.isArray(styles) ? styles : []).map((style) => ({
      ...style,
      start: Math.max(0, Math.min(limit, style.start)),
      end: Math.max(0, Math.min(limit, style.end)),
    })).filter((style) => style.start < style.end));
  };

  const canonicalLineStart = (lines, lineIndex) => {
    let offset = 0;
    let hasText = false;
    (Array.isArray(lines) ? lines : []).slice(0, Math.max(0, lineIndex)).forEach((line) => {
      const value = normalizeText(line);
      if (!value) return;
      if (hasText) offset += 1;
      offset += pointLength(value);
      hasText = true;
    });
    const current = normalizeText((lines || [])[lineIndex] || '');
    return offset + (hasText && current ? 1 : 0);
  };

  const suggestBalancedLines = (text, preferredCount = null) => {
    const words = normalizeText(text).split(' ').filter(Boolean);
    if (words.length < 2) return words;

    const maxLines = Math.min(6, words.length);
    const wordUnits = words.map((word) => pointLength(word));
    const prefix = [0];
    wordUnits.forEach((units) => prefix.push(prefix.at(-1) + units));
    const totalUnits = prefix.at(-1) + words.length - 1;
    const idealCount = Math.max(1, Math.min(maxLines, Math.round(totalUnits / 22)));
    let best = null;

    for (let lineCount = 1; lineCount <= maxLines; lineCount += 1) {
      if (lineCount > 1 && words.length < lineCount * 2) continue;
      const targetUnits = totalUnits / lineCount;
      const score = Array.from({ length: lineCount + 1 }, () => Array(words.length + 1).fill(Infinity));
      const breaks = Array.from({ length: lineCount + 1 }, () => Array(words.length + 1).fill(-1));
      score[0][0] = 0;

      for (let row = 1; row <= lineCount; row += 1) {
        for (let end = row; end <= words.length; end += 1) {
          for (let start = row - 1; start < end; start += 1) {
            if (!Number.isFinite(score[row - 1][start])) continue;
            const wordCount = end - start;
            const units = prefix[end] - prefix[start] + wordCount - 1;
            const imbalance = ((units - targetUnits) / Math.max(targetUnits, 1)) ** 2;
            const isolatedWord = lineCount > 1 && wordCount === 1 ? 24 : 0;
            const terminalOrphan = row === lineCount && wordCount === 1 ? 36 : 0;
            const candidate = score[row - 1][start] + imbalance + isolatedWord + terminalOrphan;
            if (candidate < score[row][end]) {
              score[row][end] = candidate;
              breaks[row][end] = start;
            }
          }
        }
      }

      if (!Number.isFinite(score[lineCount][words.length])) continue;
      const lines = [];
      let row = lineCount;
      let end = words.length;
      while (row > 0) {
        const start = breaks[row][end];
        lines.unshift(words.slice(start, end).join(' '));
        end = start;
        row -= 1;
      }
      const preference = Number.isFinite(preferredCount) ? Math.abs(lineCount - preferredCount) * 0.05 : 0;
      const candidate = score[lineCount][words.length] + ((lineCount - idealCount) ** 2) * 3 + preference;
      if (!best || candidate < best.score) best = { score: candidate, lines };
    }
    return best?.lines || [words.join(' ')];
  };

  return {
    STYLE_TYPES,
    canonicalLineStart,
    clampStyleRanges,
    normalizeStyleRanges,
    normalizeText,
    pointLength,
    remapStyleRanges,
    suggestBalancedLines,
  };
});
