import json
from collections.abc import AsyncIterator
from copy import deepcopy
from typing import Any

import httpx
from fastapi import UploadFile

from ...models.conversation.stream import ChatStreamRequest
from ...settings import settings
from ..infra.ollama_client import OllamaNotConfiguredError, stream_chat_completion
from ..skill.interaction_flow import start_or_resume_interaction, submit_interaction_answer
from ..skill.registry import get_skill_interaction_config
from ..skill.runtime import ensure_skill_context_for_request, sync_skill_context_state
from ..skill.tool_loop import (
    build_skill_tools,
    build_tool_status_finish,
    build_tool_status_start,
    execute_skill_tool_call,
)
from .file_context import build_persisted_uploaded_files_context, prepare_uploaded_files
from .streaming import (
    build_skill_prompt,
    build_tool_call_signature,
    build_upstream_messages,
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
        prepared_uploaded_files, new_uploaded_files_context = await prepare_uploaded_files(
            upload_files=upload_files or [],
            conversation_id=request.conversation_id,
            skill_id=request.skill_id,
        )
        persisted_uploaded_files_context = build_persisted_uploaded_files_context(
            request.attachment_ids
        )
        uploaded_files_context = merge_uploaded_files_context(
            persisted_uploaded_files_context,
            new_uploaded_files_context,
        )
        state, _ = await ensure_skill_context_for_request(request)
    except ValueError as exc:
        yield format_sse_event({"type": "error", "message": str(exc)})
        return

    interaction_config = get_skill_interaction_config(request.skill_id)
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
                _, interaction_step = await start_or_resume_interaction(
                    request=request,
                    config=interaction_config,
                )
                if interaction_config.intro_message:
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

            try:
                next_interaction_step, completed_payload = await submit_interaction_answer(
                    request=request,
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
                            skill_id=request.skill_id,
                            tool_call=tool_call,
                        ),
                    }
                )

                tool_result, next_attachments = execute_skill_tool_call(
                    request=request,
                    state=state,
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
                            request=request,
                            state=state,
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
            skill_context = await sync_skill_context_state(
                model=request.model,
                state=state,
            )
            upstream_messages = build_upstream_messages(
                request,
                skill_context=skill_context,
                uploaded_files_context=uploaded_files_context,
                extra_messages=tool_trace_messages,
            )

            merged_tool_calls: dict[int, dict[str, Any]] = {}
            assistant_content_parts: list[str] = []

            async for chunk_payload in stream_chat_completion(
                model=request.model,
                messages=upstream_messages,
                tools=build_skill_tools(request.skill_id) if tools_enabled else None,
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
                            skill_id=request.skill_id,
                            tool_call=tool_call,
                        ),
                    }
                )

                tool_call_signature = build_tool_call_signature(tool_call)
                if tool_call_signature in executed_tool_calls:
                    cached_execution = executed_tool_calls[tool_call_signature]
                    tool_result = deepcopy(cached_execution["tool_result"])
                    tool_result["reused"] = True
                    next_attachments = []
                else:
                    before_loaded_chunk_ids = set(state.loaded_chunk_ids)
                    tool_result, next_attachments = execute_skill_tool_call(
                        request=request,
                        state=state,
                        tool_call=tool_call,
                    )
                    after_loaded_chunk_ids = set(state.loaded_chunk_ids)
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
                            request=request,
                            state=state,
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
