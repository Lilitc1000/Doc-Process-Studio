import type { SkillCatalogPayload } from '../types/skill';
import type { ModelCatalogPayload } from '../utils/catalog';
import { extractModelNames, normalizeSkillCatalog } from '../utils/catalog';
import { apiClient } from './client';

export const fetchAvailableModels = async () => {
  const response = await apiClient.get<ModelCatalogPayload>('/models');
  return extractModelNames(response.data);
};

export const fetchAvailableSkills = async () => {
  const response = await apiClient.get<SkillCatalogPayload>('/skills');
  return {
    skills: normalizeSkillCatalog(response.data),
  };
};
