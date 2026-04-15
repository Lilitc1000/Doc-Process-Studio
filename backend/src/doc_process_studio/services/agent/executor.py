import asyncio
import inspect
import json
import time
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Callable, Literal

from ...models.conversation.stream import ChatStreamRequest
from ...services.infra.tool_args import parse_tool_arguments
from ...models.skill.runtime import (
    ConversationAgentState,
    SkillConversationState,
    SkillPlanDecision,
    SkillToolHistoryRecord,
)
from ...settings import settings

TaskNodeType = Literal["read", "search", "load", "declare_tool"]


@dataclass
class ExecutionBudget:
    max_tool_calls: int
    max_time_seconds: float
    max_prompt_tokens: int
    prompt_tokens_estimate: int
    used_tool_calls: int = 0
    accumulated_execution_seconds: float = 0.0
    round_started_monotonic: float = 0.0


@dataclass
class ExecutionStateDiff:
    loaded_chunk_ids_added: dict[str, list[str]] = field(default_factory=dict)
    tool_history_added: int = 0
    attachment_count_added: int = 0
    reused_tool_calls: int = 0
    budget_converged: bool = False
    budget_reason: str | None = None


@dataclass
class ExecutionResult:
    status_events: list[dict[str, Any]] = field(default_factory=list)
    tool_trace_messages: list[dict[str, Any]] = field(default_factory=list)
    attachments: list[Any] = field(default_factory=list)
    assistant_deltas: list[str] = field(default_factory=list)
    error_message: str | None = None
    round_made_progress: bool = False
    disable_tools: bool = False
    executed_tool_calls: dict[str, dict[str, Any]] = field(default_factory=dict)
    state_diff: ExecutionStateDiff = field(default_factory=ExecutionStateDiff)
    tool_calls_consumed: int = 0


@dataclass
class ExecutionInput:
    request: ChatStreamRequest
    primary_request: ChatStreamRequest
    plan_decision: SkillPlanDecision
    agent_state: ConversationAgentState
    states_by_skill: dict[str, SkillConversationState]
    primary_skill_id: str
    primary_state: SkillConversationState
    tooling_skill_ids: list[str]
    normalized_tool_calls: list[dict[str, Any]]
    executed_tool_calls: dict[str, dict[str, Any]]
    budget: ExecutionBudget


@dataclass
class ExecutorDeps:
    build_tool_status_start: Callable[..., dict[str, str]]
    build_tool_status_finish: Callable[..., dict[str, str]]
    build_tool_call_signature: Callable[[dict[str, Any]], str]
    get_tool_call_name: Callable[[dict[str, Any]], str]
    detect_tool_call_progress: Callable[..., bool]
    execute_skill_tool_call: Callable[..., tuple[dict[str, Any], list[Any]]]
    execute_scoped_skill_tool_call: Callable[..., tuple[dict[str, Any], list[Any]]]


@dataclass
class _TaskNode:
    index: int
    tool_call: dict[str, Any]
    tool_name: str
    base_tool_name: str
    skill_id: str
    node_type: TaskNodeType
    dependencies: set[int] = field(default_factory=set)


def _resolve_tool_scope(
    *,
    default_skill_id: str,
    tool_call: dict[str, Any],
    tool_name: str,
) -> tuple[str, str]:
    normalized_tool_name = tool_name.strip()
    if "::" in normalized_tool_name:
        scoped_skill_id, base_tool_name = normalized_tool_name.split("::", 1)
        scoped_skill_id = scoped_skill_id.strip()
        base_tool_name = base_tool_name.strip()
        if scoped_skill_id and base_tool_name:
            return scoped_skill_id, base_tool_name

    arguments = parse_tool_arguments(tool_call)
    scoped_skill_id = str(arguments.get("skill_id", "")).strip()
    if scoped_skill_id:
        return scoped_skill_id, normalized_tool_name
    return default_skill_id, normalized_tool_name


def _classify_node_type(base_tool_name: str) -> TaskNodeType:
    if base_tool_name in {"list_skill_directory", "read_skill_file"}:
        return "read"
    if base_tool_name == "search_skill_context":
        return "search"
    if base_tool_name == "read_skill_context":
        return "load"
    return "declare_tool"


