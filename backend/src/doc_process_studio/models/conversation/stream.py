from typing import Literal

from pydantic import BaseModel, Field


class ChatMessageInput(BaseModel):
    role: Literal["system", "user", "assistant"] = Field(
        ...,
        description="消息角色",
    )
    content: str = Field(..., description="消息文本内容")


class ChatInteractionAnswer(BaseModel):
    session_id: str | None = Field(
        default=None,
        description="交互会话标识，用于防止并发覆盖",
    )
    step_id: str = Field(..., description="当前提交的步骤标识")
    value: str | list[str] | None = Field(
        default=None,
        description="当前步骤提交值，single/text 用字符串，multi 用数组",
    )
    custom_value: str | None = Field(
        default=None,
        description="当步骤支持自定义输入时的补充值",
    )
    use_defaults_for_missing: bool = Field(
        default=False,
        description="是否允许缺失字段以默认值继续生成",
    )


class ChatStreamRequest(BaseModel):
    user_message_id: str = Field(
        ...,
        description="当前触发本次请求的用户消息标识",
    )
    conversation_id: str = Field(
        ...,
        description="前后端共享的会话标识，用于缓存 skill 上下文",
    )
    model: str = Field(..., description="要调用的模型名称")
    skill_id: str = Field(
        default="",
        description="保留字段：兼容历史请求，不参与当前规划层主决策。",
    )
    selected_skill_ids: list[str] = Field(
        default_factory=list,
        description="本轮显式选择的 skill 列表；为空时由模型按任务在可用 skill 中隐式选择。",
    )
    messages: list[ChatMessageInput] = Field(
        default_factory=list,
        description="对话消息列表",
    )
    attachment_ids: list[str] = Field(
        default_factory=list,
        description="当前消息路径上已持久化的用户上传文件标识",
    )
    interaction_answer: ChatInteractionAnswer | None = Field(
        default=None,
        description="交互式步骤提交数据；为空表示发起或继续普通对话",
    )
