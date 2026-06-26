from datetime import UTC, datetime

import pytest

from doc_process_studio.skill.application.dtos.catalog import SkillInterfaceConfig
from doc_process_studio.skill.application.dtos.runtime import SkillPlanDecision


@pytest.fixture()
def build_skill():
    def _build_skill(
        *,
        skill_id: str = "test-skill",
        display_name: str | None = None,
        short_description: str | None = None,
        skill_type: str = "chat",
    ) -> SkillInterfaceConfig:
        return SkillInterfaceConfig(
            id=skill_id,
            display_name=display_name or skill_id,
            skill_type=skill_type,
            short_description=short_description or display_name or skill_id,
            default_prompt=short_description or display_name or skill_id,
            tools=[],
        )

    return _build_skill


@pytest.fixture()
def build_plan_decision():
    def _build_plan_decision(**overrides) -> SkillPlanDecision:
        defaults = dict(
            planner_model="qwen3-coder-next:latest",
            required_skill_ids=[],
            optional_skill_ids=[],
            missing_explicit_skill_ids=[],
            active_skill_ids=["document-assistant"],
            primary_skill_id="document-assistant",
            confidence=1.0,
            reasons={},
            candidates=[],
            created_at=datetime.now(UTC),
        )
        defaults.update(overrides)
        return SkillPlanDecision(**defaults)

    return _build_plan_decision
