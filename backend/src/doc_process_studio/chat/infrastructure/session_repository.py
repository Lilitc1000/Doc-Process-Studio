"""会话仓储实现：委托 sessions 与 db_session_store 工具层。"""

from ..application.dtos.session import ChatSessionSnapshot, ChatSessionSummary
from ..application.ports import SessionRepository, TitleGenerator
from ..router.schemas.response import ChatSessionDetail, ChatSessionListResponse
from .db_session_store import (
    delete_chat_sessions_by_title_prefix,
    delete_chat_sessions_by_user,
    get_chat_session_user_id,
    save_chat_session_snapshot,
    save_chat_session_summary_with_user_id,
    touch_chat_session_updated_at,
)
from .sessions import (
    delete_chat_session,
    generate_session_title,
    get_chat_session,
    list_chat_sessions,
)


class SqlSessionRepository(SessionRepository):
    """基于 SQLAlchemy 的会话仓储。"""

    async def list_sessions(self, user_id: str) -> ChatSessionListResponse:
        return await list_chat_sessions(user_id)

    async def get_session(self, session_id: str) -> ChatSessionDetail | None:
        return await get_chat_session(session_id)

    async def get_session_user_id(self, session_id: str) -> str | None:
        return await get_chat_session_user_id(session_id)

    async def upsert_session(
        self,
        *,
        session_id: str,
        user_id: str,
        title: str,
        snapshot: ChatSessionSnapshot,
    ) -> ChatSessionSummary:
        from ...common.utils.dtutils import to_utc8, utcnow

        existing = await get_chat_session(session_id)
        created_at = existing.created_at if existing else to_utc8(utcnow())
        summary = ChatSessionSummary(
            id=session_id,
            title=title,
            created_at=created_at,
            updated_at=to_utc8(utcnow()),
            selected_model=snapshot.selected_model,
            selected_reranker_model=(snapshot.selected_reranker_model or snapshot.selected_model),
        )
        await save_chat_session_summary_with_user_id(summary, user_id)
        await save_chat_session_snapshot(session_id, snapshot)
        await touch_chat_session_updated_at(session_id)
        return summary

    async def update_title(self, session_id: str, title: str) -> ChatSessionSummary | None:
        from ...common.utils.dtutils import to_utc8, utcnow

        existing = await get_chat_session(session_id)
        if existing is None:
            return None
        summary = ChatSessionSummary(
            **existing.model_dump(exclude={"snapshot"}),
            title=title,
            updated_at=to_utc8(utcnow()),
        )
        await save_chat_session_summary_with_user_id(
            summary,
            await get_chat_session_user_id(session_id) or "",
        )
        await touch_chat_session_updated_at(session_id)
        return summary

    async def delete_session(self, session_id: str) -> bool:
        return await delete_chat_session(session_id)

    async def delete_by_title_prefix(self, user_id: str, title_prefix: str) -> int:
        return await delete_chat_sessions_by_title_prefix(user_id, title_prefix)

    async def delete_by_user(self, user_id: str) -> int:
        return await delete_chat_sessions_by_user(user_id)


class OllamaTitleGenerator(TitleGenerator):
    """基于 Ollama 的会话标题生成器。"""

    async def generate(self, *, model: str, title_source_messages: list[str]) -> str:
        return await generate_session_title(
            model=model,
            title_source_messages=title_source_messages,
        )
