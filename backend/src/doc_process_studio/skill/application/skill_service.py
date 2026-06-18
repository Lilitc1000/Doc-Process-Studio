"""Skill 用例服务。"""

from ..domain.errors import SkillNotFoundError
from ..schemas.catalog import SkillInterfaceConfig
from ..schemas.runtime import SkillContextChunk
from .ports import (
    ConversationStateRepository,
    SkillContextSearcher,
    SkillRegistry,
)


class SkillService:
    """Skill 用例服务：编排 Skill 列表、上下文检索、会话状态管理。"""

    def __init__(
        self,
        *,
        registry: SkillRegistry,
        context_searcher: SkillContextSearcher,
        state_repo: ConversationStateRepository,
    ) -> None:
        self._registry = registry
        self._searcher = context_searcher
        self._states = state_repo

    def list_skills(self) -> list[SkillInterfaceConfig]:
        return self._registry.list_interfaces()

    async def search_context(
        self, skill_id: str, query: str
    ) -> list[SkillContextChunk]:
        self._require_skill(skill_id)
        return await self._searcher.search_chunks(skill_id, query)

    async def refresh_conversation_cache(
        self, conversation_id: str, tenant_id: str = "default"
    ) -> tuple[bool, int]:
        return await self._states.refresh_ttl(conversation_id, tenant_id=tenant_id)

    async def delete_conversation_cache(
        self, conversation_id: str, tenant_id: str = "default"
    ) -> tuple[bool, int]:
        cleared = await self._states.clear_state(conversation_id, tenant_id=tenant_id)
        ttl_seconds = await self._states.get_ttl_seconds(
            conversation_id, tenant_id=tenant_id
        )
        return cleared, ttl_seconds

    def _require_skill(self, skill_id: str) -> SkillInterfaceConfig:
        try:
            return self._registry.get_interface(skill_id)
        except ValueError as exc:
            raise SkillNotFoundError(str(exc)) from exc
