from typing import Any

from doc_process_studio.skill.infrastructure.tool_loop.tool_status import (
    _build_builtin_status_label,
    _format_short_path,
    _get_read_context_relative_path,
)


def test_build_builtin_status_label_list_directory() -> None:
    assert "查看" in _build_builtin_status_label("list_skill_directory")


def test_build_builtin_status_label_list_reference() -> None:
    assert "参考" in _build_builtin_status_label("list_skill_directory", "references/doc.md")


def test_build_builtin_status_label_list_script() -> None:
    assert "脚本" in _build_builtin_status_label("list_skill_directory", "scripts/gen.py")


def test_build_builtin_status_label_list_asset() -> None:
    assert "模板" in _build_builtin_status_label("list_skill_directory", "assets/template.docx")


def test_build_builtin_status_label_read_file() -> None:
    assert "读取" in _build_builtin_status_label("read_skill_file")


def test_build_builtin_status_label_read_reference() -> None:
    assert "参考" in _build_builtin_status_label("read_skill_file", "references/doc.md")


def test_build_builtin_status_label_search() -> None:
    assert "检索" in _build_builtin_status_label("search_skill_context")


def test_build_builtin_status_label_search_reference() -> None:
    assert "参考" in _build_builtin_status_label("search_skill_context", "references/doc.md")


def test_build_builtin_status_label_read_context() -> None:
    assert "载入" in _build_builtin_status_label("read_skill_context")


def test_build_builtin_status_label_unknown() -> None:
    result = _build_builtin_status_label("unknown_tool")
    assert "unknown" in result.lower() or "tool" in result.lower()


def test_format_short_path_root() -> None:
    assert _format_short_path(".") == "根目录"


def test_format_short_path_relative() -> None:
    assert _format_short_path("references/doc.md") == "references/doc.md"


def test_format_short_path_none() -> None:
    assert _format_short_path(None) == "根目录"


def test_get_read_context_relative_path_with_chunks() -> None:
    tool_result = {
        "chunks": [
            {"source_path": "references/doc.md", "id": "c1"},
        ]
    }
    result = _get_read_context_relative_path(tool_result)
    assert result == "references/doc.md"


def test_get_read_context_relative_path_empty_chunks() -> None:
    tool_result: dict[str, Any] = {"chunks": []}
    result = _get_read_context_relative_path(tool_result)
    assert result is None


def test_get_read_context_relative_path_no_chunks() -> None:
    tool_result: dict[str, Any] = {}
    result = _get_read_context_relative_path(tool_result)
    assert result is None


def test_get_read_context_relative_path_non_string_source() -> None:
    tool_result = {"chunks": [{"source_path": 123}]}
    result = _get_read_context_relative_path(tool_result)
    assert result is None


def test_get_read_context_relative_path_empty_source() -> None:
    tool_result = {"chunks": [{"source_path": "  "}]}
    result = _get_read_context_relative_path(tool_result)
    assert result is None
