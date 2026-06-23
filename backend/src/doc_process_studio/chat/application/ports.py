"""Chat 域应用层端口定义。"""

from abc import ABC, abstractmethod
from pathlib import Path

from ..schemas.attachment import ChatAttachment, ChatAttachmentMetadata
from ..schemas.response import ChatSessionDetail, ChatSessionListResponse
from ..schemas.session import ChatSessionSnapshot, ChatSessionSummary


class SessionRepository(ABC):
    """会话数据访问端口。

    封装会话列表、详情、upsert、改标题、删除、按前缀/用户批量删除、归属校验。
    """

    @abstractmethod
    async def list_sessions(self, user_id: str) -> ChatSessionListResponse: ...

    @abstractmethod
    async def get_session(self, session_id: str) -> ChatSessionDetail | None: ...

    @abstractmethod
    async def get_session_user_id(self, session_id: str) -> str | None: ...

    @abstractmethod
    async def upsert_session(
        self,
        *,
        session_id: str,
        user_id: str,
        title: str,
        title_source_messages: list[str],
        snapshot: ChatSessionSnapshot,
    ) -> ChatSessionSummary: ...

    @abstractmethod
    async def update_title(self, session_id: str, title: str) -> ChatSessionSummary | None: ...

    @abstractmethod
    async def delete_session(self, session_id: str) -> bool: ...

    @abstractmethod
    async def delete_by_title_prefix(self, user_id: str, title_prefix: str) -> int: ...

    @abstractmethod
    async def delete_by_user(self, user_id: str) -> int: ...


class TitleGenerator(ABC):
    """会话标题生成端口。"""

    @abstractmethod
    async def generate(self, *, model: str, title_source_messages: list[str]) -> str: ...


class ConversationStateStore(ABC):
    """对话状态存储端口（用于删除会话时清理 skill 侧状态）。"""

    @abstractmethod
    async def clear_state(self, conversation_id: str) -> bool: ...


class AttachmentStore(ABC):
    """附件存储端口。

    封装附件路径解析、上传/生成保存、按会话批量删除、过期清理。
    """

    @abstractmethod
    def resolve_path(self, attachment_id: str) -> tuple[ChatAttachmentMetadata | None, Path | None, bool]: ...

    @abstractmethod
    def save_uploaded(
        self,
        *,
        raw_bytes: bytes,
        conversation_id: str,
        skill_id: str,
        file_name: str,
        mime_type: str | None = None,
        extracted_text: str | None = None,
    ) -> ChatAttachment: ...

    @abstractmethod
    def save_generated(
        self,
        *,
        source_path: Path,
        conversation_id: str,
        skill_id: str,
        output_name: str | None = None,
        mime_type: str | None = None,
    ) -> ChatAttachment: ...

    @abstractmethod
    def delete_for_conversation(self, conversation_id: str) -> int: ...

    @abstractmethod
    def cleanup_expired(self) -> None: ...
