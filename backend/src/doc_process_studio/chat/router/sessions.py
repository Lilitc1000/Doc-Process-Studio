from fastapi import APIRouter, Depends, HTTPException

from ...common.security.security import get_current_user_id
from ..application.dtos.session import ChatSessionSummary
from ..application.session_service import SessionService
from ..domain.errors import ChatError, SessionAccessDeniedError, SessionNotFoundError
from ..infrastructure.dependencies import get_session_service
from .schemas.request import ChatSessionTitleUpdateRequest, ChatSessionUpsertRequest
from .schemas.response import ChatSessionDetail, ChatSessionListResponse

router = APIRouter(prefix="/api/chat-sessions", tags=["chat-sessions"])


def _handle_session_error(exc: ChatError) -> HTTPException:
    if isinstance(exc, SessionAccessDeniedError):
        return HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, SessionNotFoundError):
        return HTTPException(status_code=404, detail="未找到对应历史会话。")
    return HTTPException(status_code=400, detail=str(exc))


@router.get("", response_model=ChatSessionListResponse)
async def list_sessions(
    user_id: str = Depends(get_current_user_id),
    service: SessionService = Depends(get_session_service),
) -> ChatSessionListResponse:
    return await service.list_sessions(user_id)


@router.get("/{session_id}", response_model=ChatSessionDetail)
async def get_session(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    service: SessionService = Depends(get_session_service),
) -> ChatSessionDetail:
    try:
        return await service.get_session(session_id, user_id)
    except ChatError as exc:
        raise _handle_session_error(exc) from exc


@router.put("/{session_id}", response_model=ChatSessionSummary)
async def save_session(
    session_id: str,
    payload: ChatSessionUpsertRequest,
    user_id: str = Depends(get_current_user_id),
    service: SessionService = Depends(get_session_service),
) -> ChatSessionSummary:
    return await service.save_session(
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
    service: SessionService = Depends(get_session_service),
) -> ChatSessionSummary:
    try:
        return await service.rename_session(session_id, user_id, payload.title)
    except ChatError as exc:
        raise _handle_session_error(exc) from exc


@router.delete("/by-title-prefix/{prefix}")
async def delete_sessions_by_title_prefix(
    prefix: str,
    user_id: str = Depends(get_current_user_id),
    service: SessionService = Depends(get_session_service),
) -> dict[str, int]:
    count = await service.delete_sessions_by_title_prefix(user_id, prefix)
    return {"deleted": count}


@router.delete("/by-user/{target_user_id}")
async def delete_sessions_by_user(
    target_user_id: str,
    user_id: str = Depends(get_current_user_id),
    service: SessionService = Depends(get_session_service),
) -> dict[str, int]:
    try:
        count = await service.delete_sessions_by_user(target_user_id, user_id)
    except ChatError as exc:
        raise _handle_session_error(exc) from exc
    return {"deleted": count}


@router.delete("/{session_id}")
async def remove_session(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    service: SessionService = Depends(get_session_service),
) -> dict[str, bool]:
    try:
        deleted = await service.delete_session(session_id, user_id)
    except ChatError as exc:
        raise _handle_session_error(exc) from exc
    return {"deleted": deleted}
