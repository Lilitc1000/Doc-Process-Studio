export interface SkillOption {
  id: string;
  displayName: string;
  shortDescription?: string;
}

export interface SkillCatalogPayload {
  skills?: Array<{
    id?: string;
    display_name?: string;
    displayName?: string;
    short_description?: string;
    shortDescription?: string;
  }>;
  default_skill_id?: string;
  defaultSkillId?: string;
}