def _build_task_graph(
    *,
    tool_calls: list[dict[str, Any]],
    default_skill_id: str,
    get_tool_call_name: Callable[[dict[str, Any]], str],
) -> list[_TaskNode]:
    nodes: list[_TaskNode] = []
    collect_steps_by_skill: dict[str, list[int]] = {}
    latest_search_or_read_by_skill: dict[str, int] = {}

    for index, tool_call in enumerate(tool_calls):
        tool_name = get_tool_call_name(tool_call)
        skill_id, base_tool_name = _resolve_tool_scope(
            default_skill_id=default_skill_id,
            tool_call=tool_call,
            tool_name=tool_name,
        )
        node_type = _classify_node_type(base_tool_name)
        dependencies: set[int] = set()

        if node_type == "load":
            previous_collect = latest_search_or_read_by_skill.get(skill_id)
            if previous_collect is not None:
                dependencies.add(previous_collect)
            collect_steps_by_skill.setdefault(skill_id, []).append(index)
        elif node_type == "declare_tool":
            dependencies.update(collect_steps_by_skill.get(skill_id, []))
        elif node_type in {"read", "search"}:
            latest_search_or_read_by_skill[skill_id] = index
            collect_steps_by_skill.setdefault(skill_id, []).append(index)

        nodes.append(
            _TaskNode(
                index=index,
                tool_call=tool_call,
                tool_name=tool_name,
                base_tool_name=base_tool_name,
                skill_id=skill_id,
                node_type=node_type,
                dependencies=dependencies,
            )
        )

    return nodes


def _collect_loaded_chunk_signatures(
    states_by_skill: dict[str, SkillConversationState],
) -> set[str]:
    signatures: set[str] = set()
    for skill_id, state in states_by_skill.items():
        for chunk_id in state.loaded_chunk_ids:
            signatures.add(f"{skill_id}::{chunk_id}")
    return signatures


def _append_tool_history(
    *,
    agent_state: ConversationAgentState,
    record: SkillToolHistoryRecord,
) -> None:
    agent_state.tool_history.append(record)
    max_entries = max(1, settings.skill_tool_history_max_entries)
    if len(agent_state.tool_history) > max_entries:
        agent_state.tool_history = agent_state.tool_history[-max_entries:]


def _copy_tool_call_with_arguments(
    tool_call: dict[str, Any],
    arguments: dict[str, Any],
) -> dict[str, Any]:
    function_payload = tool_call.get("function")
    copied = {
        "id": tool_call.get("id"),
        "type": tool_call.get("type"),
        "function": {
            "name": "",
            "arguments": arguments,
        },
    }
    if isinstance(function_payload, dict):
        copied["function"]["name"] = str(function_payload.get("name", "")).strip()
    return copied


def _build_retry_fallback_tool_call(
    *,
    node: _TaskNode,
    tool_call: dict[str, Any],
) -> tuple[dict[str, Any], str] | None:
    arguments = parse_tool_arguments(tool_call)

    if node.base_tool_name == "search_skill_context":
        source_path = str(arguments.get("source_path", "")).strip()
        if source_path:
            updated = {
                key: value for key, value in arguments.items() if key != "source_path"
            }
            return (
                _copy_tool_call_with_arguments(tool_call, updated),
                "检索失败，已自动移除 source_path 限制后重试。",
            )

    if node.base_tool_name == "list_skill_directory":
        relative_path = str(arguments.get("relative_path", "")).strip()
        if relative_path:
            updated = dict(arguments)
            updated["relative_path"] = ""
            return (
                _copy_tool_call_with_arguments(tool_call, updated),
                "目录读取失败，已自动回退到根目录重试。",
            )

    return None


def _is_tool_success(tool_result: dict[str, Any]) -> bool:
    return bool(tool_result.get("ok"))


async def _invoke_callable(
    callable_object: Callable[..., Any],
    **kwargs: Any,
) -> Any:
    if inspect.iscoroutinefunction(callable_object):
        return await callable_object(**kwargs)
    return await asyncio.to_thread(callable_object, **kwargs)


