from ...models.skill.interaction import SkillInteractionState
from ...settings import settings
from ..infra.redis_store import build_cache_key, delete_key, get_json, set_json


def build_interaction_state_key(conversation_id: str, skill_id: str) -> str:
    return build_cache_key("interaction", conversation_id, skill_id)


async def load_interaction_state(
    conversation_id: str,
    skill_id: str,
) -> SkillInteractionState | None:
    payload = await get_json(build_interaction_state_key(conversation_id, skill_id))
    if not isinstance(payload, dict):
        return None
    return SkillInteractionState.model_validate(payload)


async def save_interaction_state(state: SkillInteractionState) -> None:
    await set_json(
        build_interaction_state_key(state.conversation_id, state.skill_id),
        state.model_dump(mode="json"),
        ttl_seconds=settings.redis_ttl_seconds,
    )


async def clear_interaction_state(conversation_id: str, skill_id: str) -> bool:
    deleted = await delete_key(build_interaction_state_key(conversation_id, skill_id))
    return deleted > 0
