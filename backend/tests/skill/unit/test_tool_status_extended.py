from unittest.mock import MagicMock, patch

from doc_process_studio.chat.application.dtos.attachment import ChatAttachment
from doc_process_studio.skill.infrastructure.tool_loop.tool_status import (
    _build_builtin_tool_status,
    _build_declared_tool_status,
    _build_reused_tool_status,
    build_tool_status_finish,
    build_tool_status_start,
)


def _make_attachment(**overrides) -> ChatAttachment:
    defaults = dict(
        attachment_id="att-1",
        name="report.docx",
        source="generated",
        size_label="10 KB",
        size_bytes=10240,
        download_url="/api/attachments/att-1/download",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        expires_at="2026-12-31T00:00:00Z",
    )
    defaults.update(overrides)
    return ChatAttachment(**defaults)


def _make_tool_call(function_name="list_skill_directory", arguments=None):
    return {
        "function": {
            "name": function_name,
            "arguments": arguments or "{}",
        }
    }


def test_build_tool_status_start_list_directory():
    tool_call = _make_tool_call("list_skill_directory", '{"relative_path": "references/"}')
    result = build_tool_status_start(skill_id="test-skill", tool_call=tool_call)
    assert "label" in result
    assert "message" in result
    assert "查看" in result["label"]


def test_build_tool_status_start_read_file():
    tool_call = _make_tool_call("read_skill_file", '{"relative_path": "README.md"}')
    result = build_tool_status_start(skill_id="test-skill", tool_call=tool_call)
    assert "读取" in result["label"]


def test_build_tool_status_start_search_context():
    tool_call = _make_tool_call("search_skill_context", '{"query": "test"}')
    result = build_tool_status_start(skill_id="test-skill", tool_call=tool_call)
    assert "检索" in result["label"]


def test_build_tool_status_start_search_context_with_source():
    tool_call = _make_tool_call("search_skill_context", '{"query": "test", "source_path": "references/"}')
    result = build_tool_status_start(skill_id="test-skill", tool_call=tool_call)
    assert "检索" in result["label"]


def test_build_tool_status_start_read_context():
    tool_call = _make_tool_call("read_skill_context", '{"chunk_ids": ["c1", "c2"]}')
    with patch(
        "doc_process_studio.skill.infrastructure.tool_loop.tool_status.get_skill_context_chunks_by_ids",
        return_value=[],
    ):
        result = build_tool_status_start(skill_id="test-skill", tool_call=tool_call)
    assert "载入" in result["label"]


def test_build_tool_status_start_declared_tool():
    mock_tool_config = MagicMock()
    mock_tool_config.status = MagicMock()
    mock_tool_config.status.label = "自定义标签"
    mock_tool_config.status.start = "正在执行自定义操作"
    mock_tool_config.description = "自定义工具"

    tool_call = _make_tool_call("custom_tool", '{"param": "value"}')
    with patch(
        "doc_process_studio.skill.infrastructure.tool_loop.tool_status.get_skill_tool_config",
        return_value=mock_tool_config,
    ):
        result = build_tool_status_start(skill_id="test-skill", tool_call=tool_call)
    assert result["label"] == "自定义标签"
    assert result["message"] == "正在执行自定义操作"


def test_build_tool_status_start_declared_tool_no_status():
    mock_tool_config = MagicMock()
    mock_tool_config.status = None
    mock_tool_config.description = "无状态工具"

    tool_call = _make_tool_call("custom_tool", '{"param": "value"}')
    with patch(
        "doc_process_studio.skill.infrastructure.tool_loop.tool_status.get_skill_tool_config",
        return_value=mock_tool_config,
    ):
        result = build_tool_status_start(skill_id="test-skill", tool_call=tool_call)
    assert "无状态工具" in result["label"]


def test_build_tool_status_start_unknown_tool():
    tool_call = _make_tool_call("unknown_tool", "{}")
    with patch(
        "doc_process_studio.skill.infrastructure.tool_loop.tool_status.get_skill_tool_config",
        side_effect=ValueError("not found"),
    ):
        result = build_tool_status_start(skill_id="test-skill", tool_call=tool_call)
    assert "执行工具" in result["label"]


def test_build_reused_tool_status_list_directory():
    result = _build_reused_tool_status(
        tool_name="list_skill_directory",
        arguments={"relative_path": "references/"},
        tool_result={"reused": True},
    )
    assert result is not None
    assert "不再重复" in result["message"]


