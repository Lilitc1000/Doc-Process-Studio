from datetime import UTC, datetime

from doc_process_studio.chat.schemas.request import ChatMessageInput, ChatStreamRequest
from doc_process_studio.skill.schemas.catalog import SkillInterfaceConfig
from doc_process_studio.skill.schemas.runtime import SkillPlanDecision
import doc_process_studio.chat.service.stream as chat_stream_module


def _build_skill(
    *,
    skill_id: str,
    skill_type: str,
) -> SkillInterfaceConfig:
    return SkillInterfaceConfig(
        id=skill_id,
        display_name=skill_id,
        skill_type=skill_type,
        short_description="",
        default_prompt=f"${skill_id}",
        tools=[],
    )


async def test_resolve_skill_plan_filters_non_chat_skill_types(monkeypatch) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        chat_stream_module,
        "list_skill_interfaces",
        lambda: [
            _build_skill(skill_id="document-assistant", skill_type="chat"),
            _build_skill(skill_id="project-architecture-docx", skill_type="chat"),
            _build_skill(skill_id="incident-report", skill_type="workspace_incident"),
        ],
    )

    async def fake_select_for_chat_skills(**kwargs):
        captured["available_skill_ids"] = [skill.id for skill in kwargs["available_skills"]]
        captured["explicit_skill_ids"] = kwargs["explicit_skill_ids"]
        captured["missing_explicit_skill_ids"] = kwargs["missing_explicit_skill_ids"]
        return SkillPlanDecision(
            planner_model="qwen3-coder-next:latest",
            required_skill_ids=[],
            optional_skill_ids=[],
            missing_explicit_skill_ids=kwargs["missing_explicit_skill_ids"],
            active_skill_ids=["document-assistant"],
            primary_skill_id="document-assistant",
            confidence=1.0,
            reasons={},
            candidates=[],
            created_at=datetime.now(UTC),
        )

    monkeypatch.setattr(
        chat_stream_module,
        "select_for_chat_skills",
        fake_select_for_chat_skills,
    )

    request = ChatStreamRequest(
        user_message_id="user-1",
        conversation_id="conv-1",
        model="qwen3-coder-next:latest",
        selected_skill_ids=["incident-report"],
        messages=[ChatMessageInput(role="user", content="请用 $incident-report")],
    )

    await chat_stream_module._resolve_skill_plan(request)

    assert captured["available_skill_ids"] == [
        "document-assistant",
        "project-architecture-docx",
    ]
    assert captured["explicit_skill_ids"] == []
    assert captured["missing_explicit_skill_ids"] == ["incident-report"]
