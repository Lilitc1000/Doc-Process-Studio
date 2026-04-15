export interface SkillOption {
  id: string;
  display_name: string;
  short_description?: string;
  skill_type?: string;
}

export interface SkillCatalogPayload {
  skills?: Array<{
    id?: string;
    display_name?: string;
    short_description?: string;
    skill_type?: string;
  }>;
}
