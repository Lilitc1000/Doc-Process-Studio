from fastapi import APIRouter, HTTPException, Query

from ...models.skill.catalog import (
    SkillCacheStatusResponse,
    SkillContextSearchResponse,
    SkillConversationCacheResponse,
    SkillListResponse,
)
from ...services.infra.redis_store import ping_redis
from ...services.skill.context import search_skill_context_chunks
from ...services.skill.conversation_store import (
    clear_conversation_state,
    get_conversation_state_ttl_seconds,
    refresh_conversation_state_ttl,
)
from ...services.skill.registry import (
    get_skill_interface,
    list_skill_interfaces,
)

router = APIRouter(prefix="/api", tags=["skills"])


@router.get("/skills", response_model=SkillListResponse)
async def list_skills() -> SkillListResponse:
    return SkillListResponse(
        skills=list_skill_interfaces(),
    )


@router.get(
    "/skills/{skill_id}/context/search",
    response_model=SkillContextSearchResponse,
)
async def search_skill_context(
    skill_id: str,
    query: str = Query(..., min_length=1),
) -> SkillContextSearchResponse:
    try:
        get_skill_interface(skill_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    matched_chunks = search_skill_context_chunks(skill_id, query)
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
) -> SkillConversationCacheResponse:
    refreshed, ttl_seconds = await refresh_conversation_state_ttl(
        conversation_id,
        tenant_id=tenant_id,
    )
    return SkillConversationCacheResponse(
        conversation_id=conversation_id,
        exists=refreshed,
        ttl_seconds=ttl_seconds,
        message=(
            "会话缓存 TTL 已刷新。"
            if refreshed
            else "未找到该会话缓存，无法刷新 TTL。"
        ),
    )


@router.delete(
    "/skills/cache/conversations/{conversation_id}",
    response_model=SkillConversationCacheResponse,
)
async def delete_skill_conversation_cache(
    conversation_id: str,
    tenant_id: str = Query(default="default"),
) -> SkillConversationCacheResponse:
    cleared = await clear_conversation_state(conversation_id, tenant_id=tenant_id)
    ttl_seconds = await get_conversation_state_ttl_seconds(
        conversation_id,
        tenant_id=tenant_id,
    )
    return SkillConversationCacheResponse(
        conversation_id=conversation_id,
        exists=not cleared and ttl_seconds >= 0,
        ttl_seconds=ttl_seconds,
        message=(
            "会话缓存已清理。"
            if cleared
            else "未找到该会话缓存，无需清理。"
        ),
    )
