export interface SkillOption {
  id: string;
  displayName: string;
  shortDescription?: string;
  skillType?: string;
}

export interface SkillCatalogPayload {
  skills?: Array<{
    id?: string;
    displayName?: string;
    shortDescription?: string;
    skillType?: string;
  }>;
}
