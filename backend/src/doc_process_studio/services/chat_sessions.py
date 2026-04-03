from datetime import UTC, datetime

import httpx

from ..models.chat import ChatMessageInput
from ..models.chat_sessions import (
    ChatSessionDetail,
    ChatSessionListResponse,
    ChatSessionSnapshot,
    ChatSessionSummary,
)
from ..settings import settings
from .redis_store import (
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


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _normalize_title_candidate(value: str) -> str:
    collapsed = " ".join(value.split()).strip()
    return collapsed[:40]


def _build_local_session_title(title_source_messages: list[str]) -> str:
    for message in title_source_messages:
        normalized = _normalize_title_candidate(message)
        if normalized:
            return normalized[:18]
    return "新对话"


async def generate_session_title(
    *,
    model: str,
    title_source_messages: list[str],
) -> str:
    fallback_title = _build_local_session_title(title_source_messages)
    if not settings.ollama_base_url or not title_source_messages:
        return fallback_title

    system_prompt = (
        "你是对话标题生成器。"
        "请根据给定对话内容生成一个简洁、自然的中文标题。"
        "要求少于 14 个汉字，不要使用引号，不要带句号。"
        "只输出标题本身。"
    )
    user_prompt = "\n\n".join(
        [
            "请基于下面这些对话片段生成标题：",
            "\n".join(
                f"- {message.strip()}"
                for message in title_source_messages
                if message.strip()
            ),
        ]
    )

    payload = {
        "model": model,
        "stream": False,
        "messages": [
            ChatMessageInput(role="system", content=system_prompt).model_dump(),
            ChatMessageInput(role="user", content=user_prompt).model_dump(),
        ],
    }

    timeout = httpx.Timeout(
        connect=settings.ollama_timeout_seconds,
        read=settings.ollama_timeout_seconds,
        write=settings.ollama_timeout_seconds,
        pool=settings.ollama_timeout_seconds,
    )

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{settings.ollama_base_url.rstrip('/')}/v1/chat/completions",
                json=payload,
            )
            response.raise_for_status()
            response_payload = response.json()
    except httpx.HTTPError:
        return fallback_title

    choices = response_payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return fallback_title

    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        return fallback_title

    message = first_choice.get("message")
    if not isinstance(message, dict):
        return fallback_title

    content = _normalize_title_candidate(str(message.get("content", "")))
    return content or fallback_title


async def list_chat_sessions() -> ChatSessionListResponse:
    session_ids = await get_redis_client().zrevrange(CHAT_SESSION_INDEX_KEY, 0, -1)
    sessions: list[ChatSessionSummary] = []

    for session_id in session_ids:
        meta_payload = await get_json(build_chat_session_meta_key(session_id))
        if isinstance(meta_payload, dict):
            sessions.append(ChatSessionSummary.model_validate(meta_payload))

    return ChatSessionListResponse(sessions=sessions)


async def get_chat_session(session_id: str) -> ChatSessionDetail | None:
    meta_payload = await get_json(build_chat_session_meta_key(session_id))
    snapshot_payload = await get_json(build_chat_session_snapshot_key(session_id))
    if not isinstance(meta_payload, dict) or not isinstance(snapshot_payload, dict):
        return None

    summary = ChatSessionSummary.model_validate(meta_payload)
    snapshot = ChatSessionSnapshot.model_validate(snapshot_payload)
    return ChatSessionDetail(
        **summary.model_dump(),
        snapshot=snapshot,
    )


async def upsert_chat_session(
    *,
    session_id: str,
    title: str,
    title_source_messages: list[str],
    snapshot: ChatSessionSnapshot,
) -> ChatSessionSummary:
    existing_session = await get_chat_session(session_id)
    now = _utcnow()
    normalized_title = title.strip()

    if not normalized_title:
        if existing_session and existing_session.title.strip():
            normalized_title = existing_session.title
        else:
            normalized_title = await generate_session_title(
                model=snapshot.selected_model,
                title_source_messages=title_source_messages,
            )

    created_at = existing_session.created_at if existing_session else now
    summary = ChatSessionSummary(
        id=session_id,
        title=normalized_title,
        created_at=created_at,
        updated_at=now,
        selected_processing_mode=snapshot.selected_processing_mode,
        selected_model=snapshot.selected_model,
    )

    await set_json(
        build_chat_session_meta_key(session_id),
        summary.model_dump(mode="json"),
        ttl_seconds=None,
    )
    await set_json(
        build_chat_session_snapshot_key(session_id),
        snapshot.model_dump(mode="json"),
        ttl_seconds=None,
    )
    await get_redis_client().zadd(
        CHAT_SESSION_INDEX_KEY,
        {session_id: now.timestamp()},
    )

    return summary


async def update_chat_session_title(
    session_id: str,
    title: str,
) -> ChatSessionSummary | None:
    existing_session = await get_chat_session(session_id)
    if existing_session is None:
        return None

    summary = ChatSessionSummary(
        **existing_session.model_dump(exclude={"snapshot"}),
        title=title.strip(),
        updated_at=_utcnow(),
    )
    await set_json(
        build_chat_session_meta_key(session_id),
        summary.model_dump(mode="json"),
        ttl_seconds=None,
    )
    await get_redis_client().zadd(
        CHAT_SESSION_INDEX_KEY,
        {session_id: summary.updated_at.timestamp()},
    )
    return summary


async def delete_chat_session(session_id: str) -> bool:
    deleted_meta = await delete_key(build_chat_session_meta_key(session_id))
    deleted_snapshot = await delete_key(build_chat_session_snapshot_key(session_id))
    await get_redis_client().zrem(CHAT_SESSION_INDEX_KEY, session_id)
    return bool(deleted_meta or deleted_snapshot)
