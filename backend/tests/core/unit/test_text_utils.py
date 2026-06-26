from doc_process_studio.common.utils.text_utils import parse_json_object


def test_parse_json_object_valid_dict():
    result = parse_json_object('{"key": "value"}')
    assert result == {"key": "value"}


def test_parse_json_object_empty_string():
    assert parse_json_object("") is None


def test_parse_json_object_whitespace_only():
    assert parse_json_object("   ") is None


def test_parse_json_object_invalid_json():
    assert parse_json_object("not json") is None


def test_parse_json_object_json_array():
    assert parse_json_object("[1,2,3]") is None


def test_parse_json_object_markdown_wrapped():
    result = parse_json_object('```json\n{"key": "value"}\n```')
    assert result == {"key": "value"}


def test_parse_json_object_markdown_without_language():
    result = parse_json_object('```\n{"key": "value"}\n```')
    assert result == {"key": "value"}


def test_parse_json_object_embedded_in_text():
    result = parse_json_object('some text {"key": "value"} more text')
    assert result == {"key": "value"}


def test_parse_json_object_nested_braces():
    result = parse_json_object('{"outer": {"inner": "value"}}')
    assert result == {"outer": {"inner": "value"}}
