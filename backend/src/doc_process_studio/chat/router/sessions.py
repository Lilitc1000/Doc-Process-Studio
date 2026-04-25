from fastapi import APIRouter, Depends, HTTPException

from ..models.session import ChatSessionSummary
from ..schemas.request import ChatSessionTitleUpdateRequest, ChatSessionUpsertRequest
from ..schemas.response import ChatSessionDetail, ChatSessionListResponse
from ..service.sessions import (
    check_chat_session_access,
    delete_chat_session,
    get_chat_session,
    list_chat_sessions,
    upsert_chat_session,
    update_chat_session_title,
)
from ...core.security import get_current_user_id
from ...chat.service.db_session_store import delete_chat_sessions_by_title_prefix
from ...skill.service.conversation_store import clear_conversation_state

router = APIRouter(prefix="/api/chat-sessions", tags=["chat-sessions"])


@router.get("", response_model=ChatSessionListResponse)
async def list_sessions(
    user_id: str = Depends(get_current_user_id),
) -> ChatSessionListResponse:
    return await list_chat_sessions(user_id)


@router.get("/{session_id}", response_model=ChatSessionDetail)
async def get_session(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
) -> ChatSessionDetail:
    if not await check_chat_session_access(session_id, user_id):
        raise HTTPException(status_code=403, detail="无权访问该会话。")
    session = await get_chat_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="未找到对应历史会话。")
    return session


@router.put("/{session_id}", response_model=ChatSessionSummary)
async def save_session(
    session_id: str,
    payload: ChatSessionUpsertRequest,
    user_id: str = Depends(get_current_user_id),
) -> ChatSessionSummary:
    return await upsert_chat_session(
        session_id=session_id,
        user_id=user_id,
        title=payload.title,
        title_source_messages=payload.title_source_messages,
        snapshot=payload.snapshot,
    )


@router.patch("/{session_id}/title", response_model=ChatSessionSummary)
async def rename_session(
    session_id: str,
    payload: ChatSessionTitleUpdateRequest,
    user_id: str = Depends(get_current_user_id),
) -> ChatSessionSummary:
    if not await check_chat_session_access(session_id, user_id):
        raise HTTPException(status_code=403, detail="无权访问该会话。")
    session = await update_chat_session_title(session_id, payload.title)
    if session is None:
        raise HTTPException(status_code=404, detail="未找到对应历史会话。")
    return session


@router.delete("/by-title-prefix/{prefix}")
async def delete_sessions_by_title_prefix(
    prefix: str,
    user_id: str = Depends(get_current_user_id),
) -> dict[str, int]:
    count = await delete_chat_sessions_by_title_prefix(user_id, prefix)
    return {"deleted": count}


@router.delete("/{session_id}")
async def remove_session(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
) -> dict[str, bool]:
    if not await check_chat_session_access(session_id, user_id):
        raise HTTPException(status_code=403, detail="无权访问该会话。")
    deleted = await delete_chat_session(session_id)
    await clear_conversation_state(session_id)
    return {"deleted": deleted}
