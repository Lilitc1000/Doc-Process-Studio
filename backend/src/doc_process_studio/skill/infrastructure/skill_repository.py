"""Skill 基础设施实现：委托 service/ 工具层。"""

from ..application.ports import (
    ConversationStateRepository,
    SkillContextSearcher,
    SkillRegistry,
)
from ..schemas.catalog import SkillInterfaceConfig
from ..schemas.runtime import ConversationAgentState, SkillContextChunk
from ..service.context import search_skill_context_chunks
from ..service.conversation_store import (
    clear_conversation_state,
    get_conversation_state_ttl_seconds,
    load_conversation_state,
    refresh_conversation_state_ttl,
    save_conversation_state,
)
from ..service.registry import get_skill_interface, list_skill_interfaces


class LocalSkillRegistry(SkillRegistry):
    """基于本地 skills/ 目录的 Skill 注册表。"""

    def list_interfaces(self) -> list[SkillInterfaceConfig]:
        return list_skill_interfaces()

    def get_interface(self, skill_id: str) -> SkillInterfaceConfig:
        return get_skill_interface(skill_id)


class HybridSkillContextSearcher(SkillContextSearcher):
    """基于 BM25 + embedding 混合召回的 Skill 上下文检索器。"""

    async def search_chunks(self, skill_id: str, query: str) -> list[SkillContextChunk]:
        return await search_skill_context_chunks(skill_id, query)


class RedisConversationStateRepository(ConversationStateRepository):
    """基于 Redis 的对话状态仓储。"""

    async def load_state(self, conversation_id: str, tenant_id: str = "default") -> ConversationAgentState | None:
        return await load_conversation_state(conversation_id, tenant_id=tenant_id)

    async def save_state(self, state: ConversationAgentState, tenant_id: str = "default") -> None:
        await save_conversation_state(state, tenant_id=tenant_id)

    async def refresh_ttl(self, conversation_id: str, tenant_id: str = "default") -> tuple[bool, int]:
        return await refresh_conversation_state_ttl(conversation_id, tenant_id=tenant_id)

    async def clear_state(self, conversation_id: str, tenant_id: str = "default") -> bool:
        return await clear_conversation_state(conversation_id, tenant_id=tenant_id)

    async def get_ttl_seconds(self, conversation_id: str, tenant_id: str = "default") -> int:
        return await get_conversation_state_ttl_seconds(conversation_id, tenant_id=tenant_id)
