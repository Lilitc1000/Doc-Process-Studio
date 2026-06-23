import json
import logging
import re
import time
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import UploadFile

from ...core.config import settings
from ...core.model_context import estimate_prompt_tokens, get_model_context_length
from ...core.ollama import OllamaNotConfiguredError, stream_chat_completion
from ...core.request_guard import RequestGuardError, guard_request_slot
from ...shared.dtutils import to_utc8
from ...shared.error_utils import build_error_event_detail
from ...shared.tool_args import build_normalized_tool_calls
from ...skill.schemas.catalog import SkillInterfaceConfig
from ...skill.schemas.runtime import (
    ConversationAgentState,
    SkillConversationState,
    SkillPlanDecision,
)
from ...skill.service.conversation_store import load_conversation_state, save_conversation_state
from ...skill.service.registry import (
    get_skill_interface,
    list_skill_interfaces,
)
from ...skill.service.runtime import sync_skill_context_state
from ...skill.service.selector import select_for_chat_skills
from ...skill.service.tool_loop import (
    build_skill_tools,
    build_skill_tools_for_skills,
    build_tool_status_finish,
    build_tool_status_start,
    execute_scoped_skill_tool_call,
    execute_skill_tool_call,
)
from ...system.service.error_detail import summarize_exception
from ...system.service.executor import (
    ExecutionBudget,
    ExecutionInput,
    ExecutorDeps,
    execute_tool_graph,
)
from ...system.service.feature_flags import is_feature_enabled_for_key
from ...system.service.trace_store import AgentTraceRecorder
from ..schemas.file_context import PreparedUploadedFile
from ..schemas.request import ChatMessageInput, ChatStreamRequest
from .file_context import build_persisted_uploaded_files_context, prepare_uploaded_files
from .streaming import (
    build_ollama_assistant_chunk,
    build_ollama_done_chunk,
    build_tool_call_signature,
    build_upstream_messages_for_skills,
    detect_tool_call_progress,
    extract_delta_text,
    extract_delta_tool_calls,
    extract_done_reason,
    format_sse_event,
    get_tool_call_name,
    merge_stream_tool_calls,
    merge_uploaded_files_context,
)
from .streaming.context import (
    build_kb_skill_interface,
    extract_kb_project_name,
    is_kb_skill_id,
)

logger = logging.getLogger(__name__)

SYSTEM_DOCUMENT_SKILL_ID = "document-assistant"
CHAT_SKILL_TYPE = "chat"


def _list_chat_skill_interfaces() -> list[Any]:
    base_skills = [
        skill
        for skill in list_skill_interfaces()
        if str(getattr(skill, "skill_type", CHAT_SKILL_TYPE)).strip() == CHAT_SKILL_TYPE
    ]
    return base_skills


_KB_PRESCAN_PATTERN = re.compile(r"\$kb:([A-Za-z0-9._\u4e00-\u9fff-]+)")


def _register_kb_skills_from_messages(
    messages: Any,
    initial_kb_ids: list[str],
    available_skills: list[Any],
    available_skill_ids: set[str] | list[str],
) -> list[str]:
    """Pre-scan messages for $kb:xxx mentions and register KB skills.

    Returns the full list of KB skill IDs (initial + discovered from messages).
    """
    kb_skill_ids = list(initial_kb_ids)

    for message in messages:
        if getattr(message, "role", None) != "user":
            continue
        content = str(getattr(message, "content", "") or "")
        for project_name in _KB_PRESCAN_PATTERN.findall(content):
            kb_sid = f"kb:{project_name}"
            if kb_sid not in kb_skill_ids:
                kb_skill_ids.append(kb_sid)

    for kb_sid in kb_skill_ids:
        project_name = extract_kb_project_name(kb_sid)
        if project_name and kb_sid not in available_skill_ids:
            kb_interface = build_kb_skill_interface(project_name)
            available_skills.append(kb_interface)
            if isinstance(available_skill_ids, set):
                available_skill_ids.add(kb_sid)
            else:
                available_skill_ids.append(kb_sid)

    return kb_skill_ids


