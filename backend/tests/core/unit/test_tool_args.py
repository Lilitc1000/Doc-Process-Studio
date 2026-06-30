from typing import Any

from doc_process_studio.common.utils.tool_args import (
    build_normalized_tool_calls,
    parse_tool_arguments,
)


def test_parse_tool_arguments_dict_arguments() -> None:
    tool_call = {"function": {"name": "test", "arguments": {"key": "value"}}}
    result = parse_tool_arguments(tool_call)
    assert result == {"key": "value"}


def test_parse_tool_arguments_string_arguments() -> None:
    tool_call = {"function": {"name": "test", "arguments": '{"key": "value"}'}}
    result = parse_tool_arguments(tool_call)
    assert result == {"key": "value"}


def test_parse_tool_arguments_no_function() -> None:
    result = parse_tool_arguments({})
    assert result == {}


def test_parse_tool_arguments_non_dict_function() -> None:
    result = parse_tool_arguments({"function": "invalid"})
    assert result == {}


def test_parse_tool_arguments_empty_string() -> None:
    result = parse_tool_arguments({"function": {"name": "test", "arguments": ""}})
    assert result == {}


def test_parse_tool_arguments_invalid_json_string() -> None:
    result = parse_tool_arguments({"function": {"name": "test", "arguments": "not json"}})
    assert result == {}


def test_parse_tool_arguments_json_array() -> None:
    result = parse_tool_arguments({"function": {"name": "test", "arguments": "[1,2]"}})
    assert result == {}


def test_build_normalized_tool_calls_basic() -> None:
    tool_calls: list[dict[str, Any]] = [
        {"function": {"name": "tool_a", "arguments": {"x": 1}}},
        {"function": {"name": "tool_b", "arguments": '{"y": 2}'}},
    ]
    result = build_normalized_tool_calls(tool_calls)
    assert len(result) == 2
    assert result[0]["function"]["name"] == "tool_a"
    assert result[0]["function"]["arguments"] == {"x": 1}
    assert result[1]["function"]["name"] == "tool_b"
    assert result[1]["function"]["arguments"] == {"y": 2}


def test_build_normalized_tool_calls_skips_empty_name() -> None:
    tool_calls = [{"function": {"name": "", "arguments": {}}}]
    result = build_normalized_tool_calls(tool_calls)
    assert len(result) == 0


def test_build_normalized_tool_calls_skips_no_function() -> None:
    tool_calls = [{"id": "1"}]
    result = build_normalized_tool_calls(tool_calls)
    assert len(result) == 0


def test_build_normalized_tool_calls_strips_name() -> None:
    tool_calls = [{"function": {"name": "  tool_a  ", "arguments": {}}}]
    result = build_normalized_tool_calls(tool_calls)
    assert result[0]["function"]["name"] == "tool_a"
