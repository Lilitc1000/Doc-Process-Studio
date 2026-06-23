from datetime import UTC, datetime

from doc_process_studio.chat.schemas.request import ChatMessageInput
from doc_process_studio.skill.schemas.runtime import SkillPlanDecision
from doc_process_studio.skill.service import selector as selector_module
from doc_process_studio.skill.service.selector import (
    SelectorOption,
    build_selector_skill_interfaces,
    select_for_chat_skills,
    select_for_workspace_reference,
    select_skills_with_planner,
)
from doc_process_studio.core.config import settings


def test_build_selector_skill_interfaces_dedupes_and_fallbacks() -> None:
    interfaces = build_selector_skill_interfaces(
        options=[
            SelectorOption(id="  ", display_name="empty"),
            SelectorOption(id="body-sections/common.md", display_name="", short_description="", default_prompt=""),
            SelectorOption(
                id="body-sections/impact.md",
                display_name="影响范围",
                short_description="影响范围与严重级别",
                default_prompt="impact ref",
            ),
            SelectorOption(id="body-sections/common.md", display_name="重复"),
        ],
        skill_type="workspace_incident_reference",
    )

    assert [item.id for item in interfaces] == [
        "body-sections/common.md",
        "body-sections/impact.md",
    ]
    assert interfaces[0].display_name == "body-sections/common.md"
    assert interfaces[0].short_description == "body-sections/common.md"
    assert interfaces[0].default_prompt == "body-sections/common.md"
    assert interfaces[1].display_name == "影响范围"
    assert interfaces[1].short_description == "影响范围与严重级别"
    assert interfaces[1].default_prompt == "impact ref"


async def test_select_skills_with_planner_uses_defaults_and_normalization(monkeypatch, build_skill) -> None:
    captured: dict[str, object] = {}

    async def fake_plan_skill_activation(**kwargs):
        captured.update(kwargs)
        return SkillPlanDecision(
            planner_model=kwargs["model"],
            required_skill_ids=kwargs["explicit_skill_ids"],
            optional_skill_ids=[],
            missing_explicit_skill_ids=kwargs["missing_explicit_skill_ids"],
            active_skill_ids=[kwargs["system_skill_id"]],
            primary_skill_id=kwargs["system_skill_id"],
            confidence=kwargs["min_confidence"],
            reasons={},
            candidates=[],
            created_at=datetime.now(UTC),
        )

    monkeypatch.setattr(
        selector_module,
        "plan_skill_activation",
        fake_plan_skill_activation,
    )

    decision = await select_skills_with_planner(
        model="qwen3-coder-next:latest",
        messages=[ChatMessageInput(role="user", content="测试选择器")],
        available_skills=[build_skill(skill_id="document-assistant")],
        explicit_skill_ids=["document-assistant", " document-assistant ", ""],
        missing_explicit_skill_ids=["unknown-skill", "unknown-skill"],
        system_skill_id="document-assistant",
        max_implicit_skills=0,
        top_k_candidates=None,
        min_confidence=1.2,
    )

    assert captured["explicit_skill_ids"] == ["document-assistant"]
    assert captured["missing_explicit_skill_ids"] == ["unknown-skill"]
    assert captured["max_implicit_skills"] == max(1, settings.skill_planner_max_implicit_skills)
    assert captured["top_k_candidates"] == max(1, settings.skill_planner_top_k_candidates)
    assert captured["min_confidence"] == 1.0
    assert decision.primary_skill_id == "document-assistant"
    assert decision.required_skill_ids == ["document-assistant"]


async def test_select_for_chat_skills_uses_chat_template_defaults(monkeypatch, build_skill) -> None:
    captured: dict[str, object] = {}

    async def fake_select_skills_with_planner(**kwargs):
        captured.update(kwargs)
        return SkillPlanDecision(
            planner_model=kwargs["model"],
            required_skill_ids=[],
            optional_skill_ids=[],
            missing_explicit_skill_ids=[],
            active_skill_ids=[kwargs["system_skill_id"]],
            primary_skill_id=kwargs["system_skill_id"],
            confidence=1.0,
            reasons={},
            candidates=[],
            created_at=datetime.now(UTC),
        )

    monkeypatch.setattr(
        selector_module,
        "select_skills_with_planner",
        fake_select_skills_with_planner,
    )

    decision = await select_for_chat_skills(
        model="qwen3-coder-next:latest",
        messages=[ChatMessageInput(role="user", content="测试 chat 模板")],
        available_skills=[build_skill(skill_id="document-assistant")],
        explicit_skill_ids=["document-assistant"],
        missing_explicit_skill_ids=["missing-skill"],
        system_skill_id="document-assistant",
    )

    assert captured["max_implicit_skills"] == settings.skill_planner_max_implicit_skills
    assert captured["top_k_candidates"] == settings.skill_planner_top_k_candidates
    assert captured["min_confidence"] == settings.skill_planner_min_confidence
    assert decision.primary_skill_id == "document-assistant"


async def test_select_for_workspace_reference_uses_reference_template_defaults(monkeypatch, build_skill) -> None:
    captured: dict[str, object] = {}

    async def fake_select_skills_with_planner(**kwargs):
        captured.update(kwargs)
        return SkillPlanDecision(
            planner_model=kwargs["model"],
            required_skill_ids=[],
            optional_skill_ids=[],
            missing_explicit_skill_ids=[],
            active_skill_ids=[kwargs["system_skill_id"]],
            primary_skill_id=kwargs["system_skill_id"],
            confidence=kwargs["min_confidence"],
            reasons={},
            candidates=[],
            created_at=datetime.now(UTC),
        )

    monkeypatch.setattr(
        selector_module,
        "select_skills_with_planner",
        fake_select_skills_with_planner,
    )

    decision = await select_for_workspace_reference(
        model="qwen3-coder-next:latest",
        messages=[ChatMessageInput(role="user", content="测试 workspace 模板")],
        available_skills=[
            build_skill(skill_id="body-sections/common.md"),
            build_skill(skill_id="body-sections/impact.md"),
            build_skill(skill_id="body-sections/timeline.md"),
        ],
        explicit_skill_ids=["body-sections/common.md"],
        system_skill_id="__incident_reference_system__",
        reference_select_limit=4,
    )

    assert captured["missing_explicit_skill_ids"] == []
    assert captured["max_implicit_skills"] == 3
    assert captured["top_k_candidates"] == 4
    assert captured["min_confidence"] == 0.2
    assert decision.primary_skill_id == "__incident_reference_system__"
