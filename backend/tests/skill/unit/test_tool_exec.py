
from doc_process_studio.skill.service.tool_loop.tool_exec import (
    _normalize_json_like_punctuation,
    _normalize_text_to_chaptered_document,
    _strip_wrapped_code_fence,
    _apply_json_file_text_normalizer,
    _format_declared_tool_default_name,
    _try_parse_json_like_value,
)


def test_strip_wrapped_code_fence_json():
    assert _strip_wrapped_code_fence('```json\n{"a":1}\n```') == '{"a":1}'


def test_strip_wrapped_code_fence_yaml():
    assert _strip_wrapped_code_fence('```yaml\nkey: val\n```') == 'key: val'


def test_strip_wrapped_code_fence_no_fence():
    assert _strip_wrapped_code_fence('{"a":1}') == '{"a":1}'


def test_strip_wrapped_code_fence_incomplete():
    assert _strip_wrapped_code_fence('```\nonly one') == '```\nonly one'


def test_normalize_text_to_chaptered_document_empty():
    assert _normalize_text_to_chaptered_document("") is None


def test_normalize_text_to_chaptered_document_plain():
    result = _normalize_text_to_chaptered_document("纯文本内容")
    assert result is not None
    assert "chapters" in result
    assert len(result["chapters"]) == 1


def test_normalize_text_to_chaptered_document_heading():
    text = "# 第一章\n正文内容\n## 1.1 小节\n小节内容"
    result = _normalize_text_to_chaptered_document(text)
    assert result is not None
    assert len(result["chapters"]) >= 1
    assert result["chapters"][0]["title"] == "第一章"


def test_normalize_text_to_chaptered_document_nested():
    text = "# 第一章\n正文\n## 1.1 小节\n小节内容\n## 1.2 小节二\n内容二"
    result = _normalize_text_to_chaptered_document(text)
    assert result is not None
    assert len(result["chapters"][0]["sections"]) == 2


def test_apply_json_file_text_normalizer_none():
    assert _apply_json_file_text_normalizer(
        argument_name="test", normalized_text="text", text_normalizer=None
    ) is None


def test_apply_json_file_text_normalizer_chaptered():
    result = _apply_json_file_text_normalizer(
        argument_name="test",
        normalized_text="# 标题\n正文",
        text_normalizer="chaptered_document",
    )
    assert result is not None
    assert "chapters" in result


def test_apply_json_file_text_normalizer_unsupported():
    try:
        _apply_json_file_text_normalizer(
            argument_name="test",
            normalized_text="text",
            text_normalizer="unsupported",
        )
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_normalize_json_like_punctuation():
    assert _normalize_json_like_punctuation('{"a"："b"，"c"："d"}') == '{"a":"b","c":"d"}'


def test_normalize_json_like_punctuation_in_string():
    result = _normalize_json_like_punctuation('{"text":"中文，冒号："}')
    assert "中文，冒号：" in result


def test_try_parse_json_like_value_valid():
    result = _try_parse_json_like_value('{"a":1}')
    assert result == {"a": 1}


def test_try_parse_json_like_value_invalid():
    assert _try_parse_json_like_value("not json") is None


def test_try_parse_json_like_value_double_encoded():
    result = _try_parse_json_like_value('"{\\"a\\":1}"')
    assert result == {"a": 1}


def test_format_declared_tool_default_name():
    from doc_process_studio.skill.schemas.catalog import SkillToolConfig
    tool = SkillToolConfig.model_validate({
        "name": "my_tool",
        "description": "test",
        "kind": "script",
        "path": "scripts/test.py",
        "parameters": {"type": "object", "properties": {}},
        "execution": {
            "runtime": "python",
            "arg_bindings": {},
        },
    })
    result = _format_declared_tool_default_name(tool, {"key": "value"})
    assert "my_tool" in result
