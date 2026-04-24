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
    def is_complete_json_payload(text: str) -> bool:
        if not text:
            return False
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return False
        return isinstance(parsed, (dict, list))

    def is_progressive_json_update(current_text: str, incoming_text: str) -> bool:
        if not (is_complete_json_payload(current_text) and is_complete_json_payload(incoming_text)):
            return False
        try:
            current_payload = json.loads(current_text)
            incoming_payload = json.loads(incoming_text)
        except json.JSONDecodeError:
            return False

        def _is_value_progressive(base: Any, target: Any) -> bool:
            if base == target:
                return True
            if isinstance(base, str) and isinstance(target, str):
                return target.startswith(base)
            if isinstance(base, dict) and isinstance(target, dict):
                base_keys = set(base.keys())
                target_keys = set(target.keys())
                if not base_keys.issubset(target_keys):
                    return False
                return all(_is_value_progressive(base[key], target[key]) for key in base_keys)
            if isinstance(base, list) and isinstance(target, list):
                if len(base) > len(target):
                    return False
                return all(_is_value_progressive(base[idx], target[idx]) for idx in range(len(base)))
            return False

        return _is_value_progressive(current_payload, incoming_payload)

    def merge_stream_text(current_text: str, incoming_text: str) -> str:
        if not incoming_text:
            return current_text
        if not current_text:
            return incoming_text
        if incoming_text == current_text:
            return current_text
        if incoming_text.startswith(current_text):
            return incoming_text
        if current_text.startswith(incoming_text):
            return current_text
        if current_text.endswith(incoming_text):
            return current_text
        return current_text + incoming_text

    def normalize_arguments_text(raw_arguments: Any) -> str:
        if isinstance(raw_arguments, dict):
            return json.dumps(raw_arguments, ensure_ascii=False)
        if isinstance(raw_arguments, str):
            return raw_arguments
        return ""

    def has_name_fragment_relation(current_name: str, incoming_name: str) -> bool:
        if not current_name or not incoming_name:
            return True
        return (
            current_name.startswith(incoming_name)
            or incoming_name.startswith(current_name)
            or current_name.endswith(incoming_name)
            or incoming_name.endswith(current_name)
        )

    def should_start_new_tool_call(
        *,
        current_call: dict[str, Any],
        incoming_call: dict[str, Any],
    ) -> bool:
        current_id = str(current_call.get("id") or "").strip()
        incoming_id = str(incoming_call.get("id") or "").strip()
        if current_id and incoming_id and current_id != incoming_id:
            return True

        current_function = current_call.get("function")
        incoming_function = incoming_call.get("function")
        if not isinstance(current_function, dict) or not isinstance(incoming_function, dict):
            return False

        current_name = str(current_function.get("name") or "").strip()
        incoming_name = str(incoming_function.get("name") or "").strip()
        current_arguments_text = normalize_arguments_text(current_function.get("arguments"))
        incoming_arguments_text = normalize_arguments_text(incoming_function.get("arguments"))

        if current_name and incoming_name and not has_name_fragment_relation(current_name, incoming_name):
            return True

        if (
            current_name
            and incoming_name
            and current_name == incoming_name
            and current_arguments_text
            and incoming_arguments_text
            and current_arguments_text != incoming_arguments_text
            and is_complete_json_payload(current_arguments_text)
            and is_complete_json_payload(incoming_arguments_text)
            and not (
                is_progressive_json_update(current_arguments_text, incoming_arguments_text)
                or is_progressive_json_update(incoming_arguments_text, current_arguments_text)
            )
        ):
            return True

        return False

    def allocate_next_tool_call_index() -> int:
        if not merged_tool_calls:
            return 0
        return max(merged_tool_calls.keys()) + 1

    for tool_call in delta_tool_calls:
        raw_index = tool_call.get("index", len(merged_tool_calls))
        index = raw_index if isinstance(raw_index, int) and raw_index >= 0 else len(
            merged_tool_calls
        )
        current = merged_tool_calls.get(index)
        if current is not None and should_start_new_tool_call(
            current_call=current,
            incoming_call=tool_call,
        ):
            index = allocate_next_tool_call_index()
            current = None

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
            current["function"]["name"] = merge_stream_text(
                str(current["function"].get("name") or ""),
                function_name,
            )

        function_arguments = function_payload.get("arguments")
        if isinstance(function_arguments, dict):
            incoming_arguments = json.dumps(function_arguments, ensure_ascii=False)
            current["function"]["arguments"] = merge_stream_text(
                str(current["function"].get("arguments") or ""),
                incoming_arguments,
            )
            continue
        if isinstance(function_arguments, str) and function_arguments:
            current["function"]["arguments"] = merge_stream_text(
                str(current["function"].get("arguments") or ""),
                function_arguments,
            )
