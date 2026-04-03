from fastapi import APIRouter, HTTPException

from ..models.chat_sessions import (
    ChatSessionDetail,
    ChatSessionListResponse,
    ChatSessionSummary,
    ChatSessionTitleUpdateRequest,
    ChatSessionUpsertRequest,
)
from ..services.chat_sessions import (
    delete_chat_session,
    get_chat_session,
    list_chat_sessions,
    upsert_chat_session,
    update_chat_session_title,
)
from ..services.skill_conversation_store import clear_conversation_state

router = APIRouter(prefix="/api/chat-sessions", tags=["chat-sessions"])


@router.get("", response_model=ChatSessionListResponse)
async def list_sessions() -> ChatSessionListResponse:
    return await list_chat_sessions()


@router.get("/{session_id}", response_model=ChatSessionDetail)
async def get_session(session_id: str) -> ChatSessionDetail:
    session = await get_chat_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="未找到对应历史会话。")
    return session


@router.put("/{session_id}", response_model=ChatSessionSummary)
async def save_session(
    session_id: str,
    payload: ChatSessionUpsertRequest,
) -> ChatSessionSummary:
    return await upsert_chat_session(
        session_id=session_id,
        title=payload.title,
        title_source_messages=payload.title_source_messages,
        snapshot=payload.snapshot,
    )


@router.patch("/{session_id}/title", response_model=ChatSessionSummary)
async def rename_session(
    session_id: str,
    payload: ChatSessionTitleUpdateRequest,
) -> ChatSessionSummary:
    session = await update_chat_session_title(session_id, payload.title)
    if session is None:
        raise HTTPException(status_code=404, detail="未找到对应历史会话。")
    return session


@router.delete("/{session_id}")
async def remove_session(session_id: str) -> dict[str, bool]:
    deleted = await delete_chat_session(session_id)
    await clear_conversation_state(session_id)
    return {"deleted": deleted}