def test_build_reused_tool_status_read_file():
    result = _build_reused_tool_status(
        tool_name="read_skill_file",
        arguments={"relative_path": "README.md"},
        tool_result={"reused": True},
    )
    assert result is not None
    assert "不再重复" in result["message"]


def test_build_reused_tool_status_search():
    result = _build_reused_tool_status(
        tool_name="search_skill_context",
        arguments={"source_path": "references/"},
        tool_result={"reused": True},
    )
    assert result is not None
    assert "不再重复" in result["message"]


def test_build_reused_tool_status_read_context():
    result = _build_reused_tool_status(
        tool_name="read_skill_context",
        arguments={"chunk_ids": ["c1"]},
        tool_result={"reused": True, "chunks": [{"source_path": "refs/doc.md", "id": "c1"}]},
    )
    assert result is not None
    assert "不再重复" in result["message"]


def test_build_reused_tool_status_not_reused():
    result = _build_reused_tool_status(
        tool_name="list_skill_directory",
        arguments={},
        tool_result={"reused": False},
    )
    assert result is None


def test_build_reused_tool_status_other_tool():
    result = _build_reused_tool_status(
        tool_name="custom_tool",
        arguments={},
        tool_result={"reused": True},
    )
    assert result is None


def test_build_builtin_tool_status_list_directory():
    result = _build_builtin_tool_status(
        tool_name="list_skill_directory",
        arguments={"relative_path": "references/"},
        tool_result={},
    )
    assert result is not None
    assert "列出" in result["message"]


def test_build_builtin_tool_status_read_file():
    result = _build_builtin_tool_status(
        tool_name="read_skill_file",
        arguments={"relative_path": "README.md"},
        tool_result={},
    )
    assert result is not None
    assert "已读取" in result["message"]


def test_build_builtin_tool_status_search():
    result = _build_builtin_tool_status(
        tool_name="search_skill_context",
        arguments={"source_path": "references/"},
        tool_result={"chunks": [{"id": "c1"}, {"id": "c2"}]},
    )
    assert result is not None
    assert "2" in result["message"]


def test_build_builtin_tool_status_search_no_source():
    result = _build_builtin_tool_status(
        tool_name="search_skill_context",
        arguments={},
        tool_result={"chunks": [{"id": "c1"}]},
    )
    assert result is not None
    assert "1" in result["message"]


def test_build_builtin_tool_status_read_context():
    result = _build_builtin_tool_status(
        tool_name="read_skill_context",
        arguments={"chunk_ids": ["c1"]},
        tool_result={"loaded_chunk_ids": ["c1"], "chunks": [{"source_path": "refs/doc.md", "id": "c1"}]},
    )
    assert result is not None
    assert "1" in result["message"]


def test_build_builtin_tool_status_other():
    result = _build_builtin_tool_status(
        tool_name="custom_tool",
        arguments={},
        tool_result={},
    )
    assert result is None


def test_build_declared_tool_status_success():
    mock_tool_config = MagicMock()
    mock_tool_config.status = MagicMock()
    mock_tool_config.status.label = "生成报告"
    mock_tool_config.status.success = "报告已生成"
    mock_tool_config.description = "报告生成工具"

    with patch(
        "doc_process_studio.skill.infrastructure.tool_loop.tool_status.get_skill_tool_config",
        return_value=mock_tool_config,
    ):
        result = _build_declared_tool_status(
            resolved_skill_id="test-skill",
            tool_name="generate_report",
            tool_result={"ok": True},
            attachments=[],
        )
    assert result["message"] == "报告已生成"


def test_build_declared_tool_status_failure():
    mock_tool_config = MagicMock()
    mock_tool_config.status = MagicMock()
    mock_tool_config.status.label = "生成报告"
    mock_tool_config.status.failure = "生成失败"
    mock_tool_config.description = "报告生成工具"

    with patch(
        "doc_process_studio.skill.infrastructure.tool_loop.tool_status.get_skill_tool_config",
        return_value=mock_tool_config,
    ):
        result = _build_declared_tool_status(
            resolved_skill_id="test-skill",
            tool_name="generate_report",
            tool_result={"ok": False, "error": "权限不足"},
            attachments=[],
        )
    assert "生成失败" in result["message"]
    assert "权限不足" in result["message"]


def test_build_declared_tool_status_reused():
    mock_tool_config = MagicMock()
    mock_tool_config.status = MagicMock()
    mock_tool_config.status.label = "生成报告"
    mock_tool_config.description = "报告生成工具"

    with patch(
        "doc_process_studio.skill.infrastructure.tool_loop.tool_status.get_skill_tool_config",
        return_value=mock_tool_config,
    ):
        result = _build_declared_tool_status(
            resolved_skill_id="test-skill",
            tool_name="generate_report",
            tool_result={"reused": True},
            attachments=[],
        )
    assert "不再重复" in result["message"]


