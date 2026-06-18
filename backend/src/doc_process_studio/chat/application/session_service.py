"""会话用例服务。"""

from ..domain.errors import SessionAccessDeniedError, SessionNotFoundError
from ..schemas.response import ChatSessionDetail, ChatSessionListResponse
from ..schemas.session import ChatSessionSnapshot, ChatSessionSummary
from .ports import ConversationStateStore, SessionRepository, TitleGenerator


class SessionService:
    """会话用例服务：编排会话 CRUD、归属校验、标题生成与状态清理。"""

    def __init__(
        self,
        *,
        repository: SessionRepository,
        title_generator: TitleGenerator,
        state_store: ConversationStateStore,
    ) -> None:
        self._repo = repository
        self._titles = title_generator
        self._states = state_store

    async def list_sessions(self, user_id: str) -> ChatSessionListResponse:
        return await self._repo.list_sessions(user_id)

    async def get_session(self, session_id: str, user_id: str) -> ChatSessionDetail:
        await self._ensure_access(session_id, user_id)
        session = await self._repo.get_session(session_id)
        if session is None:
            raise SessionNotFoundError("Session not found")
        return session

    async def save_session(
        self,
        *,
        session_id: str,
        user_id: str,
        title: str,
        title_source_messages: list[str],
        snapshot: ChatSessionSnapshot,
    ) -> ChatSessionSummary:
        existing = await self._repo.get_session(session_id)
        normalized_title = title.strip()
        if not normalized_title:
            if existing and existing.title.strip():
                normalized_title = existing.title
            else:
                normalized_title = await self._titles.generate(
                    model=snapshot.selected_model,
                    title_source_messages=title_source_messages,
                )
        return await self._repo.upsert_session(
            session_id=session_id,
            user_id=user_id,
            title=normalized_title,
            title_source_messages=title_source_messages,
            snapshot=snapshot,
        )

    async def rename_session(
        self, session_id: str, user_id: str, title: str
    ) -> ChatSessionSummary:
        await self._ensure_access(session_id, user_id)
        summary = await self._repo.update_title(session_id, title.strip())
        if summary is None:
            raise SessionNotFoundError("Session not found")
        return summary

    async def delete_sessions_by_title_prefix(
        self, user_id: str, title_prefix: str
    ) -> int:
        return await self._repo.delete_by_title_prefix(user_id, title_prefix)

    async def delete_sessions_by_user(self, target_user_id: str, user_id: str) -> int:
        if target_user_id != user_id:
            raise SessionAccessDeniedError("无权删除其他用户的会话。")
        return await self._repo.delete_by_user(target_user_id)

    async def delete_session(self, session_id: str, user_id: str) -> bool:
        await self._ensure_access(session_id, user_id)
        deleted = await self._repo.delete_session(session_id)
        await self._states.clear_state(session_id)
        return deleted

    async def _ensure_access(self, session_id: str, user_id: str) -> None:
        owner_id = await self._repo.get_session_user_id(session_id)
        if owner_id is None or owner_id != user_id:
            raise SessionAccessDeniedError("无权访问该会话。")
