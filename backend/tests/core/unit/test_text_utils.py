from doc_process_studio.common.utils.text_utils import parse_json_object


def test_parse_json_object_valid_dict() -> None:
    result = parse_json_object('{"key": "value"}')
    assert result == {"key": "value"}


def test_parse_json_object_empty_string() -> None:
    assert parse_json_object("") is None


def test_parse_json_object_whitespace_only() -> None:
    assert parse_json_object("   ") is None


def test_parse_json_object_invalid_json() -> None:
    assert parse_json_object("not json") is None


def test_parse_json_object_json_array() -> None:
    assert parse_json_object("[1,2,3]") is None


def test_parse_json_object_markdown_wrapped() -> None:
    result = parse_json_object('```json\n{"key": "value"}\n```')
    assert result == {"key": "value"}


def test_parse_json_object_markdown_without_language() -> None:
    result = parse_json_object('```\n{"key": "value"}\n```')
    assert result == {"key": "value"}


def test_parse_json_object_embedded_in_text() -> None:
    result = parse_json_object('some text {"key": "value"} more text')
    assert result == {"key": "value"}


def test_parse_json_object_nested_braces() -> None:
    result = parse_json_object('{"outer": {"inner": "value"}}')
    assert result == {"outer": {"inner": "value"}}
