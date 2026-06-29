import { describe, expect, it } from 'vitest';
import {
  extractModelNames,
  normalizeSkillCatalog,
} from '@shared/utils/catalog';

describe('extractModelNames', () => {
  it('extracts model names from models array', () => {
    expect(
      extractModelNames({
        models: [{ name: 'qwen3:8b' }, { name: 'llama3:70b' }],
      }),
    ).toEqual(['qwen3:8b', 'llama3:70b']);
  });

  it('extracts model names from data array', () => {
    expect(
      extractModelNames({
        data: [{ model: 'qwen3:8b' }, { id: 'llama3:70b' }],
      }),
    ).toEqual(['qwen3:8b', 'llama3:70b']);
  });

  it('returns empty for empty payload', () => {
    expect(extractModelNames({})).toEqual([]);
  });
});

describe('normalizeSkillCatalog', () => {
  it('normalizes skill catalog with display names', () => {
    const payload = {
      skills: [
        {
          id: 'incident-report',
          displayName: 'Incident Report',
          shortDescription: 'Create incident reports',
          skillType: 'chat',
        },
        {
          id: 'workspace-skill',
          displayName: 'Workspace',
          shortDescription: 'WS',
          skillType: 'workspace',
        },
      ],
    };
    const result = normalizeSkillCatalog(payload);
    expect(result).toHaveLength(2);
    expect(result[0].id).toBe('incident-report');
    expect(result[0].displayName).toBe('Incident Report');
  });

  it('returns empty for empty skills', () => {
    expect(normalizeSkillCatalog({ skills: [] })).toEqual([]);
  });
});