async def _run_tool_with_retry(
    *,
    node: _TaskNode,
    execution_input: ExecutionInput,
    deps: ExecutorDeps,
) -> tuple[dict[str, Any], list[Any], dict[str, Any], str | None]:
    max_attempts = max(1, settings.agent_executor_tool_retry_max_attempts)
    base_delay = max(0.05, settings.agent_executor_tool_retry_base_delay_seconds)

    current_tool_call = node.tool_call
    fallback_note: str | None = None
    last_result: tuple[dict[str, Any], list[Any]] = (
        {"ok": False, "error": "工具执行失败。"},
        [],
    )

    for attempt_index in range(max_attempts):
        execution_input.budget.used_tool_calls += 1

        if len(execution_input.tooling_skill_ids) == 1:
            single_skill_id = execution_input.tooling_skill_ids[0]
            scoped_request = execution_input.request.model_copy(
                update={"skill_id": single_skill_id}
            )
            last_result = await _invoke_callable(
                deps.execute_skill_tool_call,
                request=scoped_request,
                state=execution_input.states_by_skill[single_skill_id],
                tool_call=current_tool_call,
            )
        else:
            last_result = await _invoke_callable(
                deps.execute_scoped_skill_tool_call,
                request=execution_input.request,
                states_by_skill=execution_input.states_by_skill,
                default_skill_id=execution_input.primary_skill_id,
                tool_call=current_tool_call,
            )

        tool_result, next_attachments = last_result
        if _is_tool_success(tool_result):
            return tool_result, next_attachments, current_tool_call, fallback_note

        if attempt_index >= max_attempts - 1:
            break

        fallback = _build_retry_fallback_tool_call(
            node=node,
            tool_call=current_tool_call,
        )
        if fallback is not None:
            current_tool_call, fallback_note = fallback

        await asyncio.sleep(base_delay * (2**attempt_index))

    tool_result, next_attachments = last_result
    return tool_result, next_attachments, current_tool_call, fallback_note


def _is_execution_time_exceeded(budget: ExecutionBudget) -> bool:
    if budget.round_started_monotonic <= 0:
        return budget.accumulated_execution_seconds >= budget.max_time_seconds
    current_round_elapsed = time.monotonic() - budget.round_started_monotonic
    return (budget.accumulated_execution_seconds + current_round_elapsed) >= budget.max_time_seconds


def _build_budget_converged_result(reason: str) -> ExecutionResult:
    result = ExecutionResult(
        disable_tools=True,
    )
    result.state_diff.budget_converged = True
    result.state_diff.budget_reason = reason
    result.tool_trace_messages.append(
        {
            "role": "system",
            "content": (
                f"{reason} 请基于已经读取到的内容直接完成回答，不要继续调用工具。"
            ),
        }
    )
    return result


def _build_loaded_chunk_diff(
    *,
    before_states: dict[str, set[str]],
    after_states: dict[str, SkillConversationState],
) -> dict[str, list[str]]:
    diff: dict[str, list[str]] = {}
    for skill_id, state in after_states.items():
        before_chunk_ids = before_states.get(skill_id, set())
        added = [chunk_id for chunk_id in state.loaded_chunk_ids if chunk_id not in before_chunk_ids]
        if added:
            diff[skill_id] = added
    return diff


