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


def test_coerce_json_file_argument_rejects_invalid_string() -> None:
    with pytest.raises(ValueError, match="无法解析为 JSON"):
        _coerce_json_file_argument("doc_plan", "这不是 JSON")
