import json

import pytest

from doc_process_studio.services.skill.tool_loop import _coerce_json_file_argument


def test_coerce_json_file_argument_accepts_object_and_list() -> None:
    payload_object = {"chapters": [{"title": "章节一", "content": "正文"}]}
    assert _coerce_json_file_argument("doc_plan", payload_object) == payload_object

    payload_list = [{"title": "章节一", "content": "正文"}]
    assert _coerce_json_file_argument("doc_plan", payload_list) == payload_list


def test_coerce_json_file_argument_accepts_json_string() -> None:
    payload = '{"chapters":[{"title":"章节一","content":"正文"}]}'
    parsed = _coerce_json_file_argument("doc_plan", payload)
    assert isinstance(parsed, dict)
    assert parsed["chapters"][0]["title"] == "章节一"


def test_coerce_json_file_argument_accepts_double_encoded_json_string() -> None:
    payload = json.dumps('{"chapters":[{"title":"章节一"}]}')
    parsed = _coerce_json_file_argument("doc_plan", payload)
    assert isinstance(parsed, dict)
    assert parsed["chapters"][0]["title"] == "章节一"


def test_coerce_json_file_argument_accepts_yaml_string() -> None:
    payload = """
chapters:
  - title: 章节一
    content: 正文
"""
    parsed = _coerce_json_file_argument("doc_plan", payload)
    assert isinstance(parsed, dict)
    assert parsed["chapters"][0]["title"] == "章节一"


def test_coerce_json_file_argument_accepts_markdown_outline() -> None:
    payload = """
# 第一章 项目概述
这里是概述正文。

## 1.1 建设目标
这里是目标正文。
"""
    parsed = _coerce_json_file_argument("doc_plan", payload)
    assert isinstance(parsed, dict)
    assert parsed["chapters"][0]["title"] == "第一章 项目概述"
    assert parsed["chapters"][0]["sections"][0]["title"] == "1.1 建设目标"


def test_coerce_json_file_argument_accepts_plain_text_doc_plan() -> None:
    parsed = _coerce_json_file_argument("doc_plan", "这是整理好的正文草稿。")
    assert isinstance(parsed, dict)
    assert parsed["chapters"][0]["title"] == "文档内容"
    assert "正文草稿" in parsed["chapters"][0]["content"]


def test_coerce_json_file_argument_rejects_invalid_string() -> None:
    with pytest.raises(ValueError, match="JSON/YAML"):
        _coerce_json_file_argument("other_argument", "这不是 JSON")
