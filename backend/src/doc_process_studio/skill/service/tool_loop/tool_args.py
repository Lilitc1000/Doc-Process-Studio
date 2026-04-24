from typing import Any

from .skill_files import _resolve_search_limit_bounds

def _get_tool_name(tool_call: dict[str, Any]) -> str:
    function_payload = tool_call.get("function")
    if not isinstance(function_payload, dict):
        return ""

    name = function_payload.get("name")
    if isinstance(name, str):
        return name.strip()
    return ""


def _validate_simple_type(value: Any, expected_type: str) -> bool:
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "array":
        return isinstance(value, list)
    if expected_type == "object":
        return isinstance(value, dict)
    return True


def _validate_tool_arguments_schema(
    *,
    tool_name: str,
    arguments: dict[str, Any],
    parameters: dict[str, Any],
) -> None:
    schema_type = str(parameters.get("type", "object")).strip()
    if schema_type and schema_type != "object":
        raise ValueError(f"工具 `{tool_name}` 参数 schema.type 仅支持 object。")

    properties = parameters.get("properties")
    if not isinstance(properties, dict):
        properties = {}

    raw_required = parameters.get("required")
    required_keys: list[str] = []
    if isinstance(raw_required, list):
        required_keys = [
            str(key).strip()
            for key in raw_required
            if isinstance(key, str) and str(key).strip()
        ]
    for required_key in required_keys:
        if required_key not in arguments:
            raise ValueError(f"工具 `{tool_name}` 缺少必填参数：{required_key}")

    additional_properties = parameters.get("additionalProperties", True)
    if additional_properties is False:
        unknown_keys = [key for key in arguments.keys() if key not in properties]
        if unknown_keys:
            raise ValueError(
                f"工具 `{tool_name}` 参数包含未声明字段：{', '.join(sorted(unknown_keys))}"
            )

    for key, value in arguments.items():
        prop_schema = properties.get(key)
        if not isinstance(prop_schema, dict):
            continue

        expected_type = prop_schema.get("type")
        if isinstance(expected_type, str):
            if not _validate_simple_type(value, expected_type):
                raise ValueError(
                    f"工具 `{tool_name}` 参数 `{key}` 类型错误，期望 {expected_type}。"
                )

            if expected_type == "array" and isinstance(value, list):
                item_schema = prop_schema.get("items")
                if isinstance(item_schema, dict):
                    item_type = item_schema.get("type")
                    if isinstance(item_type, str):
                        for index, item in enumerate(value):
                            if not _validate_simple_type(item, item_type):
                                raise ValueError(
                                    f"工具 `{tool_name}` 参数 `{key}[{index}]` 类型错误，期望 {item_type}。"
                                )

        enum_values = prop_schema.get("enum")
        if isinstance(enum_values, list) and enum_values:
            if value not in enum_values:
                raise ValueError(
                    f"工具 `{tool_name}` 参数 `{key}` 不在允许枚举值中。"
                )

        minimum = prop_schema.get("minimum")
        if isinstance(minimum, (int, float)) and isinstance(value, (int, float)):
            if value < minimum:
                raise ValueError(
                    f"工具 `{tool_name}` 参数 `{key}` 小于最小值 {minimum}。"
                )

        maximum = prop_schema.get("maximum")
        if isinstance(maximum, (int, float)) and isinstance(value, (int, float)):
            if value > maximum:
                raise ValueError(
                    f"工具 `{tool_name}` 参数 `{key}` 超过最大值 {maximum}。"
                )


def _normalize_builtin_tool_arguments(
    *,
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """对内置工具参数做温和规整，避免模型轻微越界直接失败。"""
    normalized_arguments = dict(arguments)
    if tool_name != "search_skill_context":
        return normalized_arguments

    default_search_limit, max_search_limit = _resolve_search_limit_bounds()
    raw_limit = normalized_arguments.get("limit")
    if raw_limit is None:
        return normalized_arguments

    parsed_limit: int | None = None
    if isinstance(raw_limit, int) and not isinstance(raw_limit, bool):
        parsed_limit = raw_limit
    elif isinstance(raw_limit, str):
        stripped_limit = raw_limit.strip()
        if stripped_limit:
            try:
                parsed_limit = int(stripped_limit)
            except ValueError:
                parsed_limit = None

    if parsed_limit is None:
        normalized_arguments.pop("limit", None)
        return normalized_arguments

    if parsed_limit < 1:
        normalized_arguments["limit"] = default_search_limit
    elif parsed_limit > max_search_limit:
        normalized_arguments["limit"] = max_search_limit
    else:
        normalized_arguments["limit"] = parsed_limit

    return normalized_arguments


def _build_builtin_tool_parameters(tool_name: str) -> dict[str, Any] | None:
    if tool_name == "list_skill_directory":
        return {
            "type": "object",
            "properties": {"relative_path": {"type": "string"}},
            "additionalProperties": False,
        }
    if tool_name == "read_skill_file":
        return {
            "type": "object",
            "properties": {"relative_path": {"type": "string"}},
            "required": ["relative_path"],
            "additionalProperties": False,
        }
    if tool_name == "search_skill_context":
        _, max_search_limit = _resolve_search_limit_bounds()
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "source_path": {"type": "string"},
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": max_search_limit,
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        }
    if tool_name == "read_skill_context":
        return {
            "type": "object",
            "properties": {
                "chunk_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                }
            },
            "required": ["chunk_ids"],
            "additionalProperties": False,
        }
    return None
