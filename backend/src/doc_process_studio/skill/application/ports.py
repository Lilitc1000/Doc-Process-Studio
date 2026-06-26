"""Skill 域应用层端口定义。"""

from abc import ABC, abstractmethod

from .dtos.catalog import SkillInterfaceConfig
from .dtos.runtime import SkillContextChunk


class SkillRegistry(ABC):
    """Skill 注册表端口：发现与查询 Skill 接口配置。"""

    @abstractmethod
    def list_interfaces(self) -> list[SkillInterfaceConfig]: ...

    @abstractmethod
    def get_interface(self, skill_id: str) -> SkillInterfaceConfig: ...


class SkillContextSearcher(ABC):
    """Skill 上下文检索端口：基于 BM25 + embedding 混合召回。"""

    @abstractmethod
    async def search_chunks(self, skill_id: str, query: str) -> list[SkillContextChunk]: ...


class ConversationStateRepository(ABC):
    """对话状态仓储端口：会话级 Agent 状态的 TTL/清理。"""

    @abstractmethod
    async def refresh_ttl(self, conversation_id: str, tenant_id: str = "default") -> tuple[bool, int]: ...

    @abstractmethod
    async def clear_state(self, conversation_id: str, tenant_id: str = "default") -> bool: ...

    @abstractmethod
    async def get_ttl_seconds(self, conversation_id: str, tenant_id: str = "default") -> int: ...
