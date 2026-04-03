from ...models.conversation.sessions import ChatSessionSnapshot, ChatSessionSummary
from ..infra.redis_store import (
    build_cache_key,
    delete_key,
    get_json,
    get_redis_client,
    set_json,
)

CHAT_SESSION_INDEX_KEY = build_cache_key("chat-sessions", "index")


def build_chat_session_meta_key(session_id: str) -> str:
    return build_cache_key("chat-session", session_id, "meta")


def build_chat_session_snapshot_key(session_id: str) -> str:
    return build_cache_key("chat-session", session_id, "snapshot")


async def list_chat_session_ids() -> list[str]:
    return await get_redis_client().zrevrange(CHAT_SESSION_INDEX_KEY, 0, -1)


async def load_chat_session_summary(session_id: str) -> ChatSessionSummary | None:
    payload = await get_json(build_chat_session_meta_key(session_id))
    if not isinstance(payload, dict):
        return None
    return ChatSessionSummary.model_validate(payload)


async def load_chat_session_snapshot(
    session_id: str,
) -> ChatSessionSnapshot | None:
    payload = await get_json(build_chat_session_snapshot_key(session_id))
    if not isinstance(payload, dict):
        return None
    return ChatSessionSnapshot.model_validate(payload)


async def save_chat_session_summary(summary: ChatSessionSummary) -> None:
    await set_json(
        build_chat_session_meta_key(summary.id),
        summary.model_dump(mode="json"),
        ttl_seconds=None,
    )


async def save_chat_session_snapshot(
    session_id: str,
    snapshot: ChatSessionSnapshot,
) -> None:
    await set_json(
        build_chat_session_snapshot_key(session_id),
        snapshot.model_dump(mode="json"),
        ttl_seconds=None,
    )


async def touch_chat_session_index(
    session_id: str,
    score: float,
) -> None:
    await get_redis_client().zadd(CHAT_SESSION_INDEX_KEY, {session_id: score})


async def delete_chat_session_records(session_id: str) -> bool:
    deleted_meta = await delete_key(build_chat_session_meta_key(session_id))
    deleted_snapshot = await delete_key(build_chat_session_snapshot_key(session_id))
    await get_redis_client().zrem(CHAT_SESSION_INDEX_KEY, session_id)
    return bool(deleted_meta or deleted_snapshot)

