import json
from typing import Any


def _normalize_tool_name(tool_name: str) -> str:
    if "::" in tool_name:
        return tool_name.split("::", 1)[1].strip()
    return tool_name


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
    tool_name = _normalize_tool_name(tool_name)
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
