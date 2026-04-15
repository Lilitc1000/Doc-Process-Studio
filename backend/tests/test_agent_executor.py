from datetime import UTC, datetime

import time

from doc_process_studio.models.conversation.stream import ChatMessageInput, ChatStreamRequest
from doc_process_studio.models.skill.runtime import (
    ConversationAgentState,
    SkillConversationState,
    SkillPlanDecision,
)
from doc_process_studio.services.agent.executor import (
    ExecutionBudget,
    ExecutionInput,
    ExecutorDeps,
    execute_tool_graph,
)


def _build_execution_input(
    *,
    normalized_tool_calls: list[dict],
    budget: ExecutionBudget,
) -> ExecutionInput:
    request = ChatStreamRequest(
        user_message_id="user-1",
        conversation_id="conv-1",
        model="qwen3-coder-next:latest",
        skill_id="incident-report",
        selected_skill_ids=["incident-report"],
        messages=[ChatMessageInput(role="user", content="请生成事故报告")],
        attachment_ids=[],
    )
    plan = SkillPlanDecision(
        planner_model="qwen3-coder-next:latest",
        required_skill_ids=["incident-report"],
        optional_skill_ids=[],
        missing_explicit_skill_ids=[],
        active_skill_ids=["incident-report", "document-assistant"],
        primary_skill_id="incident-report",
        confidence=0.9,
        reasons={},
        candidates=[],
        created_at=datetime.now(UTC),
    )
    state = SkillConversationState(
        conversation_id="conv-1",
        skill_id="incident-report",
        system_prompt="test",
        loaded_chunk_ids=[],
    )
    return ExecutionInput(
        request=request,
        primary_request=request,
        plan_decision=plan,
        agent_state=ConversationAgentState(
            conversation_id="conv-1",
            skills_state={"incident-report": state},
        ),
        states_by_skill={"incident-report": state},
        primary_skill_id="incident-report",
        primary_state=state,
        tooling_skill_ids=["incident-report"],
        normalized_tool_calls=normalized_tool_calls,
        executed_tool_calls={},
        budget=budget,
    )


def _build_deps(
    *,
    execute_skill_tool_call,
) -> ExecutorDeps:
    return ExecutorDeps(
        build_tool_status_start=lambda **_kwargs: {"label": "x", "message": "start"},
        build_tool_status_finish=lambda **_kwargs: {"label": "x", "message": "finish"},
        build_tool_call_signature=lambda tool_call: str(tool_call),
        get_tool_call_name=lambda tool_call: tool_call["function"]["name"],
        detect_tool_call_progress=lambda **_kwargs: True,
        execute_skill_tool_call=execute_skill_tool_call,
        execute_scoped_skill_tool_call=lambda **_kwargs: ({"ok": True}, []),
    )


def test_execute_tool_graph_converges_when_prompt_budget_exceeded() -> None:
    budget = ExecutionBudget(
        max_tool_calls=10,
        max_time_seconds=20,
        max_prompt_tokens=100,
        prompt_tokens_estimate=120,
    )
    execution_input = _build_execution_input(
        normalized_tool_calls=[
            {
                "function": {
                    "name": "search_skill_context",
                    "arguments": {"query": "事故报告模板"},
                }
            }
        ],
        budget=budget,
    )

    def fake_execute_skill_tool_call(**_kwargs):
        raise AssertionError("预算收束后不应真正执行工具。")

    import asyncio

    result = asyncio.run(
        execute_tool_graph(
            execution_input=execution_input,
            deps=_build_deps(execute_skill_tool_call=fake_execute_skill_tool_call),
        )
    )

    assert result.disable_tools is True
    assert result.state_diff.budget_converged is True
    assert result.state_diff.budget_reason is not None


