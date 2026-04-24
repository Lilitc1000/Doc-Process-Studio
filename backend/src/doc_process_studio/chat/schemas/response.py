from pydantic import BaseModel, Field

from ..models.session import ChatSessionSnapshot, ChatSessionSummary


class ChatSessionListResponse(BaseModel):
    sessions: list[ChatSessionSummary] = Field(
        default_factory=list,
        description="历史会话列表",
    )


class ChatSessionDetail(ChatSessionSummary):
    snapshot: ChatSessionSnapshot = Field(..., description="会话快照")


__all__ = [
    "ChatSessionDetail",
    "ChatSessionListResponse",
]