async def _execute_single_node(
    *,
    node: _TaskNode,
    execution_input: ExecutionInput,
    deps: ExecutorDeps,
    result: ExecutionResult,
    inflight_tool_calls: dict[str, asyncio.Task[tuple[dict[str, Any], list[Any], dict[str, Any], bool, str | None]]],
    inflight_lock: asyncio.Lock,
    semaphore: asyncio.Semaphore,
) -> tuple[_TaskNode, dict[str, Any], list[Any], dict[str, Any], bool, str | None]:
    tool_call = node.tool_call
    result.status_events.append(
        {
            "type": "tool-status",
            "phase": "start",
            "tool_name": node.tool_name,
            **deps.build_tool_status_start(
                skill_id=execution_input.primary_skill_id,
                tool_call=tool_call,
            ),
        }
    )

    tool_call_signature = deps.build_tool_call_signature(tool_call)
    if tool_call_signature in result.executed_tool_calls:
        cached_execution = result.executed_tool_calls[tool_call_signature]
        tool_result = deepcopy(cached_execution["tool_result"])
        tool_result["reused"] = True
        return node, tool_result, [], tool_call, False, None
    existing_task = None
    task_owned_by_current_node = False
    async with inflight_lock:
        existing_task = inflight_tool_calls.get(tool_call_signature)
        if existing_task is None:
            task_owned_by_current_node = True

            async def _execute_once():
                async with semaphore:
                    before_loaded_chunk_ids = _collect_loaded_chunk_signatures(
                        execution_input.states_by_skill
                    )
                    (
                        local_tool_result,
                        local_attachments,
                        local_resolved_tool_call,
                        local_fallback_note,
                    ) = await _run_tool_with_retry(
                        node=node,
                        execution_input=execution_input,
                        deps=deps,
                    )
                    after_loaded_chunk_ids = _collect_loaded_chunk_signatures(
                        execution_input.states_by_skill
                    )

                local_made_progress = deps.detect_tool_call_progress(
                    tool_name=node.tool_name,
                    before_loaded_chunk_ids=before_loaded_chunk_ids,
                    after_loaded_chunk_ids=after_loaded_chunk_ids,
                    tool_result=local_tool_result,
                    next_attachments=local_attachments,
                )
                return (
                    local_tool_result,
                    local_attachments,
                    local_resolved_tool_call,
                    local_made_progress,
                    local_fallback_note,
                )

            existing_task = asyncio.create_task(_execute_once())
            inflight_tool_calls[tool_call_signature] = existing_task

    assert existing_task is not None
    try:
        tool_result, attachments, resolved_tool_call, made_progress, fallback_note = await existing_task
    finally:
        if task_owned_by_current_node:
            async with inflight_lock:
                inflight_tool_calls.pop(tool_call_signature, None)

    if task_owned_by_current_node:
        result.executed_tool_calls[tool_call_signature] = {
            "tool_result": deepcopy(tool_result),
        }
        return (
            node,
            tool_result,
            attachments,
            resolved_tool_call,
            made_progress,
            fallback_note,
        )

    reused_tool_result = deepcopy(tool_result)
    reused_tool_result["reused"] = True
    return node, reused_tool_result, [], resolved_tool_call, False, None


def _collect_outcome(
    *,
    node: _TaskNode,
    tool_result: dict[str, Any],
    attachments: list[Any],
    resolved_tool_call: dict[str, Any],
    made_progress: bool,
    fallback_note: str | None,
    execution_input: ExecutionInput,
    deps: ExecutorDeps,
    result: ExecutionResult,
) -> None:
    result.tool_calls_consumed += 1
    if attachments:
        for attachment in attachments:
            result.attachments.append(attachment)
            result.status_events.append(
                {
                    "type": "attachment",
                    "attachment": attachment.model_dump(
                        mode="json",
                    ),
                }
            )
            result.state_diff.attachment_count_added += 1

    if tool_result.get("reused"):
        result.state_diff.reused_tool_calls += 1

    if made_progress or attachments:
        result.round_made_progress = True

    if fallback_note:
        tool_result = dict(tool_result)
        tool_result["fallback"] = fallback_note

    result.status_events.append(
        {
            "type": "tool-status",
            "phase": "finish",
            "tool_name": node.tool_name,
            **deps.build_tool_status_finish(
                request=execution_input.primary_request,
                state=execution_input.primary_state,
                tool_call=resolved_tool_call,
                tool_result=tool_result,
                attachments=attachments,
            ),
        }
    )

    result.tool_trace_messages.append(
        {
            "role": "tool",
            "name": node.tool_name,
            "content": json.dumps(tool_result, ensure_ascii=False),
        }
    )

    _append_tool_history(
        agent_state=execution_input.agent_state,
        record=SkillToolHistoryRecord(
            skill_id=node.skill_id,
            tool_name=node.base_tool_name,
            ok=bool(tool_result.get("ok")),
            reused=bool(tool_result.get("reused")),
            attachment_count=len(attachments),
            error=(
                str(tool_result.get("error"))
                if not tool_result.get("ok") and tool_result.get("error") is not None
                else None
            ),
            created_at=datetime.now(UTC),
        ),
    )
    result.state_diff.tool_history_added += 1


