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
    const displayName = (
      skill.display_name ??
      skill.displayName ??
      skill.id ??
      ''
    ).trim();
    const shortDescription = (
      skill.short_description ??
      skill.shortDescription ??
      ''
    ).trim();
    const skillType = (skill.skill_type ?? skill.skillType ?? 'chat').trim();

    if (!id || !displayName) {
      continue;
    }

    skills.push({
      id,
      displayName,
      shortDescription,
      skillType,
    });
  }

  return skills;
};
