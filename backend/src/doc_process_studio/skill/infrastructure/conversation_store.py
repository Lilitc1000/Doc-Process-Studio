import logging

from ...common.infrastructure.cache import (
    build_cache_key,
    delete_key,
    get_json,
    get_ttl_seconds,
    refresh_ttl,
    set_json,
)
from ...common.infrastructure.config import settings
from ..application.dtos.runtime import ConversationAgentState

logger = logging.getLogger(__name__)


def build_conversation_state_key(
    conversation_id: str,
    tenant_id: str = "default",
) -> str:
    normalized_tenant_id = tenant_id.strip() or "default"
    return build_cache_key("conversation", normalized_tenant_id, conversation_id)


async def load_conversation_state(
    conversation_id: str,
    tenant_id: str = "default",
) -> ConversationAgentState | None:
    cached_payload = await get_json(build_conversation_state_key(conversation_id, tenant_id))
    if not isinstance(cached_payload, dict):
        return None
    return ConversationAgentState.model_validate(cached_payload)


async def save_conversation_state(
    state: ConversationAgentState,
    tenant_id: str = "default",
) -> None:
    await set_json(
        build_conversation_state_key(state.conversation_id, tenant_id),
        state.model_dump(mode="json"),
        ttl_seconds=settings.redis_ttl_seconds,
    )


async def refresh_conversation_state_ttl(
    conversation_id: str,
    tenant_id: str = "default",
) -> tuple[bool, int]:
    key = build_conversation_state_key(conversation_id, tenant_id)
    refreshed = await refresh_ttl(key, ttl_seconds=settings.redis_ttl_seconds)
    return refreshed, await get_ttl_seconds(key)


async def clear_conversation_state(
    conversation_id: str,
    tenant_id: str = "default",
) -> bool:
    return await delete_key(build_conversation_state_key(conversation_id, tenant_id)) > 0


async def get_conversation_state_ttl_seconds(
    conversation_id: str,
    tenant_id: str = "default",
) -> int:
    return await get_ttl_seconds(build_conversation_state_key(conversation_id, tenant_id))
