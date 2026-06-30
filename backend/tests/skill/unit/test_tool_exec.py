import pytest

from doc_process_studio.skill.infrastructure.tool_loop.tool_exec import (
    _apply_json_file_text_normalizer,
    _format_declared_tool_default_name,
    _normalize_json_like_punctuation,
    _normalize_text_to_chaptered_document,
    _strip_wrapped_code_fence,
    _try_parse_json_like_value,
)


def test_strip_wrapped_code_fence_json() -> None:
    assert _strip_wrapped_code_fence('```json\n{"a":1}\n```') == '{"a":1}'


def test_strip_wrapped_code_fence_yaml() -> None:
    assert _strip_wrapped_code_fence("```yaml\nkey: val\n```") == "key: val"


def test_strip_wrapped_code_fence_no_fence() -> None:
    assert _strip_wrapped_code_fence('{"a":1}') == '{"a":1}'


def test_strip_wrapped_code_fence_incomplete() -> None:
    assert _strip_wrapped_code_fence("```\nonly one") == "```\nonly one"


def test_normalize_text_to_chaptered_document_empty() -> None:
    assert _normalize_text_to_chaptered_document("") is None


def test_normalize_text_to_chaptered_document_plain() -> None:
    result = _normalize_text_to_chaptered_document("纯文本内容")
    assert result is not None
    assert "chapters" in result
    assert len(result["chapters"]) == 1


def test_normalize_text_to_chaptered_document_heading() -> None:
    text = "# 第一章\n正文内容\n## 1.1 小节\n小节内容"
    result = _normalize_text_to_chaptered_document(text)
    assert result is not None
    assert len(result["chapters"]) >= 1
    assert result["chapters"][0]["title"] == "第一章"


def test_normalize_text_to_chaptered_document_nested() -> None:
    text = "# 第一章\n正文\n## 1.1 小节\n小节内容\n## 1.2 小节二\n内容二"
    result = _normalize_text_to_chaptered_document(text)
    assert result is not None
    assert len(result["chapters"][0]["sections"]) == 2


def test_apply_json_file_text_normalizer_none() -> None:
    assert _apply_json_file_text_normalizer(argument_name="test", normalized_text="text", text_normalizer=None) is None


def test_apply_json_file_text_normalizer_chaptered() -> None:
    result = _apply_json_file_text_normalizer(
        argument_name="test",
        normalized_text="# 标题\n正文",
        text_normalizer="chaptered_document",
    )
    assert result is not None
    assert "chapters" in result


def test_apply_json_file_text_normalizer_unsupported() -> None:
    with pytest.raises(ValueError):
        _apply_json_file_text_normalizer(
            argument_name="test",
            normalized_text="text",
            text_normalizer="unsupported",
        )


def test_normalize_json_like_punctuation() -> None:
    assert _normalize_json_like_punctuation('{"a"："b"，"c"："d"}') == '{"a":"b","c":"d"}'


def test_normalize_json_like_punctuation_in_string() -> None:
    result = _normalize_json_like_punctuation('{"text":"中文，冒号："}')
    assert "中文，冒号：" in result


def test_try_parse_json_like_value_valid() -> None:
    result = _try_parse_json_like_value('{"a":1}')
    assert result == {"a": 1}


def test_try_parse_json_like_value_invalid() -> None:
    assert _try_parse_json_like_value("not json") is None


def test_try_parse_json_like_value_double_encoded() -> None:
    result = _try_parse_json_like_value('"{\\"a\\":1}"')
    assert result == {"a": 1}


def test_format_declared_tool_default_name() -> None:
    from doc_process_studio.skill.application.dtos.catalog import SkillToolConfig

    tool = SkillToolConfig.model_validate(
        {
            "name": "my_tool",
            "description": "test",
            "kind": "script",
            "path": "scripts/test.py",
            "parameters": {"type": "object", "properties": {}},
            "execution": {
                "runtime": "python",
                "arg_bindings": {},
            },
        }
    )
    result = _format_declared_tool_default_name(tool, {"key": "value"})
    assert "my_tool" in result
