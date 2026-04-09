import json
from typing import Any


def format_sse_event(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def build_ollama_assistant_chunk(
    *,
    model: str,
    content: str,
) -> dict[str, Any]:
    return {
        "model": model,
        "message": {
            "role": "assistant",
            "content": content,
        },
        "done": False,
    }


def build_ollama_done_chunk(
    *,
    model: str,
    done_reason: str,
) -> dict[str, Any]:
    return {
        "model": model,
        "message": {
            "role": "assistant",
            "content": "",
        },
        "done": True,
        "done_reason": done_reason,
    }


def extract_delta_text(chunk_payload: dict[str, Any]) -> str:
    # Ollama 原生流：{"message":{"content":"..."}, "done": false}
    message = chunk_payload.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str):
            return content
    return ""


def extract_done_reason(chunk_payload: dict[str, Any]) -> str | None:
    # Ollama 原生流：最终块带 done=true / done_reason
    done_flag = chunk_payload.get("done")
    if done_flag is True:
        done_reason = chunk_payload.get("done_reason")
        if isinstance(done_reason, str) and done_reason.strip():
            return done_reason.strip()

        return "stop"
    return None


def extract_delta_tool_calls(chunk_payload: dict[str, Any]) -> list[dict[str, Any]]:
    # Ollama 原生流：{"message":{"tool_calls":[{"function":{"name":"...","arguments":{...}}}]}}
    message = chunk_payload.get("message")
    if isinstance(message, dict):
        tool_calls = message.get("tool_calls")
        if isinstance(tool_calls, list):
            normalized_tool_calls: list[dict[str, Any]] = []
            for index, tool_call in enumerate(tool_calls):
                if not isinstance(tool_call, dict):
                    continue

                function_payload = tool_call.get("function")
                if not isinstance(function_payload, dict):
                    continue

                function_name = function_payload.get("name")
                if not isinstance(function_name, str) or not function_name.strip():
                    continue

                raw_arguments = function_payload.get("arguments")
                if isinstance(raw_arguments, dict):
                    arguments_text = json.dumps(raw_arguments, ensure_ascii=False)
                elif isinstance(raw_arguments, str):
                    arguments_text = raw_arguments
                else:
                    arguments_text = ""

                normalized_tool_calls.append(
                    {
                        "index": index,
                        "type": "function",
                        "function": {
                            "name": function_name.strip(),
                            "arguments": arguments_text,
                        },
                    }
                )
            if normalized_tool_calls:
                return normalized_tool_calls
    return []


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
        if isinstance(function_arguments, dict):
            # 原生 Ollama 工具参数常是对象，统一转成字符串给后续解析器处理。
            current["function"]["arguments"] = json.dumps(
                function_arguments, ensure_ascii=False
            )
            continue
        if isinstance(function_arguments, str) and function_arguments:
            current["function"]["arguments"] += function_arguments
