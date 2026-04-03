from ..models.skill_runtime import SkillConversationState
from ..settings import settings
from .redis_store import (
    build_cache_key,
    delete_key,
    get_json,
    get_ttl_seconds,
    refresh_ttl,
    set_json,
)


def build_conversation_state_key(conversation_id: str) -> str:
    return build_cache_key("conversation", conversation_id)


async def load_conversation_state(
    conversation_id: str,
) -> SkillConversationState | None:
    cached_payload = await get_json(build_conversation_state_key(conversation_id))
    if not isinstance(cached_payload, dict):
        return None
    return SkillConversationState.model_validate(cached_payload)


async def save_conversation_state(state: SkillConversationState) -> None:
    await set_json(
        build_conversation_state_key(state.conversation_id),
        state.model_dump(),
        ttl_seconds=settings.redis_ttl_seconds,
    )


async def refresh_conversation_state_ttl(conversation_id: str) -> tuple[bool, int]:
    key = build_conversation_state_key(conversation_id)
    refreshed = await refresh_ttl(key, ttl_seconds=settings.redis_ttl_seconds)
    return refreshed, await get_ttl_seconds(key)


async def clear_conversation_state(conversation_id: str) -> bool:
    return await delete_key(build_conversation_state_key(conversation_id)) > 0


async def get_conversation_state_ttl_seconds(conversation_id: str) -> int:
    return await get_ttl_seconds(build_conversation_state_key(conversation_id))
