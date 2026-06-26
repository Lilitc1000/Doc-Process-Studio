import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from ...common.infrastructure.cache import ping_redis
from ...common.security.security import get_current_user_id
from ..application.skill_service import SkillService
from ..domain.errors import SkillError, SkillNotFoundError
from ..infrastructure.dependencies import get_skill_service
from .schemas import (
    SkillCacheStatusResponse,
    SkillContextSearchResponse,
    SkillConversationCacheResponse,
    SkillListResponse,
)

_logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api",
    tags=["skills"],
    dependencies=[Depends(get_current_user_id)],
)


def _handle_skill_error(exc: SkillError) -> HTTPException:
    if isinstance(exc, SkillNotFoundError):
        _logger.warning("Skill error (404): %s", exc)
        return HTTPException(status_code=404, detail=str(exc))
    _logger.warning("Skill error (400): %s", exc)
    return HTTPException(status_code=400, detail=str(exc))


@router.get("/skills", response_model=SkillListResponse)
async def list_skills(
    service: SkillService = Depends(get_skill_service),
) -> SkillListResponse:
    return SkillListResponse(skills=service.list_skills())


@router.get(
    "/skills/{skill_id}/context/search",
    response_model=SkillContextSearchResponse,
)
async def search_skill_context(
    skill_id: str,
    query: str = Query(..., min_length=1),
    service: SkillService = Depends(get_skill_service),
) -> SkillContextSearchResponse:
    try:
        matched_chunks = await service.search_context(skill_id, query)
    except SkillError as exc:
        raise _handle_skill_error(exc) from exc

    return SkillContextSearchResponse(
        skill_id=skill_id,
        query=query,
        chunks=[
            {
                "id": chunk.id,
                "source_path": chunk.source_path,
                "title": chunk.title,
                "preview": chunk.preview,
            }
            for chunk in matched_chunks
        ],
    )


@router.get("/skills/cache/status", response_model=SkillCacheStatusResponse)
async def get_skill_cache_status() -> SkillCacheStatusResponse:
    try:
        if await ping_redis():
            return SkillCacheStatusResponse(
                ok=True,
                message="Redis 已连接，可用于 skill 会话缓存。",
            )
    except Exception as exc:
        return SkillCacheStatusResponse(ok=False, message=str(exc))

    return SkillCacheStatusResponse(
        ok=False,
        message="Redis 未返回成功状态。",
    )


@router.post(
    "/skills/cache/conversations/{conversation_id}/refresh",
    response_model=SkillConversationCacheResponse,
)
async def refresh_skill_conversation_cache(
    conversation_id: str,
    tenant_id: str = Query(default="default"),
    service: SkillService = Depends(get_skill_service),
) -> SkillConversationCacheResponse:
    refreshed, ttl_seconds = await service.refresh_conversation_cache(conversation_id, tenant_id=tenant_id)
    return SkillConversationCacheResponse(
        conversation_id=conversation_id,
        exists=refreshed,
        ttl_seconds=ttl_seconds,
        message=("会话缓存 TTL 已刷新。" if refreshed else "未找到该会话缓存，无法刷新 TTL。"),
    )


@router.delete(
    "/skills/cache/conversations/{conversation_id}",
    response_model=SkillConversationCacheResponse,
)
async def delete_skill_conversation_cache(
    conversation_id: str,
    tenant_id: str = Query(default="default"),
    service: SkillService = Depends(get_skill_service),
) -> SkillConversationCacheResponse:
    cleared, ttl_seconds = await service.delete_conversation_cache(conversation_id, tenant_id=tenant_id)
    return SkillConversationCacheResponse(
        conversation_id=conversation_id,
        exists=not cleared and ttl_seconds >= 0,
        ttl_seconds=ttl_seconds,
        message=("会话缓存已清理。" if cleared else "未找到该会话缓存，无需清理。"),
    )
