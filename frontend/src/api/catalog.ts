import type { SkillCatalogPayload } from '../types/common/skill';
import type { ModelCatalogPayload } from '../utils/common/catalog';
import {
  extractModelNames,
  normalizeSkillCatalog,
} from '../utils/common/catalog';
import { apiClient } from './request';

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
