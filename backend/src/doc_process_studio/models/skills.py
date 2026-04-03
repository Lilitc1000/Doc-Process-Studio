from pydantic import BaseModel, Field


class SkillInterfaceConfig(BaseModel):
    id: str = Field(..., description="skill 唯一标识")
    display_name: str = Field(..., description="用于前端显示的名称")
    short_description: str = Field(
        default="",
        description="skill 简短说明",
    )
    default_prompt: str = Field(..., description="默认注入提示词")


class SkillListResponse(BaseModel):
    skills: list[SkillInterfaceConfig] = Field(
        default_factory=list,
        description="当前可用的 skill 列表",
    )
    default_skill_id: str = Field(
        ...,
        description="默认选中的 skill 标识",
    )