def test_execute_tool_graph_retries_search_without_source_path() -> None:
    budget = ExecutionBudget(
        max_tool_calls=10,
        max_time_seconds=20,
        max_prompt_tokens=500,
        prompt_tokens_estimate=40,
    )
    execution_input = _build_execution_input(
        normalized_tool_calls=[
            {
                "function": {
                    "name": "search_skill_context",
                    "arguments": {
                        "query": "事故报告模板",
                        "source_path": "references/template.md",
                    },
                }
            }
        ],
        budget=budget,
    )

    observed_arguments: list[dict] = []

    def fake_execute_skill_tool_call(*, tool_call, **_kwargs):
        observed_arguments.append(tool_call["function"]["arguments"])
        if len(observed_arguments) == 1:
            return {"ok": False, "error": "source_path not found"}, []
        return {"ok": True, "chunks": [{"id": "c1"}]}, []

    import asyncio

    result = asyncio.run(
        execute_tool_graph(
            execution_input=execution_input,
            deps=_build_deps(execute_skill_tool_call=fake_execute_skill_tool_call),
        )
    )

    assert len(observed_arguments) == 2
    assert observed_arguments[0].get("source_path") == "references/template.md"
    assert "source_path" not in observed_arguments[1]
    assert result.round_made_progress is True


def test_execute_tool_graph_deduplicates_same_signature_tool_calls() -> None:
    budget = ExecutionBudget(
        max_tool_calls=10,
        max_time_seconds=20,
        max_prompt_tokens=500,
        prompt_tokens_estimate=40,
    )
    duplicated_tool_call = {
        "function": {
            "name": "read_skill_file",
            "arguments": {"relative_path": "SKILL.md"},
        }
    }
    execution_input = _build_execution_input(
        normalized_tool_calls=[duplicated_tool_call, duplicated_tool_call],
        budget=budget,
    )

    invoked_counter = {"value": 0}

    def fake_execute_skill_tool_call(**_kwargs):
        invoked_counter["value"] += 1
        return {"ok": True, "content": "loaded"}, []

    import asyncio

    result = asyncio.run(
        execute_tool_graph(
            execution_input=execution_input,
            deps=_build_deps(execute_skill_tool_call=fake_execute_skill_tool_call),
        )
    )

    assert invoked_counter["value"] == 1
    assert result.state_diff.reused_tool_calls >= 1


def test_execute_tool_graph_converges_when_accumulated_time_exceeded() -> None:
    budget = ExecutionBudget(
        max_tool_calls=10,
        max_time_seconds=5.0,
        max_prompt_tokens=500,
        prompt_tokens_estimate=40,
        accumulated_execution_seconds=6.0,
    )
    execution_input = _build_execution_input(
        normalized_tool_calls=[
            {
                "function": {
                    "name": "search_skill_context",
                    "arguments": {"query": "事故报告模板"},
                }
            }
        ],
        budget=budget,
    )

    def fake_execute_skill_tool_call(**_kwargs):
        raise AssertionError("时间预算超限后不应真正执行工具。")

    import asyncio

    result = asyncio.run(
        execute_tool_graph(
            execution_input=execution_input,
            deps=_build_deps(execute_skill_tool_call=fake_execute_skill_tool_call),
        )
    )

    assert result.disable_tools is True
    assert result.state_diff.budget_converged is True
    assert "时间预算" in result.state_diff.budget_reason


def test_execute_tool_graph_converges_when_round_time_exceeded() -> None:
    budget = ExecutionBudget(
        max_tool_calls=10,
        max_time_seconds=5.0,
        max_prompt_tokens=500,
        prompt_tokens_estimate=40,
        accumulated_execution_seconds=4.5,
        round_started_monotonic=time.monotonic(),
    )
    execution_input = _build_execution_input(
        normalized_tool_calls=[
            {
                "function": {
                    "name": "search_skill_context",
                    "arguments": {"query": "事故报告模板"},
                }
            }
        ],
        budget=budget,
    )

    def fake_execute_skill_tool_call(**_kwargs):
        raise AssertionError("时间预算超限后不应真正执行工具。")

    import asyncio

    time.sleep(0.6)

    result = asyncio.run(
        execute_tool_graph(
            execution_input=execution_input,
            deps=_build_deps(execute_skill_tool_call=fake_execute_skill_tool_call),
        )
    )

    assert result.disable_tools is True
    assert result.state_diff.budget_converged is True
    assert "时间预算" in result.state_diff.budget_reason