def _format_assistant_delta_event(*, model: str, content: str) -> str:
    return format_sse_event(
        build_ollama_assistant_chunk(
            model=model,
            content=content,
        )
    )


def _format_done_event(*, model: str, done_reason: str) -> str:
    return format_sse_event(
        build_ollama_done_chunk(
            model=model,
            done_reason=done_reason,
        )
    )


async def _extract_http_status_error_message(exc: httpx.HTTPStatusError) -> str:
    base_message = f"远程 Ollama 接口返回错误状态：{exc.response.status_code}"
    error_payload: dict[str, Any] | list[Any] | None = None

    try:
        error_payload = exc.response.json()
    except httpx.ResponseNotRead:
        try:
            raw_body = await exc.response.aread()
        except Exception:
            logger.debug("Failed to read error response body", exc_info=True)
            raw_body = b""

        if raw_body:
            try:
                error_payload = json.loads(raw_body.decode("utf-8", errors="ignore"))
            except ValueError:
                raw_text = raw_body.decode("utf-8", errors="ignore").strip()
                if raw_text:
                    return raw_text[:500]
    except ValueError:
        try:
            raw_text = exc.response.text.strip()
        except httpx.ResponseNotRead:
            raw_text = ""
        if raw_text:
            return raw_text[:500]

    if isinstance(error_payload, dict):
        detail = error_payload.get("error") or error_payload.get("message") or error_payload.get("detail")
        if isinstance(detail, str) and detail.strip():
            return detail.strip()[:500]

    return base_message


def _normalize_skill_ids(raw_skill_ids: list[str]) -> list[str]:
    normalized: list[str] = []
    for raw_skill_id in raw_skill_ids:
        skill_id = raw_skill_id.strip()
        if skill_id and skill_id not in normalized:
            normalized.append(skill_id)
    return normalized


def _extract_skill_ids_from_messages(
    *,
    messages: list[ChatMessageInput],
    available_skills: list[SkillInterfaceConfig],
) -> tuple[list[str], list[str]]:
    mentioned_skill_ids: list[str] = []
    missing_skill_ids: list[str] = []
    pattern = re.compile(r"\$([A-Za-z0-9._:\u4e00-\u9fff-]+)")
    available_skill_ids = {str(skill.id).strip() for skill in available_skills}

    for message in messages:
        if getattr(message, "role", None) != "user":
            continue
        content = str(getattr(message, "content", "") or "")
        for matched_skill_id in pattern.findall(content):
            skill_id = matched_skill_id.strip()
            if not skill_id:
                continue
            if skill_id in available_skill_ids:
                if skill_id not in mentioned_skill_ids:
                    mentioned_skill_ids.append(skill_id)
            elif skill_id not in missing_skill_ids:
                missing_skill_ids.append(skill_id)

    return mentioned_skill_ids, missing_skill_ids


async def _resolve_skill_plan(
    request: ChatStreamRequest,
) -> SkillPlanDecision:
    available_skills = _list_chat_skill_interfaces()
    available_skill_ids = {skill.id for skill in available_skills}
    explicit_skill_ids = _normalize_skill_ids(request.selected_skill_ids)

    kb_skill_ids = [sid for sid in explicit_skill_ids if is_kb_skill_id(sid)]
    _register_kb_skills_from_messages(
        request.messages,
        kb_skill_ids,
        available_skills,
        available_skill_ids,
    )

    mentioned_skill_ids, missing_mentioned_skill_ids = _extract_skill_ids_from_messages(
        messages=request.messages,
        available_skills=available_skills,
    )
    for mentioned_skill_id in mentioned_skill_ids:
        if mentioned_skill_id not in explicit_skill_ids:
            explicit_skill_ids.append(mentioned_skill_id)
    missing_explicit_skill_ids = [skill_id for skill_id in explicit_skill_ids if skill_id not in available_skill_ids]
    for missing_skill_id in missing_mentioned_skill_ids:
        if missing_skill_id not in missing_explicit_skill_ids:
            missing_explicit_skill_ids.append(missing_skill_id)
    valid_explicit_skill_ids = [skill_id for skill_id in explicit_skill_ids if skill_id in available_skill_ids]
    skill_plan = await select_for_chat_skills(
        model=request.model,
        messages=request.messages,
        available_skills=available_skills,
        explicit_skill_ids=valid_explicit_skill_ids,
        missing_explicit_skill_ids=missing_explicit_skill_ids,
        system_skill_id=SYSTEM_DOCUMENT_SKILL_ID,
    )
    return skill_plan


