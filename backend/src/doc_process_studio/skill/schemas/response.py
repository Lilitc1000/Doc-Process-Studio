from pydantic import BaseModel, Field

from ..models.catalog import SkillInterfaceConfig


class SkillListResponse(BaseModel):
    skills: list[SkillInterfaceConfig] = Field(default_factory=list)


class SkillCacheStatusResponse(BaseModel):
    ok: bool = Field(...)
    message: str = Field(default="")


class SkillContextSearchResponse(BaseModel):
    skill_id: str = Field(...)
    query: str = Field(...)
    chunks: list[dict] = Field(default_factory=list)


class SkillConversationCacheResponse(BaseModel):
    conversation_id: str = Field(...)
    exists: bool = Field(...)
    ttl_seconds: int = Field(...)
    message: str = Field(default="")


__all__ = [
    "SkillCacheStatusResponse",
    "SkillContextSearchResponse",
    "SkillConversationCacheResponse",
    "SkillListResponse",
]
