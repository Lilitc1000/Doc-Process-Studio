import type { SkillCatalogPayload, SkillOption } from '../types/skill';

export interface RemoteModelRecord {
  name?: string;
  model?: string;
  id?: string;
}

export interface ModelCatalogPayload {
  models?: RemoteModelRecord[];
  data?: RemoteModelRecord[];
}

export const extractModelNames = (payload: ModelCatalogPayload) => {
  const rawModels = payload.models ?? payload.data ?? [];
  const uniqueModelNames = new Set<string>();

  for (const item of rawModels) {
    const resolvedName = (item.name ?? item.model ?? item.id ?? '').trim();
    if (resolvedName) {
      uniqueModelNames.add(resolvedName);
    }
  }

  return Array.from(uniqueModelNames);
};

export const normalizeSkillCatalog = (payload: SkillCatalogPayload) => {
  const rawSkills = payload.skills ?? [];
  const skills: SkillOption[] = [];

  for (const skill of rawSkills) {
    const id = skill.id?.trim() ?? '';
    const display_name = (skill.display_name ?? skill.id ?? '').trim();
    const short_description = (skill.short_description ?? '').trim();
    const skill_type = (skill.skill_type ?? 'chat').trim();

    if (!id || !display_name) {
      continue;
    }

    skills.push({
      id,
      display_name,
      short_description,
      skill_type,
    });
  }

  return skills;
};