def _build_direct_skill_plan(
    *,
    request: ChatStreamRequest,
) -> SkillPlanDecision:
    available_skills = _list_chat_skill_interfaces()
    available_skill_ids = [skill.id for skill in available_skills]

    explicit_skill_ids_raw = _normalize_skill_ids(request.selected_skill_ids)

    kb_skill_ids = [sid for sid in explicit_skill_ids_raw if is_kb_skill_id(sid)]
    _register_kb_skills_from_messages(
        request.messages,
        kb_skill_ids,
        available_skills,
        available_skill_ids,
    )

    explicit_skill_ids = [skill_id for skill_id in explicit_skill_ids_raw if skill_id in available_skill_ids]
    if explicit_skill_ids:
        primary_skill_id = explicit_skill_ids[0]
    elif SYSTEM_DOCUMENT_SKILL_ID in available_skill_ids:
        primary_skill_id = SYSTEM_DOCUMENT_SKILL_ID
    else:
        primary_skill_id = available_skill_ids[0] if available_skill_ids else SYSTEM_DOCUMENT_SKILL_ID

    active_skill_ids: list[str] = [primary_skill_id]
    if SYSTEM_DOCUMENT_SKILL_ID in available_skill_ids and SYSTEM_DOCUMENT_SKILL_ID not in active_skill_ids:
        active_skill_ids.append(SYSTEM_DOCUMENT_SKILL_ID)
    for skill_id in explicit_skill_ids:
        if skill_id not in active_skill_ids:
            active_skill_ids.append(skill_id)

    return SkillPlanDecision(
        planner_model=request.model,
        required_skill_ids=explicit_skill_ids,
        optional_skill_ids=[],
        missing_explicit_skill_ids=[],
        active_skill_ids=active_skill_ids,
        primary_skill_id=primary_skill_id,
        confidence=None,
        reasons={"planner": "规划器灰度关闭，已回退到显式选择策略。"},
        candidates=[],
        created_at=to_utc8(datetime.now(UTC)),
    )


def _is_request_timed_out(started_monotonic: float) -> bool:
    timeout_seconds = max(1.0, settings.request_timeout_seconds)
    return (time.monotonic() - started_monotonic) >= timeout_seconds


def _append_planner_trace(
    *,
    agent_state: ConversationAgentState,
    decision: SkillPlanDecision,
) -> None:
    agent_state.planner_trace.append(decision)
    max_entries = max(1, settings.skill_planner_trace_max_entries)
    if len(agent_state.planner_trace) > max_entries:
        agent_state.planner_trace = agent_state.planner_trace[-max_entries:]


def _build_timeout_error_detail() -> dict[str, Any]:
    message = "请求处理超时，已终止。"
    return {
        "message": message,
        "error_detail": {
            "type": "TimeoutError",
            "message": message,
        },
    }


@dataclass
class _SkillContext:
    skill_plan: SkillPlanDecision
    active_skill_ids: list[str]
    primary_skill_id: str
    primary_request: ChatStreamRequest
    agent_state: ConversationAgentState
    states_by_skill: dict[str, SkillConversationState]
    primary_state: SkillConversationState
    prepared_uploaded_files: list[PreparedUploadedFile]
    uploaded_files_context: str | None
    planner_enabled: bool
    executor_enabled: bool


