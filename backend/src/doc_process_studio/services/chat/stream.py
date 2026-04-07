import json
from copy import deepcopy
from collections.abc import AsyncIterator
from typing import Any

import httpx
from fastapi import UploadFile

from ...models.conversation.stream import ChatMessageInput, ChatStreamRequest
from ...settings import settings
from ..infra.ollama_client import (
    OllamaNotConfiguredError,
    stream_chat_completion,
)
from ..skill.registry import get_skill_interface
from ..skill.runtime import ensure_skill_context_for_request, sync_skill_context_state
from ..skill.tool_loop import (
    build_skill_tools,
    build_tool_status_finish,
    build_tool_status_start,
    execute_skill_tool_call,
)
from .file_context import (
    build_persisted_uploaded_files_context,
    prepare_uploaded_files,
)


def format_sse_event(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def extract_delta_text(chunk_payload: dict[str, Any]) -> str:
    choices = chunk_payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""

    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        return ""

    delta = first_choice.get("delta")
    if not isinstance(delta, dict):
        return ""

    content = delta.get("content")
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_parts: list[str] = []
        for item in content:
            if not isinstance(item, dict):
                continue

            item_text = item.get("text")
            if isinstance(item_text, str):
                text_parts.append(item_text)

        return "".join(text_parts)

    return ""


def extract_finish_reason(chunk_payload: dict[str, Any]) -> str | None:
    choices = chunk_payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return None

    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        return None

    finish_reason = first_choice.get("finish_reason")
    if isinstance(finish_reason, str) and finish_reason:
        return finish_reason
    return None


def extract_delta_tool_calls(chunk_payload: dict[str, Any]) -> list[dict[str, Any]]:
    choices = chunk_payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return []

    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        return []

    delta = first_choice.get("delta")
    if not isinstance(delta, dict):
        return []

    tool_calls = delta.get("tool_calls")
    if not isinstance(tool_calls, list):
        return []

    return [tool_call for tool_call in tool_calls if isinstance(tool_call, dict)]


def merge_stream_tool_calls(
    merged_tool_calls: dict[int, dict[str, Any]],
    delta_tool_calls: list[dict[str, Any]],
) -> None:
    """聚合流式返回中的 tool_calls 片段。"""
    for tool_call in delta_tool_calls:
        raw_index = tool_call.get("index", len(merged_tool_calls))
        index = raw_index if isinstance(raw_index, int) and raw_index >= 0 else len(
            merged_tool_calls
        )
        current = merged_tool_calls.setdefault(
            index,
            {
                "id": "",
                "type": "function",
                "function": {
                    "name": "",
                    "arguments": "",
                },
            },
        )

        tool_call_id = tool_call.get("id")
        if isinstance(tool_call_id, str) and tool_call_id.strip():
            current["id"] = tool_call_id

        tool_type = tool_call.get("type")
        if isinstance(tool_type, str) and tool_type.strip():
            current["type"] = tool_type

        function_payload = tool_call.get("function")
        if not isinstance(function_payload, dict):
            continue

        function_name = function_payload.get("name")
        if isinstance(function_name, str) and function_name:
            current["function"]["name"] += function_name

        function_arguments = function_payload.get("arguments")
        if isinstance(function_arguments, str) and function_arguments:
            current["function"]["arguments"] += function_arguments


def parse_tool_call_arguments(tool_call: dict[str, Any]) -> dict[str, Any]:
    function_payload = tool_call.get("function")
    if not isinstance(function_payload, dict):
        return {}

    raw_arguments = function_payload.get("arguments")
    if isinstance(raw_arguments, dict):
        return raw_arguments

    if not isinstance(raw_arguments, str) or not raw_arguments.strip():
        return {}

    try:
        parsed_arguments = json.loads(raw_arguments)
    except json.JSONDecodeError:
        return {}

    return parsed_arguments if isinstance(parsed_arguments, dict) else {}


def get_tool_call_name(tool_call: dict[str, Any]) -> str:
    function_payload = tool_call.get("function")
    if not isinstance(function_payload, dict):
        return ""

    raw_tool_name = function_payload.get("name")
    if isinstance(raw_tool_name, str):
        return raw_tool_name.strip()
    return ""


def build_tool_call_signature(tool_call: dict[str, Any]) -> str:
    tool_name = get_tool_call_name(tool_call)
    arguments = parse_tool_call_arguments(tool_call)
    return json.dumps(
        {
            "tool_name": tool_name,
            "arguments": arguments,
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def detect_tool_call_progress(
    *,
    tool_name: str,
    before_loaded_chunk_ids: set[str],
    after_loaded_chunk_ids: set[str],
    tool_result: dict[str, Any],
    next_attachments: list[dict[str, Any]] | list[Any],
) -> bool:
    if not tool_result.get("ok"):
        return False

    if next_attachments:
        return True

    if tool_name == "read_skill_context":
        return bool(after_loaded_chunk_ids - before_loaded_chunk_ids)

    if tool_name == "search_skill_context":
        raw_chunks = tool_result.get("chunks")
        return isinstance(raw_chunks, list) and len(raw_chunks) > 0

    if tool_name == "list_skill_directory":
        raw_entries = tool_result.get("entries")
        return isinstance(raw_entries, list) and len(raw_entries) > 0

    if tool_name == "read_skill_file":
        return bool(tool_result.get("content") or tool_result.get("message"))

    return True


def build_skill_prompt(skill_id: str) -> str:
    return get_skill_interface(skill_id).default_prompt


def build_skill_runtime_instructions(skill_id: str) -> str:
    skill_interface = get_skill_interface(skill_id)
    declared_tool_names = ", ".join(tool.name for tool in skill_interface.tools) or "无声明式工具"

    return "\n".join(
        [
            "你当前正在使用一个本地 skill。",
            f"当前 skill_id: {skill_interface.id}",
            f"当前 skill 名称: {skill_interface.display_name}",
            f"skill 简介: {skill_interface.short_description or '无'}",
            f"已声明工具: {declared_tool_names}",
            "请遵循渐进式披露：先查看技能目录，再优先读取 SKILL.md；若 SKILL.md 引用了 references、scripts 或 assets，再按需继续读取。",
            "不要一次性读取整个 skill 目录。",
            "如果 skill 中已经声明了可执行工具，应优先调用这些声明式工具，而不是在回答里手写脚本让用户自己运行。",
        ]
    )


def build_upstream_messages(
    request: ChatStreamRequest,
    skill_context: str | None = None,
    uploaded_files_context: str | None = None,
    extra_messages: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    system_message = ChatMessageInput(
        role="system",
        content=build_skill_prompt(request.skill_id),
    )
    upstream_messages: list[dict[str, Any]] = [system_message.model_dump()]
    upstream_messages.append(
        ChatMessageInput(
            role="system",
            content=build_skill_runtime_instructions(request.skill_id),
        ).model_dump()
    )
    if skill_context:
        upstream_messages.append(
            ChatMessageInput(
                role="system",
                content=skill_context,
            ).model_dump()
        )
    if uploaded_files_context:
        upstream_messages.append(
            ChatMessageInput(
                role="user",
                content=uploaded_files_context,
            ).model_dump()
        )

    upstream_messages.extend([message.model_dump() for message in request.messages])
    if extra_messages:
        upstream_messages.extend(extra_messages)
    return upstream_messages


def merge_uploaded_files_context(
    *contexts: str | None,
) -> str | None:
    normalized_sections = [
        context.strip() for context in contexts if isinstance(context, str) and context.strip()
    ]
    if not normalized_sections:
        return None
    return "\n\n".join(normalized_sections)


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

        tool_trace_messages: list[dict[str, Any]] = []
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
                merged_tool_calls[index]
                for index in sorted(merged_tool_calls.keys())
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
                    execution_result = execute_skill_tool_call(
                        request=request,
                        state=state,
                        tool_call=tool_call,
                    )
                    if len(execution_result) == 3:
                        tool_result, next_attachments, _legacy_status_message = execution_result
                    else:
                        tool_result, next_attachments = execution_result
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
        error_message = (
            f"远程 Ollama 接口返回错误状态：{exc.response.status_code}"
        )
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
