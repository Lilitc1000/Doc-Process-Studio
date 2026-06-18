"""Skill 域依赖装配。"""

from functools import lru_cache

from ..application.ports import (
    ConversationStateRepository,
    SkillContextSearcher,
    SkillRegistry,
)
from ..application.skill_service import SkillService
from .skill_repository import (
    HybridSkillContextSearcher,
    LocalSkillRegistry,
    RedisConversationStateRepository,
)


@lru_cache(maxsize=1)
def get_skill_registry() -> SkillRegistry:
    return LocalSkillRegistry()


@lru_cache(maxsize=1)
def get_skill_context_searcher() -> SkillContextSearcher:
    return HybridSkillContextSearcher()


@lru_cache(maxsize=1)
def get_conversation_state_repository() -> ConversationStateRepository:
    return RedisConversationStateRepository()


@lru_cache(maxsize=1)
def get_skill_service() -> SkillService:
    return SkillService(
        registry=get_skill_registry(),
        context_searcher=get_skill_context_searcher(),
        state_repo=get_conversation_state_repository(),
    )
