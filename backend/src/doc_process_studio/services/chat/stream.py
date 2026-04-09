import json
import re
from collections.abc import AsyncIterator
from copy import deepcopy
from typing import Any

import httpx
from fastapi import UploadFile

from ...models.conversation.stream import ChatStreamRequest
from ...models.skill.runtime import SkillConversationState
from ...settings import settings
from ..infra.ollama_client import OllamaNotConfiguredError, stream_chat_completion
from ..skill.interaction_flow import start_or_resume_interaction, submit_interaction_answer
from ..skill.interaction_store import load_interaction_state
from ..skill.context import get_skill_context_chunks_by_ids
from ..skill.registry import (
    get_skill_interface,
    get_skill_interaction_config,
    list_skill_interfaces,
)
from ..skill.runtime import ensure_skill_context_for_request, sync_skill_context_state
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
    build_tool_call_signature,
    build_upstream_messages_for_skills,
    detect_tool_call_progress,
    extract_delta_text,
    extract_delta_tool_calls,
    extract_finish_reason,
    format_output_name_from_template,
    format_sse_event,
    get_tool_call_name,
    merge_stream_tool_calls,
    merge_uploaded_files_context,
)

SYSTEM_DOCUMENT_SKILL_ID = "document-assistant"


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
    """从用户消息中提取显式提及（`$skill-id` 或文本直提）。"""
    mentioned_skill_ids: list[str] = []
    missing_skill_ids: list[str] = []
    pattern = re.compile(r"\$([A-Za-z0-9._-]+)")
    available_skill_ids = {str(skill.id).strip() for skill in available_skills}
    skill_keywords: list[tuple[str, list[str]]] = []
    for skill in available_skills:
        skill_id = str(skill.id).strip()
        display_name = str(getattr(skill, "display_name", "")).strip()
        keywords = [skill_id.lower()]
        if display_name:
            keywords.append(display_name.lower())
        skill_keywords.append((skill_id, keywords))

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

        normalized_content = content.lower()
        for skill_id, keywords in skill_keywords:
            if skill_id in mentioned_skill_ids:
                continue
            if any(keyword and keyword in normalized_content for keyword in keywords):
                mentioned_skill_ids.append(skill_id)

    return mentioned_skill_ids, missing_skill_ids


def _resolve_active_skill_ids(
    request: ChatStreamRequest,
) -> tuple[list[str], list[str], list[str], str]:
    available_skills = list_skill_interfaces()
    available_skill_ids = [skill.id for skill in available_skills]
    available_skill_id_set = set(available_skill_ids)
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
    valid_explicit_skill_ids = [
        skill_id for skill_id in explicit_skill_ids if skill_id in available_skill_ids
    ]

    request_skill_id = request.skill_id.strip()
    has_system_skill = SYSTEM_DOCUMENT_SKILL_ID in available_skill_ids
    active_skill_ids: list[str] = []

    # 决策顺序：显式 selected_skill_ids > 文本中 $skill 提及 > system skill 基线。
    if valid_explicit_skill_ids:
        primary_skill_id = valid_explicit_skill_ids[0]
        active_skill_ids.append(primary_skill_id)
        if has_system_skill and SYSTEM_DOCUMENT_SKILL_ID not in active_skill_ids:
            active_skill_ids.append(SYSTEM_DOCUMENT_SKILL_ID)
        for skill_id in valid_explicit_skill_ids[1:]:
            if skill_id not in active_skill_ids:
                active_skill_ids.append(skill_id)
    else:
        if has_system_skill:
            primary_skill_id = SYSTEM_DOCUMENT_SKILL_ID
        elif request_skill_id and request_skill_id in available_skill_ids:
            primary_skill_id = request_skill_id
        else:
            primary_skill_id = next(iter(available_skill_ids), SYSTEM_DOCUMENT_SKILL_ID)

        active_skill_ids.append(primary_skill_id)
        # 未显式指定时，以 system skill 为主，再按需开放其余技能给模型隐式选择。
        if primary_skill_id == SYSTEM_DOCUMENT_SKILL_ID:
            for skill_id in available_skill_ids:
                if skill_id == SYSTEM_DOCUMENT_SKILL_ID:
                    continue
                active_skill_ids.append(skill_id)
        elif has_system_skill:
            active_skill_ids.append(SYSTEM_DOCUMENT_SKILL_ID)

    return (
        active_skill_ids,
        valid_explicit_skill_ids,
        missing_explicit_skill_ids,
        primary_skill_id,
    )


