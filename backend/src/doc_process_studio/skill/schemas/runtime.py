from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class SkillContextChunk(BaseModel):
    id: str = Field(..., description="chunk 唯一标识")
    skill_id: str = Field(..., description="所属 skill")
    source_path: str = Field(..., description="源文件相对路径")
    title: str = Field(..., description="chunk 标题")
    preview: str = Field(..., description="chunk 预览")
    content: str = Field(..., description="chunk 正文")


class SkillConversationState(BaseModel):
    conversation_id: str = Field(..., description="会话标识")
    skill_id: str = Field(..., description="当前 skill 标识")
    system_prompt: str = Field(..., description="当前 skill 默认提示词")
    loaded_chunk_ids: list[str] = Field(
        default_factory=list,
        description="已经加入会话上下文的 chunk 列表",
    )
    short_term_memory: str = Field(
        default="",
        description="短期记忆：最近一次压缩得到的摘要",
    )
    episodic_memory: str = Field(
        default="",
        description="情节记忆：跨轮对话过程中的关键摘要",
    )
    skill_memory: str = Field(
        default="",
        description="技能记忆：相对稳定的长期技能背景摘要",
    )
    compacted_chunk_ids: list[str] = Field(
        default_factory=list,
        description="已经进入层级记忆、不再全文注入的 chunk 列表",
    )


class SkillPlannerCandidate(BaseModel):
    skill_id: str = Field(..., description="候选技能标识")
    source: Literal["explicit", "implicit_lexical", "implicit_rerank", "system"] = Field(
        ...,
        description="候选来源",
    )
    selected: bool = Field(default=False, description="是否被本轮规划选中")
    lexical_score: float | None = Field(default=None, description="词法召回分数")
    confidence: float | None = Field(default=None, description="模型重排置信度")
    reason: str | None = Field(default=None, description="规划理由")


class SkillPlanDecision(BaseModel):
    planner_model: str = Field(..., description="本轮规划使用的模型")
    required_skill_ids: list[str] = Field(
        default_factory=list,
        description="必须启用的技能（显式）",
    )
    optional_skill_ids: list[str] = Field(
        default_factory=list,
        description="可选启用的技能（隐式）",
    )
    missing_explicit_skill_ids: list[str] = Field(
        default_factory=list,
        description="显式提及但不存在的技能",
    )
    active_skill_ids: list[str] = Field(
        default_factory=list,
        description="本轮最终激活技能列表",
    )
    primary_skill_id: str = Field(..., description="主技能")
    confidence: float | None = Field(default=None, description="本轮规划整体置信度")
    reasons: dict[str, str] = Field(
        default_factory=dict,
        description="按技能给出的规划理由",
    )
    candidates: list[SkillPlannerCandidate] = Field(
        default_factory=list,
        description="候选与选择过程轨迹",
    )
    created_at: datetime = Field(..., description="规划时间")


class SkillToolHistoryRecord(BaseModel):
    skill_id: str = Field(..., description="工具所属技能")
    tool_name: str = Field(..., description="工具名称")
    ok: bool = Field(..., description="工具是否执行成功")
    reused: bool = Field(default=False, description="是否命中重复调用复用")
    attachment_count: int = Field(default=0, description="本次产出的附件数量")
    error: str | None = Field(default=None, description="失败原因")
    created_at: datetime = Field(..., description="记录时间")


class ConversationAgentState(BaseModel):
    conversation_id: str = Field(..., description="会话标识")
    skills_state: dict[str, SkillConversationState] = Field(
        default_factory=dict,
        description="按 skill 维度维护的会话状态",
    )
    planner_trace: list[SkillPlanDecision] = Field(
        default_factory=list,
        description="规划轨迹",
    )
    tool_history: list[SkillToolHistoryRecord] = Field(
        default_factory=list,
        description="工具执行历史",
    )
