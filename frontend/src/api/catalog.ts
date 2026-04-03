import type { SkillCatalogPayload, SkillOption } from '../types/skill';
import type { ModelCatalogPayload, RemoteModelRecord } from '../utils/catalog';
import { extractModelNames, normalizeSkillCatalog } from '../utils/catalog';
import { apiClient } from './client';

export const fallbackModels = [
  'gpt-4o-mini',
  'gpt-4o',
  'claude-3.5-sonnet',
  'deepseek-v3',
];

export const fetchAvailableModels = async () => {
  const response = await apiClient.get<
    ModelCatalogPayload & {
      models?: RemoteModelRecord[];
    }
  >('/models');

  return extractModelNames(response.data);
};

export const fetchAvailableSkills = async (): Promise<{
  skills: SkillOption[];
  defaultSkillId: string;
}> => {
  const response = await apiClient.get<SkillCatalogPayload>('/skills');
  return normalizeSkillCatalog(response.data);
};
