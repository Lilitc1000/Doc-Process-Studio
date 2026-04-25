import { describe, expect, it } from 'vitest';
import {
  normalizeStatusOption,
  normalizeSeverityOption,
  STATUS_OPTION_FOLLOW_UP_ACTION_REQUIRED,
  STATUS_OPTION_CLOSED,
  SEVERITY_OPTION_MINOR,
  SEVERITY_OPTION_MAJOR,
  SEVERITY_OPTION_CRITICAL,
} from '../../../src/utils/incident-report/constants';

describe('normalizeStatusOption', () => {
  it('returns input for empty input', () => {
    expect(normalizeStatusOption('')).toBe('');
  });

  it('returns correct option for exact match', () => {
    expect(normalizeStatusOption('follow_up_action_required')).toBe(
      STATUS_OPTION_FOLLOW_UP_ACTION_REQUIRED,
    );
    expect(normalizeStatusOption('closed')).toBe(STATUS_OPTION_CLOSED);
  });

  it('matches Chinese keywords', () => {
    expect(normalizeStatusOption('跟进中')).toBe(
      STATUS_OPTION_FOLLOW_UP_ACTION_REQUIRED,
    );
    expect(normalizeStatusOption('已关闭')).toBe(STATUS_OPTION_CLOSED);
  });
});

describe('normalizeSeverityOption', () => {
  it('returns input for empty input', () => {
    expect(normalizeSeverityOption('')).toBe('');
  });

  it('returns correct option for exact match', () => {
    expect(normalizeSeverityOption('minor')).toBe(SEVERITY_OPTION_MINOR);
    expect(normalizeSeverityOption('major')).toBe(SEVERITY_OPTION_MAJOR);
    expect(normalizeSeverityOption('critical')).toBe(SEVERITY_OPTION_CRITICAL);
  });

  it('matches Chinese keywords', () => {
    expect(normalizeSeverityOption('一般')).toBe(SEVERITY_OPTION_MINOR);
    expect(normalizeSeverityOption('严重')).toBe(SEVERITY_OPTION_MAJOR);
    expect(normalizeSeverityOption('致命')).toBe(SEVERITY_OPTION_CRITICAL);
  });
});
