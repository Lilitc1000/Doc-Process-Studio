from datetime import UTC, datetime

import httpx

from ...models.conversation.sessions import (
    ChatSessionDetail,
    ChatSessionListResponse,
    ChatSessionSnapshot,
    ChatSessionSummary,
)
from ...models.conversation.stream import ChatMessageInput
from ...settings import settings
from ..infra.ollama_client import extract_first_message_content, post_chat_completion
from .attachments import delete_attachments_for_conversation
from .session_store import (
    delete_chat_session_records,
    list_chat_session_ids,
    load_chat_session_snapshot,
    load_chat_session_summary,
    save_chat_session_snapshot,
    save_chat_session_summary,
    touch_chat_session_index,
)


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

    try:
        response_payload = await post_chat_completion(
            model=model,
            messages=[
                ChatMessageInput(role="system", content=system_prompt),
                ChatMessageInput(role="user", content=user_prompt),
            ],
        )
    except httpx.HTTPError:
        return fallback_title

    content = _normalize_title_candidate(
        extract_first_message_content(response_payload)
    )
    return content or fallback_title


async def list_chat_sessions() -> ChatSessionListResponse:
    session_ids = await list_chat_session_ids()
    sessions: list[ChatSessionSummary] = []

    for session_id in session_ids:
        summary = await load_chat_session_summary(session_id)
        if summary is not None:
            sessions.append(summary)

    return ChatSessionListResponse(sessions=sessions)


async def get_chat_session(session_id: str) -> ChatSessionDetail | None:
    summary = await load_chat_session_summary(session_id)
    snapshot = await load_chat_session_snapshot(session_id)
    if summary is None or snapshot is None:
        return None

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

    await save_chat_session_summary(summary)
    await save_chat_session_snapshot(session_id, snapshot)
    await touch_chat_session_index(session_id, now.timestamp())

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
    await save_chat_session_summary(summary)
    await touch_chat_session_index(session_id, summary.updated_at.timestamp())
    return summary


async def delete_chat_session(session_id: str) -> bool:
    deleted_session = await delete_chat_session_records(session_id)
    deleted_attachments = delete_attachments_for_conversation(session_id)
    return bool(deleted_session or deleted_attachments > 0)