def _build_ephemeral_skill_context(state: SkillConversationState) -> str | None:
    loaded_chunks = get_skill_context_chunks_by_ids(state.skill_id, state.loaded_chunk_ids)
    if not loaded_chunks:
        return None

    sections = [
        (
            "你已经读取了该文档处理方式的以下内容片段，请优先基于这些信息回答：\n\n"
            + "\n\n".join(
                [
                    "\n".join(
                        [
                            f"来源：{chunk.source_path}",
                            f"标题：{chunk.title}",
                            "内容：",
                            chunk.content,
                        ]
                    )
                    for chunk in loaded_chunks
                ]
            )
        )
    ]
    return "\n\n".join(sections).strip() or None


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
        (
            active_skill_ids,
            explicit_skill_ids,
            missing_explicit_skill_ids,
            primary_skill_id,
        ) = _resolve_active_skill_ids(request)
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
        primary_state, _ = await ensure_skill_context_for_request(primary_request)
        states_by_skill: dict[str, SkillConversationState] = {
            primary_skill_id: primary_state
        }
        for skill_id in active_skill_ids[1:]:
            skill_interface = get_skill_interface(skill_id)
            states_by_skill[skill_id] = SkillConversationState(
                conversation_id=request.conversation_id,
                skill_id=skill_id,
                system_prompt=skill_interface.default_prompt,
                loaded_chunk_ids=[],
            )
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
                    yield format_sse_event(
                        {
                            "type": "done",
                            "finish_reason": "interaction_required",
                        }
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
                    yield format_sse_event(
                        {
                            "type": "done",
                            "finish_reason": "interaction_required",
                        }
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
                        state=states_by_skill[primary_skill_id],
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
                                state=states_by_skill[primary_skill_id],
                                tool_call=tool_call,
                                tool_result=tool_result,
                                attachments=next_attachments,
                            ),
                        }
                    )

                    if not tool_result.get("ok"):
                        error_message = str(tool_result.get("error", "工具执行失败。"))
                        yield format_sse_event({"type": "error", "message": error_message})
                        return

                    completion_text = interaction_config.completion_message or "已根据你的选择生成报告。"
                    yield format_sse_event({"type": "delta", "content": completion_text})
                    yield format_sse_event(
                        {
                            "type": "done",
                            "finish_reason": "stop",
                        }
                    )
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
        final_finish_reason = "stop"
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
            primary_context = await sync_skill_context_state(
                model=request.model,
                state=states_by_skill[primary_skill_id],
            )
            if primary_context:
                skill_context_by_skill[primary_skill_id] = primary_context

            for skill_id, skill_state in states_by_skill.items():
                if skill_id == primary_skill_id:
                    continue
                ephemeral_context = _build_ephemeral_skill_context(skill_state)
                if ephemeral_context:
                    skill_context_by_skill[skill_id] = ephemeral_context

            upstream_messages = build_upstream_messages_for_skills(
                request=request,
                active_skill_ids=active_skill_ids,
                explicit_skill_ids=explicit_skill_ids,
                missing_skill_ids=missing_explicit_skill_ids,
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
                tool_choice="auto" if tools_enabled else None,
            ):
                if chunk_payload is None:
                    break

                delta_text = extract_delta_text(chunk_payload)
                if delta_text:
                    assistant_content_parts.append(delta_text)
                    yield format_sse_event({"type": "delta", "content": delta_text})

                delta_tool_calls = extract_delta_tool_calls(chunk_payload)
                if delta_tool_calls:
                    merge_stream_tool_calls(merged_tool_calls, delta_tool_calls)

                finish_reason = extract_finish_reason(chunk_payload)
                if finish_reason:
                    final_finish_reason = finish_reason

            normalized_tool_calls = [
                merged_tool_calls[index] for index in sorted(merged_tool_calls.keys())
            ]

            if assistant_content_parts or normalized_tool_calls:
                tool_trace_messages.append(
                    {
                        "role": "assistant",
                        "content": "".join(assistant_content_parts),
                        "tool_calls": normalized_tool_calls,
                    }
                )

            if not normalized_tool_calls:
                yield format_sse_event(
                    {
                        "type": "done",
                        "finish_reason": final_finish_reason,
                    }
                )
                return

            if not tools_enabled:
                yield format_sse_event(
                    {
                        "type": "done",
                        "finish_reason": final_finish_reason,
                    }
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
                                state=states_by_skill[primary_skill_id],
                                tool_call=tool_call,
                                tool_result=tool_result,
                                attachments=[],
                            ),
                        }
                    )

                    if tool_result.get("ok") and interaction_step is not None:
                        if should_emit_intro and interaction_config and interaction_config.intro_message:
                            yield format_sse_event(
                                {"type": "delta", "content": interaction_config.intro_message}
                            )
                        yield format_sse_event(
                            {
                                "type": "interaction",
                                "status": "required",
                                "interaction": interaction_step,
                            }
                        )
                        yield format_sse_event(
                            {
                                "type": "done",
                                "finish_reason": "interaction_required",
                            }
                        )
                        return

                    tool_trace_messages.append(
                        {
                            "role": "tool",
                            "tool_name": tool_name,
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
                        "tool_name": tool_name,
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
                            state=states_by_skill[primary_skill_id],
                            tool_call=tool_call,
                            tool_result=tool_result,
                            attachments=next_attachments,
                        ),
                    }
                )

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
        error_message = f"远程 Ollama 接口返回错误状态：{exc.response.status_code}"
        try:
            error_payload = exc.response.json()
            if isinstance(error_payload, dict):
                detail = error_payload.get("error") or error_payload.get("message")
                if isinstance(detail, str) and detail.strip():
                    error_message = detail.strip()
        except ValueError:
            pass

        yield format_sse_event({"type": "error", "message": error_message})
    except httpx.HTTPError as exc:
        yield format_sse_event(
            {"type": "error", "message": f"连接远程 Ollama 失败：{exc}"}
        )
