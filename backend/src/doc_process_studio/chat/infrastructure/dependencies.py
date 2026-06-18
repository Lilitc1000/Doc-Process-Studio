"""Chat 域依赖装配。"""

from functools import lru_cache

from ..application.attachment_service import AttachmentService
from ..application.session_service import SessionService
from .attachment_store import FsAttachmentStore
from .conversation_state_store import SkillConversationStateStore
from ..application.ports import AttachmentStore, ConversationStateStore, SessionRepository, TitleGenerator
from .session_repository import OllamaTitleGenerator, SqlSessionRepository


@lru_cache(maxsize=1)
def get_session_repository() -> SessionRepository:
    return SqlSessionRepository()


@lru_cache(maxsize=1)
def get_title_generator() -> TitleGenerator:
    return OllamaTitleGenerator()


@lru_cache(maxsize=1)
def get_conversation_state_store() -> ConversationStateStore:
    return SkillConversationStateStore()


@lru_cache(maxsize=1)
def get_session_service() -> SessionService:
    return SessionService(
        repository=get_session_repository(),
        title_generator=get_title_generator(),
        state_store=get_conversation_state_store(),
    )


@lru_cache(maxsize=1)
def get_attachment_store() -> AttachmentStore:
    return FsAttachmentStore()


@lru_cache(maxsize=1)
def get_attachment_service() -> AttachmentService:
    return AttachmentService(store=get_attachment_store())
