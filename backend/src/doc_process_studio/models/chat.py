from typing import Literal

from pydantic import BaseModel, Field


class ChatMessageInput(BaseModel):
    role: Literal["system", "user", "assistant"] = Field(
        ...,
        description="消息角色",
    )
    content: str = Field(..., description="消息文本内容")


class ChatStreamRequest(BaseModel):
    conversation_id: str = Field(
        ...,
        description="前后端共享的会话标识，用于缓存 skill 上下文",
    )
    model: str = Field(..., description="要调用的模型名称")
    skill_id: str = Field(
        ...,
        description="当前选中的 skill 标识",
    )
    messages: list[ChatMessageInput] = Field(
        default_factory=list,
        description="对话消息列表",
    )
