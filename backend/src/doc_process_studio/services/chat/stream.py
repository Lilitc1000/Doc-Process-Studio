import json
import re
from datetime import UTC, datetime
from collections.abc import AsyncIterator
from copy import deepcopy
from typing import Any

import httpx
from fastapi import UploadFile

from ...models.conversation.stream import ChatStreamRequest
from ...models.skill.runtime import (
    ConversationAgentState,
    SkillConversationState,
    SkillPlanDecision,
    SkillToolHistoryRecord,
)
from ...settings import settings
from ..infra.ollama_client import OllamaNotConfiguredError, stream_chat_completion
from ..skill.interaction_flow import start_or_resume_interaction, submit_interaction_answer
from ..skill.interaction_store import load_interaction_state
from ..skill.conversation_store import load_conversation_state, save_conversation_state
from ..skill.registry import (
    get_skill_interface,
    get_skill_interaction_config,
    list_skill_interfaces,
)
from ..skill.planner import plan_skill_activation
from ..skill.runtime import sync_skill_context_state
from ..skill.tool_loop import (
    build_skill_tools,
    build_skill_tools_for_skills,
    build_tool_status_finish,
    build_tool_status_start,
    execute_scoped_skill_tool_call,
    execute_skill_tool_call,
)
from .file_context import build_persisted_uploaded_files_context, prepare_uploaded_files
from .streaming import (
    build_ollama_assistant_chunk,
    build_ollama_done_chunk,
    build_tool_call_signature,
    build_upstream_messages_for_skills,
    detect_tool_call_progress,
    extract_done_reason,
    extract_delta_text,
    extract_delta_tool_calls,
    format_output_name_from_template,
    format_sse_event,
    get_tool_call_name,
    merge_stream_tool_calls,
    merge_uploaded_files_context,
)

SYSTEM_DOCUMENT_SKILL_ID = "document-assistant"


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


def _build_native_tool_calls(tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized_calls: list[dict[str, Any]] = []
    for tool_call in tool_calls:
        function_payload = tool_call.get("function")
        if not isinstance(function_payload, dict):
            continue

        tool_name = function_payload.get("name")
        if not isinstance(tool_name, str) or not tool_name.strip():
            continue

        raw_arguments = function_payload.get("arguments")
        if isinstance(raw_arguments, dict):
            arguments: dict[str, Any] | str = raw_arguments
        elif isinstance(raw_arguments, str):
            try:
                parsed_arguments = json.loads(raw_arguments)
            except json.JSONDecodeError:
                arguments = raw_arguments
            else:
                arguments = parsed_arguments if isinstance(parsed_arguments, dict) else raw_arguments
        else:
            arguments = {}

        normalized_calls.append(
            {
                "function": {
                    "name": tool_name.strip(),
                    "arguments": arguments,
                }
            }
        )
    return normalized_calls


async def _extract_http_status_error_message(exc: httpx.HTTPStatusError) -> str:
    """安全提取上游错误信息，避免流式响应未读取时触发 ResponseNotRead。"""
    base_message = f"远程 Ollama 接口返回错误状态：{exc.response.status_code}"
    error_payload: Any | None = None

    try:
        error_payload = exc.response.json()
    except httpx.ResponseNotRead:
        try:
            raw_body = await exc.response.aread()
        except Exception:
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
        detail = (
            error_payload.get("error")
            or error_payload.get("message")
            or error_payload.get("detail")
        )
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
    messages: list[Any],
    available_skills: list[Any],
) -> tuple[list[str], list[str]]:
    """从用户消息中提取显式提及（仅识别 `$skill-id`）。"""
    mentioned_skill_ids: list[str] = []
    missing_skill_ids: list[str] = []
    pattern = re.compile(r"\$([A-Za-z0-9._-]+)")
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
    available_skills = list_skill_interfaces()
    available_skill_ids = {skill.id for skill in available_skills}
    explicit_skill_ids = _normalize_skill_ids(request.selected_skill_ids)
    mentioned_skill_ids, missing_mentioned_skill_ids = _extract_skill_ids_from_messages(
        messages=request.messages,
        available_skills=available_skills,
    )
    for mentioned_skill_id in mentioned_skill_ids:
        if mentioned_skill_id not in explicit_skill_ids:
            explicit_skill_ids.append(mentioned_skill_id)
    missing_explicit_skill_ids = [
        skill_id for skill_id in explicit_skill_ids if skill_id not in available_skill_ids
    ]
    for missing_skill_id in missing_mentioned_skill_ids:
        if missing_skill_id not in missing_explicit_skill_ids:
            missing_explicit_skill_ids.append(missing_skill_id)
    valid_explicit_skill_ids = [skill_id for skill_id in explicit_skill_ids if skill_id in available_skill_ids]
    skill_plan = await plan_skill_activation(
        model=request.model,
        messages=request.messages,
        available_skills=available_skills,
        explicit_skill_ids=valid_explicit_skill_ids,
        missing_explicit_skill_ids=missing_explicit_skill_ids,
        system_skill_id=SYSTEM_DOCUMENT_SKILL_ID,
        max_implicit_skills=settings.skill_planner_max_implicit_skills,
        top_k_candidates=settings.skill_planner_top_k_candidates,
        min_confidence=settings.skill_planner_min_confidence,
    )
    return skill_plan


