from doc_process_studio.skill.infrastructure.tool_loop.skill_files import (
    _categorize_relative_path,
    _normalize_relative_path,
    _resolve_search_limit_bounds,
    compose_scoped_tool_name,
    split_scoped_tool_name,
)


def test_compose_scoped_tool_name() -> None:
    assert compose_scoped_tool_name("skill-1", "tool_a") == "skill-1::tool_a"


def test_split_scoped_tool_name_with_scope() -> None:
    skill_id, tool_name = split_scoped_tool_name("skill-1::tool_a")
    assert skill_id == "skill-1"
    assert tool_name == "tool_a"


def test_split_scoped_tool_name_without_scope() -> None:
    skill_id, tool_name = split_scoped_tool_name("tool_a")
    assert skill_id is None
    assert tool_name == "tool_a"


def test_split_scoped_tool_name_empty_skill() -> None:
    skill_id, tool_name = split_scoped_tool_name("::tool_a")
    assert skill_id is None
    assert tool_name == "tool_a"


def test_normalize_relative_path_empty() -> None:
    assert _normalize_relative_path("") == "."
    assert _normalize_relative_path(None) == "."


def test_normalize_relative_path_dot() -> None:
    assert _normalize_relative_path(".") == "."


def test_normalize_relative_path_normal() -> None:
    assert _normalize_relative_path("references/doc.md") == "references/doc.md"


def test_normalize_relative_path_backslash() -> None:
    assert _normalize_relative_path("references\\doc.md") == "references/doc.md"


def test_categorize_relative_path_skill() -> None:
    assert _categorize_relative_path(".") == "skill"
    assert _categorize_relative_path("SKILL.md") == "skill"


def test_categorize_relative_path_reference() -> None:
    assert _categorize_relative_path("references") == "reference"
    assert _categorize_relative_path("references/doc.md") == "reference"


def test_categorize_relative_path_script() -> None:
    assert _categorize_relative_path("scripts") == "script"
    assert _categorize_relative_path("scripts/run.py") == "script"


def test_categorize_relative_path_asset() -> None:
    assert _categorize_relative_path("assets") == "asset"
    assert _categorize_relative_path("assets/template.docx") == "asset"


def test_categorize_relative_path_other() -> None:
    assert _categorize_relative_path("unknown/file.txt") == "other"


def test_resolve_search_limit_bounds() -> None:
    default, maximum = _resolve_search_limit_bounds()
    assert default >= 1
    assert maximum >= default
