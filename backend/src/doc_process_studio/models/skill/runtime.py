from pydantic import BaseModel, Field


class SkillContextChunk(BaseModel):
    id: str = Field(..., description="chunk 唯一标识")
    skill_id: str = Field(..., description="所属 skill")
    source_path: str = Field(..., description="源文件相对路径")
    title: str = Field(..., description="chunk 标题")
    preview: str = Field(..., description="chunk 预览")
    content: str = Field(..., description="chunk 正文")


class SkillContextChunkSummary(BaseModel):
    id: str = Field(..., description="chunk 唯一标识")
    source_path: str = Field(..., description="源文件相对路径")
    title: str = Field(..., description="chunk 标题")
    preview: str = Field(..., description="chunk 预览")


class SkillContextPlannerDecision(BaseModel):
    should_load_more: bool = Field(
        default=False,
        description="是否需要加载更多 skill 正文片段",
    )
    chunk_ids: list[str] = Field(
        default_factory=list,
        description="推荐加载的 chunk 列表",
    )
    reason: str = Field(default="", description="决策原因")


class SkillConversationState(BaseModel):
    conversation_id: str = Field(..., description="会话标识")
    skill_id: str = Field(..., description="当前 skill 标识")
    system_prompt: str = Field(..., description="当前 skill 默认提示词")
    loaded_chunk_ids: list[str] = Field(
        default_factory=list,
        description="已经加入会话上下文的 chunk 列表",
    )
    compact_summary: str = Field(
        default="",
        description="超出上下文后保留的压缩 skill 记忆",
    )
    compacted_chunk_ids: list[str] = Field(
        default_factory=list,
        description="已经被压缩进 compact_summary 的 chunk 列表",
    )