def _resolve_tool_scope_for_history(
    *,
    default_skill_id: str,
    tool_call: dict[str, Any],
) -> tuple[str, str]:
    tool_name = get_tool_call_name(tool_call)
    normalized_tool_name = tool_name

    if "::" in tool_name:
        scoped_skill_id, scoped_tool_name = tool_name.split("::", 1)
        scoped_skill_id = scoped_skill_id.strip()
        scoped_tool_name = scoped_tool_name.strip()
        if scoped_skill_id and scoped_tool_name:
            return scoped_skill_id, scoped_tool_name

    function_payload = tool_call.get("function")
    if isinstance(function_payload, dict):
        raw_arguments = function_payload.get("arguments")
        parsed_arguments: dict[str, Any] = {}
        if isinstance(raw_arguments, dict):
            parsed_arguments = raw_arguments
        elif isinstance(raw_arguments, str):
            try:
                loaded_arguments = json.loads(raw_arguments)
            except json.JSONDecodeError:
                loaded_arguments = {}
            if isinstance(loaded_arguments, dict):
                parsed_arguments = loaded_arguments

        scoped_skill_id = str(parsed_arguments.get("skill_id", "")).strip()
        if scoped_skill_id:
            return scoped_skill_id, normalized_tool_name

    return default_skill_id, normalized_tool_name


def _append_planner_trace(
    *,
    agent_state: ConversationAgentState,
    decision: SkillPlanDecision,
) -> None:
    agent_state.planner_trace.append(decision)
    max_entries = max(1, settings.skill_planner_trace_max_entries)
    if len(agent_state.planner_trace) > max_entries:
        agent_state.planner_trace = agent_state.planner_trace[-max_entries:]


def _append_tool_history(
    *,
    agent_state: ConversationAgentState,
    record: SkillToolHistoryRecord,
) -> None:
    agent_state.tool_history.append(record)
    max_entries = max(1, settings.skill_tool_history_max_entries)
    if len(agent_state.tool_history) > max_entries:
        agent_state.tool_history = agent_state.tool_history[-max_entries:]


def _collect_loaded_chunk_signatures(
    states_by_skill: dict[str, SkillConversationState],
) -> set[str]:
    signatures: set[str] = set()
    for skill_id, state in states_by_skill.items():
        for chunk_id in state.loaded_chunk_ids:
            signatures.add(f"{skill_id}::{chunk_id}")
    return signatures