async def _prepare_skill_context(
    request: ChatStreamRequest,
    trace_recorder: AgentTraceRecorder,
    upload_files: list[UploadFile] | None,
    tenant_id: str,
) -> _SkillContext:
    planner_enabled = is_feature_enabled_for_key(
        feature_name="planner",
        key=f"{tenant_id}:{request.conversation_id}",
        enabled=settings.feature_planner_enabled,
        rollout_ratio=settings.feature_planner_rollout_ratio,
    )
    executor_enabled = is_feature_enabled_for_key(
        feature_name="executor",
        key=f"{tenant_id}:{request.conversation_id}",
        enabled=settings.feature_executor_enabled,
        rollout_ratio=settings.feature_executor_rollout_ratio,
    )
    trace_recorder.add_event(
        event_type="feature_flags",
        detail={
            "planner_enabled": planner_enabled,
            "executor_enabled": executor_enabled,
        },
    )

    if planner_enabled:
        skill_plan = await _resolve_skill_plan(request)
    else:
        skill_plan = _build_direct_skill_plan(request=request)

    trace_recorder.set_planner(skill_plan.model_dump(mode="json"))
    active_skill_ids = skill_plan.active_skill_ids
    primary_skill_id = skill_plan.primary_skill_id
    primary_request = request.model_copy(update={"skill_id": primary_skill_id})
    prepared_uploaded_files, new_uploaded_files_context = await prepare_uploaded_files(
        upload_files=upload_files or [],
        conversation_id=request.conversation_id,
        skill_id=primary_skill_id,
    )
    persisted_uploaded_files_context = build_persisted_uploaded_files_context(request.attachment_ids)
    uploaded_files_context = merge_uploaded_files_context(
        persisted_uploaded_files_context,
        new_uploaded_files_context,
    )
    agent_state = await load_conversation_state(
        request.conversation_id,
        tenant_id=tenant_id,
    )
    if agent_state is None:
        agent_state = ConversationAgentState(conversation_id=request.conversation_id)

    states_by_skill: dict[str, SkillConversationState] = {}
    for skill_id in active_skill_ids:
        if is_kb_skill_id(skill_id):
            project_name = extract_kb_project_name(skill_id)
            skill_interface = build_kb_skill_interface(project_name)
        else:
            skill_interface = get_skill_interface(skill_id)
        state = agent_state.skills_state.get(skill_id)
        if state is None:
            state = SkillConversationState(
                conversation_id=request.conversation_id,
                skill_id=skill_id,
                system_prompt=skill_interface.default_prompt,
                loaded_chunk_ids=[],
            )
            agent_state.skills_state[skill_id] = state
        elif not state.system_prompt.strip():
            state.system_prompt = skill_interface.default_prompt
        states_by_skill[skill_id] = state

    primary_state = states_by_skill[primary_skill_id]
    _append_planner_trace(agent_state=agent_state, decision=skill_plan)
    await save_conversation_state(agent_state, tenant_id=tenant_id)

    return _SkillContext(
        skill_plan=skill_plan,
        active_skill_ids=active_skill_ids,
        primary_skill_id=primary_skill_id,
        primary_request=primary_request,
        agent_state=agent_state,
        states_by_skill=states_by_skill,
        primary_state=primary_state,
        prepared_uploaded_files=prepared_uploaded_files,
        uploaded_files_context=uploaded_files_context,
        planner_enabled=planner_enabled,
        executor_enabled=executor_enabled,
    )