async def execute_tool_graph(
    *,
    execution_input: ExecutionInput,
    deps: ExecutorDeps,
) -> ExecutionResult:
    budget = execution_input.budget
    if (
        budget.max_prompt_tokens > 0
        and budget.prompt_tokens_estimate >= budget.max_prompt_tokens
    ):
        return _build_budget_converged_result(
            (
                "当前会话上下文已接近模型可用窗口上限，"
                f"估算 token={budget.prompt_tokens_estimate}，预算={budget.max_prompt_tokens}。"
            )
        )

    if _is_execution_time_exceeded(budget):
        return _build_budget_converged_result("本次工具执行已达到时间预算上限。")

    if budget.used_tool_calls >= budget.max_tool_calls:
        return _build_budget_converged_result("本次工具执行已达到调用次数预算上限。")

    before_loaded_states = {
        skill_id: set(state.loaded_chunk_ids)
        for skill_id, state in execution_input.states_by_skill.items()
    }
    result = ExecutionResult(executed_tool_calls=execution_input.executed_tool_calls)
    inflight_tool_calls: dict[
        str,
        asyncio.Task[tuple[dict[str, Any], list[Any], dict[str, Any], bool, str | None]],
    ] = {}
    inflight_lock = asyncio.Lock()
    nodes = _build_task_graph(
        tool_calls=execution_input.normalized_tool_calls,
        default_skill_id=execution_input.primary_skill_id,
        get_tool_call_name=deps.get_tool_call_name,
    )

    pending_by_index: dict[int, _TaskNode] = {node.index: node for node in nodes}
    completed_indexes: set[int] = set()
    semaphore = asyncio.Semaphore(max(1, settings.agent_executor_max_parallel_reads))

    while pending_by_index:
        if _is_execution_time_exceeded(budget):
            return _build_budget_converged_result("本次工具执行已达到时间预算上限。")
        if budget.used_tool_calls >= budget.max_tool_calls:
            return _build_budget_converged_result("本次工具执行已达到调用次数预算上限。")

        ready_nodes = [
            node
            for node in pending_by_index.values()
            if node.dependencies.issubset(completed_indexes)
        ]
        if not ready_nodes:
            fallback_index = min(pending_by_index.keys())
            ready_nodes = [pending_by_index[fallback_index]]

        parallel_ready_nodes = sorted(
            [node for node in ready_nodes if node.node_type in {"read", "search"}],
            key=lambda node: node.index,
        )
        serial_ready_nodes = sorted(
            [node for node in ready_nodes if node.node_type not in {"read", "search"}],
            key=lambda node: node.index,
        )

        parallel_outcomes: list[tuple[_TaskNode, dict[str, Any], list[Any], dict[str, Any], bool, str | None]] = []
        if parallel_ready_nodes:
            gathered = await asyncio.gather(
                *[_execute_single_node(
                    node=node,
                    execution_input=execution_input,
                    deps=deps,
                    result=result,
                    inflight_tool_calls=inflight_tool_calls,
                    inflight_lock=inflight_lock,
                    semaphore=semaphore,
                ) for node in parallel_ready_nodes]
            )
            parallel_outcomes.extend(gathered)

        serial_outcomes: list[tuple[_TaskNode, dict[str, Any], list[Any], dict[str, Any], bool, str | None]] = []
        for node in serial_ready_nodes:
            serial_outcomes.append(await _execute_single_node(
                node=node,
                execution_input=execution_input,
                deps=deps,
                result=result,
                inflight_tool_calls=inflight_tool_calls,
                inflight_lock=inflight_lock,
                semaphore=semaphore,
            ))

        outcomes = sorted(
            [*parallel_outcomes, *serial_outcomes],
            key=lambda item: item[0].index,
        )

        for node, tool_result, attachments, resolved_tool_call, made_progress, fallback_note in outcomes:
            _collect_outcome(
                node=node,
                tool_result=tool_result,
                attachments=attachments,
                resolved_tool_call=resolved_tool_call,
                made_progress=made_progress,
                fallback_note=fallback_note,
                execution_input=execution_input,
                deps=deps,
                result=result,
            )
            completed_indexes.add(node.index)
            pending_by_index.pop(node.index, None)

    result.state_diff.loaded_chunk_ids_added = _build_loaded_chunk_diff(
        before_states=before_loaded_states,
        after_states=execution_input.states_by_skill,
    )

    if not result.round_made_progress:
        result.disable_tools = True
        result.tool_trace_messages.append(
            {
                "role": "system",
                "content": (
                    "本轮工具调用没有获得新的信息，或者只是重复读取。"
                    "请基于已经读取到的技能说明、参考资料和工具结果直接完成回答，"
                    "不要继续重复调用相同工具。"
                ),
            }
        )

    return result