async def stream_remote_chat_completion(
    request: ChatStreamRequest,
    upload_files: list[UploadFile] | None = None,
) -> AsyncIterator[str]:
    if not settings.ollama_base_url:
        yield format_sse_event(
            {
                "type": "error",
                "message": "未配置 OLLAMA_BASE_URL，请检查后端环境配置文件。",
            }
        )
        return

    try:
        skill_plan = await _resolve_skill_plan(request)
        active_skill_ids = skill_plan.active_skill_ids
        primary_skill_id = skill_plan.primary_skill_id
        primary_request = request.model_copy(update={"skill_id": primary_skill_id})
        prepared_uploaded_files, new_uploaded_files_context = await prepare_uploaded_files(
            upload_files=upload_files or [],
            conversation_id=request.conversation_id,
            skill_id=primary_skill_id,
        )
        persisted_uploaded_files_context = build_persisted_uploaded_files_context(
            request.attachment_ids
        )
        uploaded_files_context = merge_uploaded_files_context(
            persisted_uploaded_files_context,
            new_uploaded_files_context,
        )
        agent_state = await load_conversation_state(request.conversation_id)
        if agent_state is None:
            agent_state = ConversationAgentState(conversation_id=request.conversation_id)

        states_by_skill: dict[str, SkillConversationState] = {}
        for skill_id in active_skill_ids:
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
        await save_conversation_state(agent_state)
    except ValueError as exc:
        yield format_sse_event({"type": "error", "message": str(exc)})
        return

    interaction_config = get_skill_interaction_config(primary_skill_id)
    interaction_context_message: dict[str, Any] | None = None

    try:
        for prepared_uploaded_file in prepared_uploaded_files:
            yield format_sse_event(
                {
                    "type": "uploaded-attachment",
                    "attachment": prepared_uploaded_file.attachment.model_dump(
                        mode="json",
                        by_alias=True,
                    ),
                }
            )

        if interaction_config is not None:
            if request.interaction_answer is None:
                current_interaction_state = await load_interaction_state(
                    request.conversation_id,
                    primary_skill_id,
                )
                if current_interaction_state is not None:
                    _, interaction_step = await start_or_resume_interaction(
                        request=primary_request,
                        config=interaction_config,
                    )
                    yield format_sse_event(
                        {
                            "type": "interaction",
                            "status": "required",
                            "interaction": interaction_step,
                        }
                    )
                    yield _format_done_event(
                        model=request.model,
                        done_reason="interaction_required",
                    )
                    return

            else:
                try:
                    next_interaction_step, completed_payload = await submit_interaction_answer(
                        request=primary_request,
                        config=interaction_config,
                        answer=request.interaction_answer,
                    )
                except ValueError as exc:
                    yield format_sse_event({"type": "error", "message": str(exc)})
                    return

                if next_interaction_step is not None:
                    yield format_sse_event(
                        {
                            "type": "interaction",
                            "status": "required",
                            "interaction": next_interaction_step,
                        }
                    )
                    yield _format_done_event(
                        model=request.model,
                        done_reason="interaction_required",
                    )
                    return

                yield format_sse_event({"type": "interaction", "status": "completed"})

                if completed_payload is not None and interaction_config.final_tool is not None:
                    final_tool = interaction_config.final_tool
                    tool_arguments = {
                        final_tool.argument_name: completed_payload,
                        **final_tool.static_arguments,
                    }
                    rendered_output_name = format_output_name_from_template(
                        final_tool.output_name_template,
                        completed_payload,
                    )
                    if rendered_output_name:
                        tool_arguments["output_name"] = rendered_output_name

                    tool_call = {
                        "id": "interaction-final-tool",
                        "type": "function",
                        "function": {
                            "name": final_tool.name,
                            "arguments": json.dumps(tool_arguments, ensure_ascii=False),
                        },
                    }
                    tool_name = final_tool.name

                    yield format_sse_event(
                        {
                            "type": "tool-status",
                            "phase": "start",
                            "tool_name": tool_name,
                            **build_tool_status_start(
                                skill_id=primary_skill_id,
                                tool_call=tool_call,
                            ),
                        }
                    )

                    tool_result, next_attachments = execute_skill_tool_call(
                        request=primary_request,
                        state=primary_state,
                        tool_call=tool_call,
                    )

                    for attachment in next_attachments:
                        yield format_sse_event(
                            {
                                "type": "attachment",
                                "attachment": attachment.model_dump(
                                    mode="json",
                                    by_alias=True,
                                ),
                            }
                        )

                    yield format_sse_event(
                        {
                            "type": "tool-status",
                            "phase": "finish",
                            "tool_name": tool_name,
                            **build_tool_status_finish(
                                request=primary_request,
                                state=primary_state,
                                tool_call=tool_call,
                                tool_result=tool_result,
                                attachments=next_attachments,
                            ),
                        }
                    )
                    history_skill_id, history_tool_name = _resolve_tool_scope_for_history(
                        default_skill_id=primary_skill_id,
                        tool_call=tool_call,
                    )
                    _append_tool_history(
                        agent_state=agent_state,
                        record=SkillToolHistoryRecord(
                            skill_id=history_skill_id,
                            tool_name=history_tool_name,
                            ok=bool(tool_result.get("ok")),
                            reused=bool(tool_result.get("reused")),
                            attachment_count=len(next_attachments),
                            error=(
                                str(tool_result.get("error"))
                                if not tool_result.get("ok") and tool_result.get("error") is not None
                                else None
                            ),
                            created_at=datetime.now(UTC),
                        ),
                    )
                    await save_conversation_state(agent_state)

                    if not tool_result.get("ok"):
                        error_message = str(tool_result.get("error", "工具执行失败。"))
                        yield format_sse_event({"type": "error", "message": error_message})
                        return

                    completion_text = interaction_config.completion_message or "已根据你的选择生成报告。"
                    yield _format_assistant_delta_event(
                        model=request.model,
                        content=completion_text,
                    )
                    yield _format_done_event(model=request.model, done_reason="stop")
                    return

                if completed_payload is not None:
                    interaction_context_message = {
                        "role": "system",
                        "content": (
                            "以下是用户通过交互步骤确认的结构化信息，请直接基于它完成任务，不要再次向用户提问：\n"
                            + json.dumps(completed_payload, ensure_ascii=False, indent=2)
                        ),
                    }

        tool_trace_messages: list[dict[str, Any]] = (
            [interaction_context_message] if interaction_context_message is not None else []
        )
        final_done_reason = "stop"
        executed_tool_calls: dict[str, dict[str, Any]] = {}
        tools_enabled = True
        tool_round_count = 0

        while True:
            tooling_skill_ids = [
                skill_id
                for skill_id in active_skill_ids
                if skill_id != SYSTEM_DOCUMENT_SKILL_ID
            ]
            if not tooling_skill_ids:
                tooling_skill_ids = [primary_skill_id]

            skill_context_by_skill: dict[str, str] = {}
            for skill_id in active_skill_ids:
                skill_state = states_by_skill[skill_id]
                skill_context = await sync_skill_context_state(
                    model=request.model,
                    state=skill_state,
                )
                if skill_context:
                    skill_context_by_skill[skill_id] = skill_context
            await save_conversation_state(agent_state)

            upstream_messages = build_upstream_messages_for_skills(
                request=request,
                active_skill_ids=active_skill_ids,
                explicit_skill_ids=skill_plan.required_skill_ids,
                implicit_skill_ids=skill_plan.optional_skill_ids,
                missing_skill_ids=skill_plan.missing_explicit_skill_ids,
                skill_context_by_skill=skill_context_by_skill,
                uploaded_files_context=uploaded_files_context,
                extra_messages=tool_trace_messages,
            )

            merged_tool_calls: dict[int, dict[str, Any]] = {}
            assistant_content_parts: list[str] = []

            async for chunk_payload in stream_chat_completion(
                model=request.model,
                messages=upstream_messages,
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
                if chunk_payload is None:
                    break

                delta_text = extract_delta_text(chunk_payload)
                if delta_text:
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

            normalized_tool_calls = [
                merged_tool_calls[index] for index in sorted(merged_tool_calls.keys())
            ]

            if assistant_content_parts or normalized_tool_calls:
                tool_trace_messages.append(
                    {
                        "role": "assistant",
                        "content": "".join(assistant_content_parts),
                        "tool_calls": _build_native_tool_calls(normalized_tool_calls),
                    }
                )

            if not normalized_tool_calls:
                yield _format_done_event(
                    model=request.model,
                    done_reason=final_done_reason,
                )
                return

            if not tools_enabled:
                yield _format_done_event(
                    model=request.model,
                    done_reason=final_done_reason,
                )
                return

            if tool_round_count >= settings.skill_tool_max_iterations:
                yield format_sse_event(
                    {
                        "type": "error",
                        "message": "工具调用轮次过多，已终止本次请求。",
                    }
                )
                return

            tool_round_count += 1
            round_made_progress = False

            for tool_call in normalized_tool_calls:
                tool_name = get_tool_call_name(tool_call)

                yield format_sse_event(
                    {
                        "type": "tool-status",
                        "phase": "start",
                        "tool_name": tool_name,
                        **build_tool_status_start(
                            skill_id=primary_skill_id,
                            tool_call=tool_call,
                        ),
                    }
                )

                if tool_name == "start_skill_interaction":
                    interaction_step: dict[str, Any] | None = None
                    should_emit_intro = False
                    if len(tooling_skill_ids) != 1:
                        tool_result = {
                            "ok": False,
                            "error": (
                                "当前同时激活了多个文档处理方式，已禁用交互向导。"
                                "请仅选择一个处理方式后再发起向导。"
                            ),
                        }
                    elif interaction_config is None:
                        tool_result = {
                            "ok": False,
                            "error": "当前 skill 未配置交互向导。",
                        }
                    else:
                        existing_state = await load_interaction_state(
                            request.conversation_id,
                            primary_skill_id,
                        )
                        _, interaction_step = await start_or_resume_interaction(
                            request=primary_request,
                            config=interaction_config,
                        )
                        tool_result = {
                            "ok": True,
                            "interaction": interaction_step,
                            "message": "已启动交互向导。",
                        }
                        should_emit_intro = (
                            existing_state is None and bool(interaction_config.intro_message)
                        )
                    next_attachments: list[Any] = []

                    yield format_sse_event(
                        {
                            "type": "tool-status",
                            "phase": "finish",
                            "tool_name": tool_name,
                            **build_tool_status_finish(
                                request=primary_request,
                                state=primary_state,
                                tool_call=tool_call,
                                tool_result=tool_result,
                                attachments=[],
                            ),
                        }
                    )
                    history_skill_id, history_tool_name = _resolve_tool_scope_for_history(
                        default_skill_id=primary_skill_id,
                        tool_call=tool_call,
                    )
                    _append_tool_history(
                        agent_state=agent_state,
                        record=SkillToolHistoryRecord(
                            skill_id=history_skill_id,
                            tool_name=history_tool_name,
                            ok=bool(tool_result.get("ok")),
                            reused=False,
                            attachment_count=0,
                            error=(
                                str(tool_result.get("error"))
                                if not tool_result.get("ok") and tool_result.get("error") is not None
                                else None
                            ),
                            created_at=datetime.now(UTC),
                        ),
                    )
                    await save_conversation_state(agent_state)

                    if tool_result.get("ok") and interaction_step is not None:
                        if should_emit_intro and interaction_config and interaction_config.intro_message:
                            yield _format_assistant_delta_event(
                                model=request.model,
                                content=interaction_config.intro_message,
                            )
                        yield format_sse_event(
                            {
                                "type": "interaction",
                                "status": "required",
                                "interaction": interaction_step,
                            }
                        )
                        yield _format_done_event(
                            model=request.model,
                            done_reason="interaction_required",
                        )
                        return

                    tool_trace_messages.append(
                        {
                            "role": "tool",
                            "name": tool_name,
                            "content": json.dumps(tool_result, ensure_ascii=False),
                        }
                    )
                    continue

                tool_call_signature = build_tool_call_signature(tool_call)
                if tool_call_signature in executed_tool_calls:
                    cached_execution = executed_tool_calls[tool_call_signature]
                    tool_result = deepcopy(cached_execution["tool_result"])
                    tool_result["reused"] = True
                    next_attachments = []
                else:
                    before_loaded_chunk_ids = _collect_loaded_chunk_signatures(
                        states_by_skill
                    )
                    if len(tooling_skill_ids) == 1:
                        single_skill_id = tooling_skill_ids[0]
                        scoped_request = request.model_copy(
                            update={"skill_id": single_skill_id}
                        )
                        tool_result, next_attachments = execute_skill_tool_call(
                            request=scoped_request,
                            state=states_by_skill[single_skill_id],
                            tool_call=tool_call,
                        )
                    else:
                        tool_result, next_attachments = execute_scoped_skill_tool_call(
                            request=request,
                            states_by_skill=states_by_skill,
                            default_skill_id=primary_skill_id,
                            tool_call=tool_call,
                        )
                    after_loaded_chunk_ids = _collect_loaded_chunk_signatures(
                        states_by_skill
                    )
                    if detect_tool_call_progress(
                        tool_name=tool_name,
                        before_loaded_chunk_ids=before_loaded_chunk_ids,
                        after_loaded_chunk_ids=after_loaded_chunk_ids,
                        tool_result=tool_result,
                        next_attachments=next_attachments,
                    ):
                        round_made_progress = True
                    executed_tool_calls[tool_call_signature] = {
                        "tool_result": deepcopy(tool_result),
                    }

                for attachment in next_attachments:
                    yield format_sse_event(
                        {
                            "type": "attachment",
                            "attachment": attachment.model_dump(
                                mode="json",
                                by_alias=True,
                            ),
                        }
                    )

                if next_attachments:
                    round_made_progress = True

                tool_trace_messages.append(
                    {
                        "role": "tool",
                        "name": tool_name,
                        "content": json.dumps(tool_result, ensure_ascii=False),
                    }
                )
                yield format_sse_event(
                    {
                        "type": "tool-status",
                        "phase": "finish",
                        "tool_name": tool_name,
                        **build_tool_status_finish(
                            request=primary_request,
                            state=primary_state,
                            tool_call=tool_call,
                            tool_result=tool_result,
                            attachments=next_attachments,
                        ),
                    }
                )
                history_skill_id, history_tool_name = _resolve_tool_scope_for_history(
                    default_skill_id=primary_skill_id,
                    tool_call=tool_call,
                )
                _append_tool_history(
                    agent_state=agent_state,
                    record=SkillToolHistoryRecord(
                        skill_id=history_skill_id,
                        tool_name=history_tool_name,
                        ok=bool(tool_result.get("ok")),
                        reused=bool(tool_result.get("reused")),
                        attachment_count=len(next_attachments),
                        error=(
                            str(tool_result.get("error"))
                            if not tool_result.get("ok") and tool_result.get("error") is not None
                            else None
                        ),
                        created_at=datetime.now(UTC),
                    ),
                )
                await save_conversation_state(agent_state)

            if not round_made_progress:
                tools_enabled = False
                tool_trace_messages.append(
                    {
                        "role": "system",
                        "content": (
                            "本轮工具调用没有获得新的信息，或者只是重复读取。"
                            "请基于已经读取到的技能说明、参考资料和工具结果直接完成回答，"
                            "不要继续重复调用相同工具。"
                        ),
                    }
                )
    except OllamaNotConfiguredError as exc:
        yield format_sse_event({"type": "error", "message": str(exc)})
    except httpx.HTTPStatusError as exc:
        error_message = await _extract_http_status_error_message(exc)
        yield format_sse_event({"type": "error", "message": error_message})
    except httpx.HTTPError as exc:
        yield format_sse_event(
            {"type": "error", "message": f"连接远程 Ollama 失败：{exc}"}
        )
