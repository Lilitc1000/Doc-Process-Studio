import { describe, expect, it } from 'vitest';
import {
  normalizeTimeOnly,
  parseDateToken,
  parseTimeToken,
  parseAffectedDateSummary,
  composeAffectedDateSummary,
  type AffectedDateParts,
} from '../../../src/utils/incident-report/date-normalization';

describe('normalizeTimeOnly', () => {
  it('parses HH:MM format', () => {
    expect(normalizeTimeOnly('14:30')).toBe('14:30');
  });

  it('returns empty for empty input', () => {
    expect(normalizeTimeOnly('')).toBe('');
  });

  it('returns formatted time for out-of-range hours', () => {
    expect(normalizeTimeOnly('25:00')).toBe('25:00');
  });
});

describe('parseDateToken', () => {
  it('parses ISO date format', () => {
    expect(parseDateToken('2026-04-15')).toBe('2026-04-15');
  });

  it('returns empty for invalid format', () => {
    expect(parseDateToken('15/04/2026')).toBe('');
  });

  it('returns empty for empty input', () => {
    expect(parseDateToken('')).toBe('');
  });
});

describe('parseTimeToken', () => {
  it('parses HH:MM format', () => {
    expect(parseTimeToken('09:00')).toBe('09:00');
  });

  it('returns empty for invalid format', () => {
    expect(parseTimeToken('9:00 am')).toBe('');
  });

  it('returns empty for empty input', () => {
    expect(parseTimeToken('')).toBe('');
  });
});

describe('parseAffectedDateSummary', () => {
  it('parses date range with times', () => {
    const result = parseAffectedDateSummary(
      '2026-04-15 | from: 09:00 | to: 15:30',
    );
    expect(result.date).toBe('2026-04-15');
    expect(result.from).toBe('09:00');
    expect(result.to).toBe('15:30');
  });

  it('returns empty parts for empty input', () => {
    const result = parseAffectedDateSummary('');
    expect(result).toEqual({ date: '', from: '', to: '' });
  });
});

describe('composeAffectedDateSummary', () => {
  it('composes full date range', () => {
    const parts: AffectedDateParts = {
      date: '2026-04-15',
      from: '09:00',
      to: '15:30',
    };
    expect(composeAffectedDateSummary(parts)).toBe(
      '2026-04-15 | from: 09:00 | to: 15:30',
    );
  });

  it('composes date with from only', () => {
    const parts: AffectedDateParts = {
      date: '2026-04-15',
      from: '09:00',
      to: '',
    };
    expect(composeAffectedDateSummary(parts)).toBe(
      '2026-04-15 | from: 09:00 | to: ',
    );
  });

  it('returns empty for empty parts', () => {
    const parts: AffectedDateParts = { date: '', from: '', to: '' };
    expect(composeAffectedDateSummary(parts)).toBe('');
  });
});
