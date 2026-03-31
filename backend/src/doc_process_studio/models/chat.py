from typing import Literal

from pydantic import BaseModel, Field

ProcessingMode = Literal[
    "快速摘要",
    "智能问答",
    "结构化提取",
    "全文整理",
]


class ChatMessageInput(BaseModel):
    role: Literal["system", "user", "assistant"] = Field(
        ...,
        description="消息角色",
    )
    content: str = Field(..., description="消息文本内容")


class ChatStreamRequest(BaseModel):
    model: str = Field(..., description="要调用的模型名称")
    processing_mode: ProcessingMode = Field(
        ...,
        description="文档处理方式",
    )
    messages: list[ChatMessageInput] = Field(
        default_factory=list,
        description="对话消息列表",
    )
