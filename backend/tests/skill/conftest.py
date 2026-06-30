from typing import Any

import pytest

from doc_process_studio.skill.application.dtos.catalog import SkillInterfaceConfig


@pytest.fixture()
def build_skill() -> Any:
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
