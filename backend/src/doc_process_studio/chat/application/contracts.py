"""对话应用服务契约。

定义应用服务对外暴露的调用接口，测试桩类继承此契约以确保签名同步。
运行时实例化桩类会自动检测未实现的抽象方法。
"""

from abc import ABC, abstractmethod

from ..router.schemas.response import ChatSessionDetail, ChatSessionListResponse
from .dtos.session import ChatSessionSnapshot, ChatSessionSummary


class SessionServiceContract(ABC):
    """会话用例服务契约。"""

    @abstractmethod
    async def list_sessions(self, user_id: str) -> ChatSessionListResponse: ...

    @abstractmethod
    async def get_session(self, session_id: str, user_id: str) -> ChatSessionDetail: ...

    @abstractmethod
    async def save_session(
        self,
        *,
        session_id: str,
        user_id: str,
        title: str,
        title_source_messages: list[str],
        snapshot: ChatSessionSnapshot,
    ) -> ChatSessionSummary: ...

    @abstractmethod
    async def rename_session(self, session_id: str, user_id: str, title: str) -> ChatSessionSummary: ...

    @abstractmethod
    async def delete_sessions_by_title_prefix(self, user_id: str, title_prefix: str) -> int: ...

    @abstractmethod
    async def delete_sessions_by_user(self, target_user_id: str, user_id: str) -> int: ...

    @abstractmethod
    async def delete_session(self, session_id: str, user_id: str) -> bool: ...
