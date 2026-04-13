from datetime import UTC, datetime

from doc_process_studio.models.skill.runtime import (
    ConversationAgentState,
    SkillConversationState,
    SkillPlanDecision,
    SkillToolHistoryRecord,
)
from doc_process_studio.services.skill import conversation_store as store_module


def test_save_conversation_state_serializes_datetime_fields(monkeypatch) -> None:
    captured: dict[str, object] = {}

    async def fake_set_json(key, payload, ttl_seconds=None):
        captured["key"] = key
        captured["payload"] = payload
        captured["ttl_seconds"] = ttl_seconds

    monkeypatch.setattr(store_module, "set_json", fake_set_json)

    now = datetime.now(UTC)
    state = ConversationAgentState(
        conversation_id="conv-1",
        skills_state={
            "document-assistant": SkillConversationState(
                conversation_id="conv-1",
                skill_id="document-assistant",
                system_prompt="test",
                loaded_chunk_ids=[],
            )
        },
        planner_trace=[
            SkillPlanDecision(
                planner_model="qwen3-coder-next:latest",
                required_skill_ids=[],
                optional_skill_ids=[],
                missing_explicit_skill_ids=[],
                active_skill_ids=["document-assistant"],
                primary_skill_id="document-assistant",
                confidence=0.9,
                reasons={},
                candidates=[],
                created_at=now,
            )
        ],
        tool_history=[
            SkillToolHistoryRecord(
                skill_id="document-assistant",
                tool_name="read_skill_file",
                ok=True,
                reused=False,
                attachment_count=0,
                created_at=now,
            )
        ],
    )

    import asyncio

    asyncio.run(store_module.save_conversation_state(state))

    payload = captured["payload"]
    assert isinstance(payload, dict)
    planner_trace = payload.get("planner_trace")
    assert isinstance(planner_trace, list) and planner_trace
    assert isinstance(planner_trace[0].get("created_at"), str)
    tool_history = payload.get("tool_history")
    assert isinstance(tool_history, list) and tool_history
    assert isinstance(tool_history[0].get("created_at"), str)


def test_skill_conversation_state_model_can_read_old_snapshot_payload() -> None:
    legacy_payload = {
        "conversation_id": "conv-legacy",
        "skill_id": "document-assistant",
        "system_prompt": "legacy",
        "loaded_chunk_ids": ["chunk-1"],
        "compact_summary": "旧版本摘要字段",
        "compacted_chunk_ids": ["chunk-1"],
    }
    parsed = SkillConversationState.model_validate(legacy_payload)
    assert parsed.short_term_memory == ""
    assert parsed.episodic_memory == ""
    assert parsed.skill_memory == ""
    assert parsed.compacted_chunk_ids == ["chunk-1"]
