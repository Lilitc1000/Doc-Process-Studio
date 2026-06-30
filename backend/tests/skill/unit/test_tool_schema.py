from unittest.mock import MagicMock

import pytest

from doc_process_studio.skill.infrastructure.tool_loop.tool_schema import (
    build_skill_tools,
    build_skill_tools_for_skills,
)


def test_build_skill_tools_includes_builtin(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_interface = MagicMock()
    fake_interface.tools = []
    monkeypatch.setattr(
        "doc_process_studio.skill.infrastructure.tool_loop.tool_schema.get_skill_interface",
        lambda _sid: fake_interface,
    )
    tools = build_skill_tools("test-skill")
    tool_names = [t["function"]["name"] for t in tools]
    assert "list_skill_directory" in tool_names
    assert "read_skill_file" in tool_names
    assert "search_skill_context" in tool_names
    assert "read_skill_context" in tool_names


def test_build_skill_tools_includes_declared(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_tool = MagicMock()
    fake_tool.name = "custom_tool"
    fake_tool.description = "自定义工具"
    fake_tool.parameters = {"type": "object", "properties": {}}

    fake_interface = MagicMock()
    fake_interface.tools = [fake_tool]
    monkeypatch.setattr(
        "doc_process_studio.skill.infrastructure.tool_loop.tool_schema.get_skill_interface",
        lambda _sid: fake_interface,
    )
    tools = build_skill_tools("test-skill")
    tool_names = [t["function"]["name"] for t in tools]
    assert "custom_tool" in tool_names


def test_build_skill_tools_for_skills_empty() -> None:
    result = build_skill_tools_for_skills([])
    assert result == []


def test_build_skill_tools_for_skills_dedup(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_interface = MagicMock()
    fake_interface.tools = []
    monkeypatch.setattr(
        "doc_process_studio.skill.infrastructure.tool_loop.tool_schema.get_skill_interface",
        lambda _sid: fake_interface,
    )
    result = build_skill_tools_for_skills(["skill-a", "skill-a", "  ", "skill-b"])
    tool_names = [t["function"]["name"] for t in result]
    assert "list_skill_directory" in tool_names


def test_build_skill_tools_for_skills_includes_skill_id_param(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_interface = MagicMock()
    fake_interface.tools = []
    monkeypatch.setattr(
        "doc_process_studio.skill.infrastructure.tool_loop.tool_schema.get_skill_interface",
        lambda _sid: fake_interface,
    )
    tools = build_skill_tools_for_skills(["skill-a"])
    list_dir_tool = next(t for t in tools if t["function"]["name"] == "list_skill_directory")
    props = list_dir_tool["function"]["parameters"]["properties"]
    assert "skill_id" in props


def test_build_skill_tools_for_skills_scoped_declared(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_tool = MagicMock()
    fake_tool.name = "custom_tool"
    fake_tool.description = "自定义工具"
    fake_tool.parameters = {"type": "object", "properties": {}}

    fake_interface = MagicMock()
    fake_interface.display_name = "测试技能"
    fake_interface.tools = [fake_tool]

    import doc_process_studio.skill.infrastructure.tool_loop.tool_schema as schema_module

    monkeypatch.setattr(
        schema_module,
        "get_skill_interface",
        lambda _sid: fake_interface,
    )
    tools = build_skill_tools_for_skills(["skill-a"])
    declared = [
        t
        for t in tools
        if t["function"]["name"]
        not in {
            "list_skill_directory",
            "read_skill_file",
            "search_skill_context",
            "read_skill_context",
        }
    ]
    assert len(declared) == 1
    assert "skill-a" in declared[0]["function"]["name"]
    assert "测试技能" in declared[0]["function"]["description"]
