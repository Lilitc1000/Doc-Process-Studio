"""对话消息形状（应用层）。

``role`` / ``content`` 是 LLM 消息与聊天请求共用的基础形状，原位于
``router.schemas.request``（``ChatMessageInput``）；下沉到应用层后命名为
``ChatMessage``，路由层以 ``ChatMessageInput = ChatMessage`` 再导出。
"""

from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"] = Field(
        ...,
        description="消息角色",
    )
    content: str = Field(..., description="消息文本内容")
