import json
from typing import Any


def parse_tool_arguments(tool_call: dict[str, Any]) -> dict[str, Any]:
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

    if isinstance(parsed_arguments, dict):
        return parsed_arguments
    return {}


def _extract_tool_name(tool_call: dict[str, Any]) -> str:
    function_payload = tool_call.get("function")
    if not isinstance(function_payload, dict):
        return ""

    tool_name = function_payload.get("name")
    if isinstance(tool_name, str):
        return tool_name.strip()
    return ""


def build_normalized_tool_calls(tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized_calls: list[dict[str, Any]] = []
    for tool_call in tool_calls:
        tool_name = _extract_tool_name(tool_call)
        if not tool_name:
            continue

        arguments = parse_tool_arguments(tool_call)
        normalized_calls.append(
            {
                "function": {
                    "name": tool_name,
                    "arguments": arguments,
                }
            }
        )
    return normalized_calls
