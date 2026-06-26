"""测试 kb: skill 在整个 skill 系统中的动态加载流程。

这些测试覆盖了之前遗漏的关键路径：
- get_skill_interface 对 kb: skill 应抛出 ValueError（不在静态注册表）
- build_skill_prompt 对 kb: skill 应返回知识库 RAG prompt
- _build_skills_catalog_lines 对 kb: skill 应正确生成目录行
- build_skill_tools_for_skills 混合 kb: 和普通 skill 不应报错
- _prepare_skill_context 中 kb: skill 应正确构建状态
"""

import pytest

# ── get_skill_interface 对 kb: skill 应抛出 ValueError ──


def test_get_skill_interface_raises_for_kb_skill() -> None:
    from doc_process_studio.skill.infrastructure.registry import get_skill_interface

    with pytest.raises(ValueError, match="未找到 skill"):
        get_skill_interface("kb:出租车平台")


def test_get_skill_interface_raises_for_kb_empty() -> None:
    from doc_process_studio.skill.infrastructure.registry import get_skill_interface

    with pytest.raises(ValueError, match="未找到 skill"):
        get_skill_interface("kb:")


# ── build_skill_prompt 对 kb: skill 返回 RAG prompt ──


def test_build_skill_prompt_kb_skill() -> None:
    from doc_process_studio.chat.infrastructure.streaming.context import build_skill_prompt

    prompt = build_skill_prompt("kb:TestProject")
    assert "TestProject" in prompt
    assert len(prompt) > 0


def test_build_skill_prompt_kb_skill_chinese_name() -> None:
    from doc_process_studio.chat.infrastructure.streaming.context import build_skill_prompt

    prompt = build_skill_prompt("kb:出租车平台")
    assert "出租车平台" in prompt


def test_build_skill_prompt_regular_skill() -> None:
    from doc_process_studio.chat.infrastructure.streaming.context import build_skill_prompt

    # document-assistant 是静态注册的 skill
    prompt = build_skill_prompt("document-assistant")
    assert len(prompt) > 0


# ── _build_skills_catalog_lines 对 kb: skill 生成目录行 ──


def test_build_skills_catalog_lines_with_kb_skill() -> None:
    from doc_process_studio.chat.infrastructure.streaming.context import _build_skills_catalog_lines

    lines = _build_skills_catalog_lines(["document-assistant", "kb:TestProject"])
    kb_lines = [line for line in lines if "kb:TestProject" in line]
    assert len(kb_lines) == 1
    assert "知识库 RAG" in kb_lines[0]


def test_build_skills_catalog_lines_kb_skill_chinese() -> None:
    from doc_process_studio.chat.infrastructure.streaming.context import _build_skills_catalog_lines

    lines = _build_skills_catalog_lines(["kb:出租车平台"])
    assert len(lines) == 1
    assert "出租车平台" in lines[0]
    assert "知识库 RAG" in lines[0]


def test_build_skills_catalog_lines_mixed_skills() -> None:
    from doc_process_studio.chat.infrastructure.streaming.context import _build_skills_catalog_lines

    lines = _build_skills_catalog_lines(["document-assistant", "kb:TestProject"])
    assert len(lines) == 2
    doc_line = [line for line in lines if "document-assistant" in line][0]
    kb_line = [line for line in lines if "kb:TestProject" in line][0]
    assert "SKILL.md" in doc_line
    assert "知识库 RAG" in kb_line


# ── build_skill_tools_for_skills 混合 kb: 和普通 skill ──


def test_build_skill_tools_for_skills_kb_only() -> None:
    from doc_process_studio.skill.infrastructure.tool_loop.tool_schema import build_skill_tools_for_skills

    tools = build_skill_tools_for_skills(["kb:TestProject"])
    assert len(tools) >= 1
    tool_names = [t["function"]["name"] for t in tools]
    assert "search_knowledge_base" in tool_names


