export interface AffectedDateParts {
  date: string;
  from: string;
  to: string;
}

export interface TimelineItem {
  time: string;
  event: string;
  resolution: string;
  evidence: string;
}

export const parseDateToken = (value: string) => {
  const trimmed = value.trim();
  if (!trimmed) {
    return '';
  }
  const match = trimmed.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!match) {
    return '';
  }
  return trimmed;
};

export const parseTimeToken = (value: string) => {
  const trimmed = value.trim();
  if (!trimmed) {
    return '';
  }
  const match = trimmed.match(/^(\d{2}):(\d{2})(?::(\d{2}))?$/);
  if (!match) {
    return '';
  }
  return trimmed;
};

export const normalizeTimeOnly = (value: string) => {
  const trimmed = value.trim();
  if (!trimmed) {
    return '';
  }
  const match = trimmed.match(/^(\d{2}):(\d{2})(?::(\d{2}))?$/);
  if (!match) {
    return '';
  }
  return `${match[1]}:${match[2]}`;
};

export const parseAffectedDateSummary = (value: string): AffectedDateParts => {
  const trimmed = value.trim();
  if (!trimmed) {
    return { date: '', from: '', to: '' };
  }
  const match = trimmed.match(
    /^([^|]+)\s*\|\s*from:\s*([^|]*)\s*\|\s*to:\s*([^|]*)$/i,
  );
  if (!match) {
    return { date: '', from: '', to: '' };
  }
  return {
    date: parseDateToken(match[1]),
    from: parseTimeToken(match[2]),
    to: parseTimeToken(match[3]),
  };
};

export const composeAffectedDateSummary = (parts: AffectedDateParts) => {
  const date = parseDateToken(parts.date);
  const from = parseTimeToken(parts.from);
  const to = parseTimeToken(parts.to);
  if (!date && !from && !to) {
    return '';
  }
  return `${date || ''} | from: ${from || ''} | to: ${to || ''}`;
};
