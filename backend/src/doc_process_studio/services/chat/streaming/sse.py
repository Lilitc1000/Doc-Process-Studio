import json
from typing import Any


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

