import logging
from dataclasses import dataclass
from typing import Iterable, Sequence

from ..schemas.catalog import SkillInterfaceConfig
from ..schemas.runtime import SkillPlanDecision
from ...core.config import settings
from .planner import plan_skill_activation

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SelectorOption:
    """通用选择器候选项。"""

    id: str
    display_name: str
    short_description: str = ""
    default_prompt: str = ""


def _normalize_skill_ids(raw_ids: Iterable[str] | None) -> list[str]:
    normalized: list[str] = []
    if raw_ids is None:
        return normalized
    for raw in raw_ids:
        skill_id = str(raw).strip()
        if skill_id and skill_id not in normalized:
            normalized.append(skill_id)
    return normalized


def _resolve_positive_int(value: int | None, *, fallback: int) -> int:
    if isinstance(value, int) and value > 0:
        return value
    return max(1, fallback)


def _resolve_confidence(value: float | None, *, fallback: float) -> float:
    if isinstance(value, (float, int)):
        return max(0.0, min(1.0, float(value)))
    return max(0.0, min(1.0, fallback))


def build_selector_skill_interfaces(
    *,
    options: Iterable[SelectorOption],
    skill_type: str,
) -> list[SkillInterfaceConfig]:
    interfaces: list[SkillInterfaceConfig] = []
    seen_ids: set[str] = set()
    for option in options:
        option_id = str(option.id).strip()
        if not option_id:
            continue
        if option_id in seen_ids:
            continue
        seen_ids.add(option_id)
        display_name = str(option.display_name).strip() or option_id
        short_description = str(option.short_description).strip() or display_name
        default_prompt = str(option.default_prompt).strip() or short_description
        interfaces.append(
            SkillInterfaceConfig(
                id=option_id,
                display_name=display_name,
                skill_type=skill_type,
                short_description=short_description,
                default_prompt=default_prompt,
                tools=[],
            )
        )
    return interfaces


async def select_skills_with_planner(
    *,
    model: str,
    messages: Sequence[object],
    available_skills: list[SkillInterfaceConfig],
    explicit_skill_ids: list[str] | None,
    missing_explicit_skill_ids: list[str] | None,
    system_skill_id: str,
    max_implicit_skills: int | None = None,
    top_k_candidates: int | None = None,
    min_confidence: float | None = None,
) -> SkillPlanDecision:
    return await plan_skill_activation(
        model=model,
        messages=messages,
        available_skills=available_skills,
        explicit_skill_ids=_normalize_skill_ids(explicit_skill_ids),
        missing_explicit_skill_ids=_normalize_skill_ids(missing_explicit_skill_ids),
        system_skill_id=system_skill_id,
        max_implicit_skills=_resolve_positive_int(
            max_implicit_skills,
            fallback=settings.skill_planner_max_implicit_skills,
        ),
        top_k_candidates=_resolve_positive_int(
            top_k_candidates,
            fallback=settings.skill_planner_top_k_candidates,
        ),
        min_confidence=_resolve_confidence(
            min_confidence,
            fallback=settings.skill_planner_min_confidence,
        ),
    )


async def select_for_chat_skills(
    *,
    model: str,
    messages: Sequence[object],
    available_skills: list[SkillInterfaceConfig],
    explicit_skill_ids: list[str] | None,
    missing_explicit_skill_ids: list[str] | None,
    system_skill_id: str,
) -> SkillPlanDecision:
    """聊天工作区模板：使用全局 planner 参数。"""

    return await select_skills_with_planner(
        model=model,
        messages=messages,
        available_skills=available_skills,
        explicit_skill_ids=explicit_skill_ids,
        missing_explicit_skill_ids=missing_explicit_skill_ids,
        system_skill_id=system_skill_id,
        max_implicit_skills=settings.skill_planner_max_implicit_skills,
        top_k_candidates=settings.skill_planner_top_k_candidates,
        min_confidence=settings.skill_planner_min_confidence,
    )


def _resolve_workspace_reference_top_k(available_count: int) -> int:
    if available_count <= 0:
        return 4
    return max(4, min(12, available_count))


async def select_for_workspace_reference(
    *,
    model: str,
    messages: Sequence[object],
    available_skills: list[SkillInterfaceConfig],
    explicit_skill_ids: list[str] | None,
    system_skill_id: str,
    reference_select_limit: int,
    min_confidence: float = 0.2,
) -> SkillPlanDecision:
    """工作区参考模板：偏保守、低阈值，优先挑最小必要 reference。"""

    normalized_explicit = _normalize_skill_ids(explicit_skill_ids)
    implicit_budget = max(1, reference_select_limit - len(normalized_explicit))
    return await select_skills_with_planner(
        model=model,
        messages=messages,
        available_skills=available_skills,
        explicit_skill_ids=normalized_explicit,
        missing_explicit_skill_ids=[],
        system_skill_id=system_skill_id,
        max_implicit_skills=implicit_budget,
        top_k_candidates=_resolve_workspace_reference_top_k(len(available_skills)),
        min_confidence=min_confidence,
    )