def test_build_skill_tools_for_skills_mixed() -> None:
    from doc_process_studio.skill.infrastructure.tool_loop.tool_schema import build_skill_tools_for_skills

    tools = build_skill_tools_for_skills(["document-assistant", "kb:TestProject"])
    tool_names = [t["function"]["name"] for t in tools]
    assert "search_knowledge_base" in tool_names
    # document-assistant 的内置工具也应存在
    assert "list_skill_directory" in tool_names


def test_build_skill_tools_for_skills_multiple_kb() -> None:
    from doc_process_studio.skill.infrastructure.tool_loop.tool_schema import build_skill_tools_for_skills

    tools = build_skill_tools_for_skills(["kb:ProjectA", "kb:ProjectB"])
    assert len(tools) == 2
    for tool in tools:
        assert tool["function"]["name"] == "search_knowledge_base"


# ── _build_direct_skill_plan 对 kb: skill 的处理 ──


def test_build_direct_skill_plan_with_kb_skill() -> None:
    from doc_process_studio.chat.infrastructure.stream import _build_direct_skill_plan
    from doc_process_studio.chat.router.schemas.request import ChatMessageInput, ChatStreamRequest

    request = ChatStreamRequest(
        user_message_id="msg-001",
        conversation_id="test-conv",
        model="test-model",
        messages=[ChatMessageInput(role="user", content="hello")],
        selected_skill_ids=["kb:TestProject"],
    )
    plan = _build_direct_skill_plan(request=request)
    assert "kb:TestProject" in plan.active_skill_ids
    assert plan.primary_skill_id == "kb:TestProject"


def test_build_direct_skill_plan_kb_skill_not_in_missing() -> None:
    from doc_process_studio.chat.infrastructure.stream import _build_direct_skill_plan
    from doc_process_studio.chat.router.schemas.request import ChatMessageInput, ChatStreamRequest

    request = ChatStreamRequest(
        user_message_id="msg-001",
        conversation_id="test-conv",
        model="test-model",
        messages=[ChatMessageInput(role="user", content="hello")],
        selected_skill_ids=["kb:TestProject"],
    )
    plan = _build_direct_skill_plan(request=request)
    assert "kb:TestProject" not in plan.missing_explicit_skill_ids


def test_build_direct_skill_plan_mixed_skills() -> None:
    from doc_process_studio.chat.infrastructure.stream import _build_direct_skill_plan
    from doc_process_studio.chat.router.schemas.request import ChatMessageInput, ChatStreamRequest

    request = ChatStreamRequest(
        user_message_id="msg-001",
        conversation_id="test-conv",
        model="test-model",
        messages=[ChatMessageInput(role="user", content="hello")],
        selected_skill_ids=["document-assistant", "kb:TestProject"],
    )
    plan = _build_direct_skill_plan(request=request)
    assert "document-assistant" in plan.active_skill_ids
    assert "kb:TestProject" in plan.active_skill_ids


# ── context.py 中 kb: skill 辅助函数 ──


def test_context_is_kb_skill_id() -> None:
    from doc_process_studio.chat.infrastructure.streaming.context import is_kb_skill_id

    assert is_kb_skill_id("kb:TestProject") is True
    assert is_kb_skill_id("document-assistant") is False


def test_context_extract_kb_project_name() -> None:
    from doc_process_studio.chat.infrastructure.streaming.context import extract_kb_project_name

    assert extract_kb_project_name("kb:出租车平台") == "出租车平台"
    assert extract_kb_project_name("kb:") == ""
    assert extract_kb_project_name("other") == ""


def test_context_build_kb_skill_interface() -> None:
    from doc_process_studio.chat.infrastructure.streaming.context import build_kb_skill_interface

    interface = build_kb_skill_interface("出租车平台")
    assert interface.id == "kb:出租车平台"
    assert "出租车平台" in interface.display_name
    assert interface.skill_type == "chat"
    assert len(interface.default_prompt) > 0
