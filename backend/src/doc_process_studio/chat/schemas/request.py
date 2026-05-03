from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .session import ChatSessionSnapshot


class ChatMessageInput(BaseModel):
    role: Literal["system", "user", "assistant"] = Field(
        ...,
        description="消息角色",
    )
    content: str = Field(..., description="消息文本内容")


class ChatStreamRequest(BaseModel):
    user_message_id: str = Field(
        ...,
        description="当前触发本次请求的用户消息标识",
    )
    conversation_id: str = Field(
        ...,
        description="前后端共享的会话标识，用于缓存 skill 上下文",
    )
    tenant_id: str = Field(
        default="default",
        description="租户标识，用于请求隔离、限流与会话缓存隔离。",
    )
    trace_id: str = Field(
        default="",
        description="可选请求追踪标识；为空时后端自动生成。",
    )
    model: str = Field(..., description="要调用的模型名称")
    reranker_model: str = Field(
        default="",
        description="用于检索重排序的轻量模型；为空时回退使用生成模型。",
    )
    confirm_sensitive_actions: bool = Field(
        default=True,
        description="是否允许执行需要显式确认的敏感工具操作。",
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


class ChatSessionUpsertRequest(BaseModel):
    title: str = Field(default="", description="会话标题")
    title_source_messages: list[str] = Field(
        default_factory=list,
        description="用于自动生成标题的消息片段",
    )
    snapshot: "ChatSessionSnapshot" = Field(..., description="会话快照")


class ChatSessionTitleUpdateRequest(BaseModel):
    title: str = Field(..., min_length=1, description="新的会话标题")


__all__ = [
    "ChatMessageInput",
    "ChatSessionTitleUpdateRequest",
    "ChatSessionUpsertRequest",
    "ChatStreamRequest",
]