def test_build_declared_tool_status_with_single_attachment():
    mock_tool_config = MagicMock()
    mock_tool_config.status = None
    mock_tool_config.description = "生成工具"

    with patch(
        "doc_process_studio.skill.infrastructure.tool_loop.tool_status.get_skill_tool_config",
        return_value=mock_tool_config,
    ):
        result = _build_declared_tool_status(
            resolved_skill_id="test-skill",
            tool_name="generate_report",
            tool_result={"ok": True},
            attachments=[_make_attachment()],
        )
    assert "report.docx" in result["message"]


def test_build_declared_tool_status_with_multiple_attachments():
    mock_tool_config = MagicMock()
    mock_tool_config.status = None
    mock_tool_config.description = "生成工具"

    with patch(
        "doc_process_studio.skill.infrastructure.tool_loop.tool_status.get_skill_tool_config",
        return_value=mock_tool_config,
    ):
        result = _build_declared_tool_status(
            resolved_skill_id="test-skill",
            tool_name="generate_report",
            tool_result={"ok": True},
            attachments=[_make_attachment(), _make_attachment(attachment_id="att-2", name="other.docx")],
        )
    assert "2" in result["message"]


def test_build_declared_tool_status_no_attachments():
    mock_tool_config = MagicMock()
    mock_tool_config.status = None
    mock_tool_config.description = "通用工具"

    with patch(
        "doc_process_studio.skill.infrastructure.tool_loop.tool_status.get_skill_tool_config",
        return_value=mock_tool_config,
    ):
        result = _build_declared_tool_status(
            resolved_skill_id="test-skill",
            tool_name="custom_tool",
            tool_result={"ok": True},
            attachments=[],
        )
    assert "完成" in result["message"]


def test_build_declared_tool_status_unknown_tool():
    with patch(
        "doc_process_studio.skill.infrastructure.tool_loop.tool_status.get_skill_tool_config",
        side_effect=ValueError("not found"),
    ):
        result = _build_declared_tool_status(
            resolved_skill_id="test-skill",
            tool_name="unknown_tool",
            tool_result={"ok": False, "error": "未知工具"},
            attachments=[],
        )
    assert "失败" in result["message"]


def test_build_tool_status_finish_reused():
    from doc_process_studio.chat.router.schemas.request import ChatStreamRequest
    from doc_process_studio.skill.application.dtos.runtime import SkillConversationState

    request = MagicMock(spec=ChatStreamRequest)
    request.selected_skill_ids = ["test-skill"]
    state = MagicMock(spec=SkillConversationState)

    tool_call = _make_tool_call("list_skill_directory", '{"relative_path": "refs/"}')
    result = build_tool_status_finish(
        request=request,
        state=state,
        tool_call=tool_call,
        tool_result={"reused": True},
        attachments=[],
    )
    assert "不再重复" in result["message"]


def test_build_tool_status_finish_builtin():
    from doc_process_studio.chat.router.schemas.request import ChatStreamRequest
    from doc_process_studio.skill.application.dtos.runtime import SkillConversationState

    request = MagicMock(spec=ChatStreamRequest)
    request.selected_skill_ids = ["test-skill"]
    state = MagicMock(spec=SkillConversationState)

    tool_call = _make_tool_call("list_skill_directory", '{"relative_path": "refs/"}')
    result = build_tool_status_finish(
        request=request,
        state=state,
        tool_call=tool_call,
        tool_result={},
        attachments=[],
    )
    assert "列出" in result["message"]


def test_build_tool_status_finish_declared():
    from doc_process_studio.chat.router.schemas.request import ChatStreamRequest
    from doc_process_studio.skill.application.dtos.runtime import SkillConversationState

    request = MagicMock(spec=ChatStreamRequest)
    request.selected_skill_ids = ["test-skill"]
    state = MagicMock(spec=SkillConversationState)

    mock_tool_config = MagicMock()
    mock_tool_config.status = None
    mock_tool_config.description = "自定义工具"

    tool_call = _make_tool_call("custom_tool", "{}")
    with patch(
        "doc_process_studio.skill.infrastructure.tool_loop.tool_status.get_skill_tool_config",
        return_value=mock_tool_config,
    ):
        result = build_tool_status_finish(
            request=request,
            state=state,
            tool_call=tool_call,
            tool_result={"ok": True},
            attachments=[],
        )
    assert "完成" in result["message"]
