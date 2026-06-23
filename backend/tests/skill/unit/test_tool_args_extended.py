import pytest

from doc_process_studio.skill.service.tool_loop.tool_args import (
    _build_builtin_tool_parameters,
    _normalize_builtin_tool_arguments,
    _validate_simple_type,
    _validate_tool_arguments_schema,
)


def test_validate_simple_type_string():
    assert _validate_simple_type("hello", "string") is True
    assert _validate_simple_type(123, "string") is False


def test_validate_simple_type_integer():
    assert _validate_simple_type(42, "integer") is True
    assert _validate_simple_type(True, "integer") is False
    assert _validate_simple_type(3.14, "integer") is False


def test_validate_simple_type_number():
    assert _validate_simple_type(42, "number") is True
    assert _validate_simple_type(3.14, "number") is True
    assert _validate_simple_type(True, "number") is False


def test_validate_simple_type_boolean():
    assert _validate_simple_type(True, "boolean") is True
    assert _validate_simple_type(1, "boolean") is False


def test_validate_simple_type_array():
    assert _validate_simple_type([1, 2], "array") is True
    assert _validate_simple_type("not array", "array") is False


def test_validate_simple_type_object():
    assert _validate_simple_type({"a": 1}, "object") is True
    assert _validate_simple_type([1], "object") is False


def test_validate_simple_type_unknown():
    assert _validate_simple_type("anything", "unknown") is True


def test_validate_tool_arguments_schema_missing_required():
    with pytest.raises(ValueError, match="缺少必填参数"):
        _validate_tool_arguments_schema(
            tool_name="test_tool",
            arguments={},
            parameters={"type": "object", "required": ["query"], "properties": {"query": {"type": "string"}}},
        )


def test_validate_tool_arguments_schema_unknown_keys_rejected():
    with pytest.raises(ValueError, match="未声明字段"):
        _validate_tool_arguments_schema(
            tool_name="test_tool",
            arguments={"query": "hi", "extra": "bad"},
            parameters={
                "type": "object",
                "additionalProperties": False,
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        )


def test_validate_tool_arguments_schema_type_mismatch():
    with pytest.raises(ValueError, match="类型错误"):
        _validate_tool_arguments_schema(
            tool_name="test_tool",
            arguments={"count": "not_int"},
            parameters={
                "type": "object",
                "properties": {"count": {"type": "integer"}},
            },
        )


def test_validate_tool_arguments_schema_array_item_type():
    with pytest.raises(ValueError, match="类型错误"):
        _validate_tool_arguments_schema(
            tool_name="test_tool",
            arguments={"ids": [1, "bad", 3]},
            parameters={
                "type": "object",
                "properties": {"ids": {"type": "array", "items": {"type": "integer"}}},
            },
        )


def test_validate_tool_arguments_schema_enum():
    with pytest.raises(ValueError, match="枚举值"):
        _validate_tool_arguments_schema(
            tool_name="test_tool",
            arguments={"status": "unknown"},
            parameters={
                "type": "object",
                "properties": {"status": {"type": "string", "enum": ["active", "closed"]}},
            },
        )


def test_validate_tool_arguments_schema_minimum():
    with pytest.raises(ValueError, match="小于最小值"):
        _validate_tool_arguments_schema(
            tool_name="test_tool",
            arguments={"limit": 0},
            parameters={
                "type": "object",
                "properties": {"limit": {"type": "integer", "minimum": 1}},
            },
        )


def test_validate_tool_arguments_schema_maximum():
    with pytest.raises(ValueError, match="超过最大值"):
        _validate_tool_arguments_schema(
            tool_name="test_tool",
            arguments={"limit": 100},
            parameters={
                "type": "object",
                "properties": {"limit": {"type": "integer", "maximum": 16}},
            },
        )


def test_validate_tool_arguments_schema_non_object_type():
    with pytest.raises(ValueError, match="仅支持 object"):
        _validate_tool_arguments_schema(
            tool_name="test_tool",
            arguments={"a": 1},
            parameters={"type": "array"},
        )


def test_normalize_builtin_tool_arguments_search_limit_none():
    result = _normalize_builtin_tool_arguments(tool_name="search_skill_context", arguments={"query": "test"})
    assert "limit" not in result


def test_normalize_builtin_tool_arguments_search_limit_valid():
    result = _normalize_builtin_tool_arguments(
        tool_name="search_skill_context", arguments={"query": "test", "limit": 5}
    )
    assert result["limit"] == 5


def test_normalize_builtin_tool_arguments_search_limit_string():
    result = _normalize_builtin_tool_arguments(
        tool_name="search_skill_context", arguments={"query": "test", "limit": "5"}
    )
    assert result["limit"] == 5


def test_normalize_builtin_tool_arguments_search_limit_invalid_string():
    result = _normalize_builtin_tool_arguments(
        tool_name="search_skill_context", arguments={"query": "test", "limit": "abc"}
    )
    assert "limit" not in result


def test_normalize_builtin_tool_arguments_search_limit_too_low():
    result = _normalize_builtin_tool_arguments(
        tool_name="search_skill_context", arguments={"query": "test", "limit": -1}
    )
    assert result["limit"] >= 1


def test_normalize_builtin_tool_arguments_search_limit_too_high():
    result = _normalize_builtin_tool_arguments(
        tool_name="search_skill_context", arguments={"query": "test", "limit": 999}
    )
    assert result["limit"] <= 16


def test_normalize_builtin_tool_arguments_non_search():
    result = _normalize_builtin_tool_arguments(
        tool_name="read_skill_file", arguments={"relative_path": "test.md", "limit": 5}
    )
    assert result["limit"] == 5


def test_build_builtin_tool_parameters_list_directory():
    params = _build_builtin_tool_parameters("list_skill_directory")
    assert params is not None
    assert "relative_path" in params["properties"]


def test_build_builtin_tool_parameters_read_file():
    params = _build_builtin_tool_parameters("read_skill_file")
    assert params is not None
    assert "relative_path" in params["required"]


def test_build_builtin_tool_parameters_search():
    params = _build_builtin_tool_parameters("search_skill_context")
    assert params is not None
    assert "query" in params["required"]


def test_build_builtin_tool_parameters_read_context():
    params = _build_builtin_tool_parameters("read_skill_context")
    assert params is not None
    assert "chunk_ids" in params["required"]


def test_build_builtin_tool_parameters_unknown():
    assert _build_builtin_tool_parameters("unknown_tool") is None
