export interface SkillOption {
  id: string;
  displayName: string;
  shortDescription?: string;
  skillType?: string;
}

export interface SkillCatalogPayload {
  skills?: Array<{
    id?: string;
    display_name?: string;
    displayName?: string;
    short_description?: string;
    shortDescription?: string;
    skill_type?: string;
    skillType?: string;
  }>;
}
