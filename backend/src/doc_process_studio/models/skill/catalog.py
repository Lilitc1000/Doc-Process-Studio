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


class SkillContextSearchResponse(BaseModel):
    skill_id: str = Field(..., description="skill 标识")
    query: str = Field(..., description="检索关键词")
    chunks: list[dict[str, str]] = Field(
        default_factory=list,
        description="命中的 skill 片段",
    )


class SkillCacheStatusResponse(BaseModel):
    ok: bool = Field(..., description="Redis 是否可用")
    message: str = Field(..., description="状态消息")


class SkillConversationCacheResponse(BaseModel):
    conversation_id: str = Field(..., description="会话标识")
    exists: bool = Field(..., description="Redis 中是否存在该会话状态")
    ttl_seconds: int = Field(..., description="当前剩余 TTL 秒数")
    message: str = Field(..., description="状态说明")