def _build_skill_upstream_messages(
    *,
    request: ChatStreamRequest,
    skill_ctx: _SkillContext,
    skill_context_by_skill: dict[str, str],
    extra_messages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return build_upstream_messages_for_skills(
        request=request,
        active_skill_ids=skill_ctx.active_skill_ids,
        explicit_skill_ids=skill_ctx.skill_plan.required_skill_ids,
        implicit_skill_ids=skill_ctx.skill_plan.optional_skill_ids,
        missing_skill_ids=skill_ctx.skill_plan.missing_explicit_skill_ids,
        skill_context_by_skill=skill_context_by_skill,
        uploaded_files_context=skill_ctx.uploaded_files_context,
        extra_messages=extra_messages,
    )


@dataclass
class _RoundMessages:
    upstream_messages: list[dict[str, Any]]
    skill_context_by_skill: dict[str, str]
    tools_enabled: bool


async def _build_round_upstream_messages(
    *,
    request: ChatStreamRequest,
    skill_ctx: _SkillContext,
    tool_trace_messages: list[dict[str, Any]],
    execution_budget: ExecutionBudget,
    tools_enabled: bool,
    tenant_id: str,
) -> _RoundMessages:
    skill_context_by_skill: dict[str, str] = {}
    for skill_id in skill_ctx.active_skill_ids:
        skill_state = skill_ctx.states_by_skill[skill_id]
        skill_context = await sync_skill_context_state(
            model=request.model,
            state=skill_state,
        )
        if skill_context:
            skill_context_by_skill[skill_id] = skill_context
    await save_conversation_state(skill_ctx.agent_state, tenant_id=tenant_id)

    upstream_messages = _build_skill_upstream_messages(
        request=request,
        skill_ctx=skill_ctx,
        skill_context_by_skill=skill_context_by_skill,
        extra_messages=tool_trace_messages,
    )
    model_context_length = await get_model_context_length(request.model)
    prompt_tokens_estimate = estimate_prompt_tokens(upstream_messages)
    prompt_budget_tokens = max(
        256,
        int(max(1, model_context_length) * max(0.2, min(0.95, settings.agent_executor_prompt_budget_ratio))),
    )
    execution_budget.prompt_tokens_estimate = prompt_tokens_estimate
    execution_budget.max_prompt_tokens = prompt_budget_tokens

    if tools_enabled and prompt_tokens_estimate >= prompt_budget_tokens:
        compacted_context_by_skill: dict[str, str] = {}
        for skill_id in skill_ctx.active_skill_ids:
            compacted_context = await sync_skill_context_state(
                model=request.model,
                state=skill_ctx.states_by_skill[skill_id],
                force_compact=True,
            )
            if compacted_context:
                compacted_context_by_skill[skill_id] = compacted_context
        await save_conversation_state(skill_ctx.agent_state, tenant_id=tenant_id)

        skill_context_by_skill = compacted_context_by_skill
        upstream_messages = _build_skill_upstream_messages(
            request=request,
            skill_ctx=skill_ctx,
            skill_context_by_skill=skill_context_by_skill,
            extra_messages=tool_trace_messages,
        )
        prompt_tokens_estimate = estimate_prompt_tokens(upstream_messages)
        execution_budget.prompt_tokens_estimate = prompt_tokens_estimate

        if prompt_tokens_estimate >= prompt_budget_tokens:
            tools_enabled = False
            tool_trace_messages.append(
                {
                    "role": "system",
                    "content": (
                        "当前会话上下文已接近模型可用窗口上限，且压缩后仍超过预算。"
                        f"估算 token={prompt_tokens_estimate}，预算={prompt_budget_tokens}。"
                        "本轮起停止工具调用，请基于已读取内容直接回答。"
                    ),
                }
            )
            upstream_messages = _build_skill_upstream_messages(
                request=request,
                skill_ctx=skill_ctx,
                skill_context_by_skill=skill_context_by_skill,
                extra_messages=tool_trace_messages,
            )

    return _RoundMessages(
        upstream_messages=upstream_messages,
        skill_context_by_skill=skill_context_by_skill,
        tools_enabled=tools_enabled,
    )


def _build_executor_deps() -> ExecutorDeps:
    return ExecutorDeps(
        build_tool_status_start=build_tool_status_start,
        build_tool_status_finish=build_tool_status_finish,
        build_tool_call_signature=build_tool_call_signature,
        get_tool_call_name=get_tool_call_name,
        detect_tool_call_progress=detect_tool_call_progress,
        execute_skill_tool_call=execute_skill_tool_call,
        execute_scoped_skill_tool_call=execute_scoped_skill_tool_call,
    )


async def stream_remote_chat_completion(
    request: ChatStreamRequest,
    upload_files: list[UploadFile] | None = None,
) -> AsyncIterator[str]:
    started_monotonic = time.monotonic()
    tenant_id = request.tenant_id.strip() or "default"
    trace_id = request.trace_id.strip() or uuid.uuid4().hex
    trace_recorder = AgentTraceRecorder(
        trace_id=trace_id,
        tenant_id=tenant_id,
        conversation_id=request.conversation_id,
        user_message_id=request.user_message_id,
        model=request.model,
        reranker_model=(request.reranker_model or request.model),
    )
    stream_done_reason: str | None = None
    stream_error_message: str | None = None
    request_guard = guard_request_slot(tenant_id)
    request_guard_entered = False

    if not settings.ollama_base_url:
        stream_error_message = "未配置 OLLAMA_BASE_URL，请检查后端环境配置文件。"
        yield format_sse_event(
            {
                "type": "error",
                "message": stream_error_message,
            }
        )
        trace_recorder.add_event(
            event_type="error",
            detail={
                "message": stream_error_message,
                "error_detail": {
                    "type": "ConfigurationError",
                    "message": stream_error_message,
                },
            },
        )
        trace_recorder.set_final(done_reason=stream_done_reason, error=stream_error_message)
        await trace_recorder.flush()
        return

    try:
        await request_guard.__aenter__()
        request_guard_entered = True
        yield format_sse_event(
            {
                "type": "trace",
                "phase": "start",
                "trace_id": trace_id,
            }
        )

        skill_ctx = await _prepare_skill_context(
            request=request,
            trace_recorder=trace_recorder,
            upload_files=upload_files,
            tenant_id=tenant_id,
        )
    except ValueError as exc:
        stream_error_message = summarize_exception(exc)
        yield format_sse_event({"type": "error", "message": stream_error_message})
        trace_recorder.add_event(
            event_type="error",
            detail=build_error_event_detail(
                message=stream_error_message,
                exc=exc,
            ),
        )
        if request_guard_entered:
            await request_guard.__aexit__(None, None, None)
            request_guard_entered = False
        trace_recorder.set_final(done_reason=stream_done_reason, error=stream_error_message)
        await trace_recorder.flush()
        return
    except RequestGuardError as exc:
        stream_error_message = summarize_exception(exc)
        yield format_sse_event({"type": "error", "message": stream_error_message})
        trace_recorder.add_event(
            event_type="error",
            detail=build_error_event_detail(
                message=stream_error_message,
                exc=exc,
            ),
        )
        if request_guard_entered:
            await request_guard.__aexit__(None, None, None)
            request_guard_entered = False
        trace_recorder.set_final(done_reason=stream_done_reason, error=stream_error_message)
        await trace_recorder.flush()
        return

    try:
        if _is_request_timed_out(started_monotonic):
            stream_error_message = "请求处理超时，已终止。"
            yield format_sse_event({"type": "error", "message": stream_error_message})
            trace_recorder.add_event(
                event_type="error",
                detail=_build_timeout_error_detail(),
            )
            return

        for prepared_uploaded_file in skill_ctx.prepared_uploaded_files:
            yield format_sse_event(
                {
                    "type": "uploaded-attachment",
                    "attachment": prepared_uploaded_file.attachment.model_dump(
                        mode="json",
                    ),
                }
            )

        tool_trace_messages: list[dict[str, Any]] = []
        first_assistant_chunk_emitted = False
        final_done_reason = "stop"
        executed_tool_calls: dict[str, dict[str, Any]] = {}
        tools_enabled = skill_ctx.executor_enabled
        tool_disabled_retry_count = 0
        tool_round_count = 0
        execution_budget = ExecutionBudget(
            max_tool_calls=max(1, settings.agent_executor_max_tool_calls),
            max_time_seconds=max(1.0, settings.agent_executor_time_budget_seconds),
            max_prompt_tokens=0,
            prompt_tokens_estimate=0,
        )
        if not skill_ctx.executor_enabled:
            tool_trace_messages.append(
                {
                    "role": "system",
                    "content": "当前请求未命中执行器灰度范围，本轮禁用工具调用，请直接完成回答。",
                }
            )
            trace_recorder.add_event(
                event_type="executor",
                detail={"enabled": False, "message": "executor 灰度关闭"},
            )

        while True:
            if _is_request_timed_out(started_monotonic):
                stream_error_message = "请求处理超时，已终止。"
                yield format_sse_event({"type": "error", "message": stream_error_message})
                trace_recorder.add_event(
                    event_type="error",
                    detail=_build_timeout_error_detail(),
                )
                return

            tooling_skill_ids = [
                skill_id for skill_id in skill_ctx.active_skill_ids if skill_id != SYSTEM_DOCUMENT_SKILL_ID
            ]
            if not tooling_skill_ids:
                tooling_skill_ids = [skill_ctx.primary_skill_id]

            round_messages = await _build_round_upstream_messages(
                request=request,
                skill_ctx=skill_ctx,
                tool_trace_messages=tool_trace_messages,
                execution_budget=execution_budget,
                tools_enabled=tools_enabled,
                tenant_id=tenant_id,
            )
            tools_enabled = round_messages.tools_enabled

            merged_tool_calls: dict[int, dict[str, Any]] = {}
            assistant_content_parts: list[str] = []

            async for chunk_payload in stream_chat_completion(
                model=request.model,
                messages=round_messages.upstream_messages,
                tools=(
                    (
                        build_skill_tools(tooling_skill_ids[0])
                        if len(tooling_skill_ids) == 1
                        else build_skill_tools_for_skills(tooling_skill_ids)
                    )
                    if tools_enabled
                    else None
                ),
            ):
                if _is_request_timed_out(started_monotonic):
                    stream_error_message = "请求处理超时，已终止。"
                    yield format_sse_event({"type": "error", "message": stream_error_message})
                    trace_recorder.add_event(
                        event_type="error",
                        detail=_build_timeout_error_detail(),
                    )
                    return

                if chunk_payload is None:
                    break

                delta_text = extract_delta_text(chunk_payload)
                if delta_text:
                    if not first_assistant_chunk_emitted:
                        trace_recorder.add_event(
                            event_type="first_assistant_chunk",
                            detail={
                                "latency_ms": int((time.monotonic() - started_monotonic) * 1000),
                            },
                        )
                        first_assistant_chunk_emitted = True
                    assistant_content_parts.append(delta_text)
                    yield _format_assistant_delta_event(
                        model=request.model,
                        content=delta_text,
                    )

                delta_tool_calls = extract_delta_tool_calls(chunk_payload)
                if delta_tool_calls:
                    merge_stream_tool_calls(merged_tool_calls, delta_tool_calls)

                done_reason = extract_done_reason(chunk_payload)
                if done_reason:
                    final_done_reason = done_reason

            normalized_tool_calls = [merged_tool_calls[index] for index in sorted(merged_tool_calls.keys())]

            if assistant_content_parts or normalized_tool_calls:
                tool_trace_messages.append(
                    {
                        "role": "assistant",
                        "content": "".join(assistant_content_parts),
                        "tool_calls": build_normalized_tool_calls(normalized_tool_calls),
                    }
                )

            if not normalized_tool_calls:
                yield _format_done_event(
                    model=request.model,
                    done_reason=final_done_reason,
                )
                stream_done_reason = final_done_reason
                return

            if not tools_enabled:
                tool_disabled_retry_count += 1
                tool_trace_messages.append(
                    {
                        "role": "system",
                        "content": "工具调用当前不可用，请直接根据已有信息给出最终回答。",
                    }
                )
                if tool_disabled_retry_count >= 2:
                    yield _format_done_event(
                        model=request.model,
                        done_reason=final_done_reason,
                    )
                    stream_done_reason = final_done_reason
                    return
                continue

            if tool_round_count >= settings.skill_tool_max_iterations:
                stream_error_message = "工具调用轮次过多，已终止本次请求。"
                yield format_sse_event(
                    {
                        "type": "error",
                        "message": stream_error_message,
                    }
                )
                trace_recorder.add_event(
                    event_type="error",
                    detail={
                        "message": stream_error_message,
                        "error_detail": {
                            "type": "ToolRoundLimitError",
                            "message": stream_error_message,
                        },
                    },
                )
                return

            tool_round_count += 1
            execution_budget.round_started_monotonic = time.monotonic()
            execution_result = await execute_tool_graph(
                execution_input=ExecutionInput(
                    request=request,
                    primary_request=skill_ctx.primary_request,
                    plan_decision=skill_ctx.skill_plan,
                    agent_state=skill_ctx.agent_state,
                    states_by_skill=skill_ctx.states_by_skill,
                    primary_skill_id=skill_ctx.primary_skill_id,
                    primary_state=skill_ctx.primary_state,
                    tooling_skill_ids=tooling_skill_ids,
                    normalized_tool_calls=normalized_tool_calls,
                    executed_tool_calls=executed_tool_calls,
                    budget=execution_budget,
                ),
                deps=_build_executor_deps(),
            )
            execution_budget.accumulated_execution_seconds += (
                time.monotonic() - execution_budget.round_started_monotonic
            )
            executed_tool_calls = execution_result.executed_tool_calls
            tool_trace_messages.extend(execution_result.tool_trace_messages)
            trace_recorder.add_round(
                round_index=tool_round_count,
                detail={
                    "normalized_tool_calls": normalized_tool_calls,
                    "status_events": execution_result.status_events,
                    "tool_trace_messages": execution_result.tool_trace_messages,
                    "error_message": execution_result.error_message,
                    "disable_tools": execution_result.disable_tools,
                    "tool_calls_consumed": execution_result.tool_calls_consumed,
                },
            )

            for status_event in execution_result.status_events:
                yield format_sse_event(status_event)

            for assistant_delta in execution_result.assistant_deltas:
                yield _format_assistant_delta_event(
                    model=request.model,
                    content=assistant_delta,
                )

            if execution_result.error_message:
                stream_error_message = execution_result.error_message
                yield format_sse_event(
                    {
                        "type": "error",
                        "message": execution_result.error_message,
                    }
                )
                trace_recorder.add_event(
                    event_type="error",
                    detail={
                        "message": stream_error_message,
                        "error_detail": {
                            "type": "ToolExecutionError",
                            "message": stream_error_message,
                        },
                    },
                )
                return

            if execution_result.disable_tools:
                tools_enabled = False

            await save_conversation_state(skill_ctx.agent_state, tenant_id=tenant_id)
    except ValueError as exc:
        stream_error_message = summarize_exception(exc)
        trace_recorder.add_event(
            event_type="error",
            detail=build_error_event_detail(
                message=stream_error_message,
                exc=exc,
            ),
        )
        yield format_sse_event({"type": "error", "message": stream_error_message})
    except OllamaNotConfiguredError as exc:
        stream_error_message = summarize_exception(exc)
        trace_recorder.add_event(
            event_type="error",
            detail=build_error_event_detail(
                message=stream_error_message,
                exc=exc,
            ),
        )
        yield format_sse_event({"type": "error", "message": stream_error_message})
    except httpx.HTTPStatusError as exc:
        error_message = await _extract_http_status_error_message(exc)
        stream_error_message = error_message
        trace_recorder.add_event(
            event_type="error",
            detail=build_error_event_detail(
                message=stream_error_message,
                exc=exc,
            ),
        )
        yield format_sse_event({"type": "error", "message": error_message})
    except httpx.HTTPError as exc:
        stream_error_message = f"连接远程 Ollama 失败：{summarize_exception(exc)}"
        trace_recorder.add_event(
            event_type="error",
            detail=build_error_event_detail(
                message=stream_error_message,
                exc=exc,
            ),
        )
        yield format_sse_event({"type": "error", "message": stream_error_message})
    except Exception as exc:
        stream_error_message = f"未预期的错误：{summarize_exception(exc)}"
        logger.exception("stream_remote_chat_completion unhandled error")
        trace_recorder.add_event(
            event_type="error",
            detail=build_error_event_detail(
                message=stream_error_message,
                exc=exc,
            ),
        )
        yield format_sse_event({"type": "error", "message": stream_error_message})
    finally:
        if request_guard_entered:
            await request_guard.__aexit__(None, None, None)
        trace_recorder.set_final(
            done_reason=stream_done_reason,
            error=stream_error_message,
        )
        try:
            await trace_recorder.flush()
        except Exception:
            logger.warning("Failed to flush trace recorder for trace_id=%s", trace_recorder.trace_id, exc_info=True)
