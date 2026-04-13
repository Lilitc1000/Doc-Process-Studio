import json

import pytest

from doc_process_studio.models.conversation.stream import ChatMessageInput, ChatStreamRequest
from doc_process_studio.models.skill.catalog import SkillToolConfig
from doc_process_studio.models.skill.runtime import SkillConversationState
from doc_process_studio.services.skill import tool_loop as tool_loop_module
from doc_process_studio.services.skill.tool_loop import _coerce_json_file_argument


def test_coerce_json_file_argument_accepts_object_and_list() -> None:
    payload_object = {"chapters": [{"title": "章节一", "content": "正文"}]}
    assert _coerce_json_file_argument("outline_payload", payload_object) == payload_object

    payload_list = [{"title": "章节一", "content": "正文"}]
    assert _coerce_json_file_argument("outline_payload", payload_list) == payload_list


def test_coerce_json_file_argument_accepts_json_string() -> None:
    payload = '{"chapters":[{"title":"章节一","content":"正文"}]}'
    parsed = _coerce_json_file_argument("outline_payload", payload)
    assert isinstance(parsed, dict)
    assert parsed["chapters"][0]["title"] == "章节一"


def test_coerce_json_file_argument_accepts_double_encoded_json_string() -> None:
    payload = json.dumps('{"chapters":[{"title":"章节一"}]}')
    parsed = _coerce_json_file_argument("outline_payload", payload)
    assert isinstance(parsed, dict)
    assert parsed["chapters"][0]["title"] == "章节一"


def test_coerce_json_file_argument_accepts_yaml_string() -> None:
    payload = """
chapters:
  - title: 章节一
    content: 正文
"""
    parsed = _coerce_json_file_argument("outline_payload", payload)
    assert isinstance(parsed, dict)
    assert parsed["chapters"][0]["title"] == "章节一"


def test_coerce_json_file_argument_accepts_markdown_outline_with_text_normalizer() -> None:
    payload = """
# 第一章 项目概述
这里是概述正文。

## 1.1 建设目标
这里是目标正文。
"""
    parsed = _coerce_json_file_argument(
        "outline_payload",
        payload,
        text_normalizer="chaptered_document",
    )
    assert isinstance(parsed, dict)
    assert parsed["chapters"][0]["title"] == "第一章 项目概述"
    assert parsed["chapters"][0]["sections"][0]["title"] == "1.1 建设目标"


def test_coerce_json_file_argument_accepts_plain_text_with_text_normalizer() -> None:
    parsed = _coerce_json_file_argument(
        "outline_payload",
        "这是整理好的正文草稿。",
        text_normalizer="chaptered_document",
    )
    assert isinstance(parsed, dict)
    assert parsed["chapters"][0]["title"] == "文档内容"
    assert "正文草稿" in parsed["chapters"][0]["content"]


def test_coerce_json_file_argument_rejects_invalid_string() -> None:
    with pytest.raises(ValueError, match="JSON/YAML"):
        _coerce_json_file_argument("other_argument", "这不是 JSON")


def test_coerce_json_file_argument_rejects_plain_text_without_text_normalizer() -> None:
    with pytest.raises(ValueError, match="JSON/YAML"):
        _coerce_json_file_argument("outline_payload", "这是普通文本")


def test_builtin_tool_rejects_unknown_arguments() -> None:
    request = ChatStreamRequest(
        user_message_id="u1",
        conversation_id="c1",
        model="qwen3-coder-next:latest",
        messages=[ChatMessageInput(role="user", content="读取 skill 文件")],
        attachment_ids=[],
        skill_id="document-assistant",
    )
    state = SkillConversationState(
        conversation_id="c1",
        skill_id="document-assistant",
        system_prompt="test",
    )
    tool_call = {
        "function": {
            "name": "read_skill_file",
            "arguments": json.dumps(
                {"relative_path": "SKILL.md", "unexpected": "bad"},
                ensure_ascii=False,
            ),
        }
    }
    tool_result, _attachments = tool_loop_module.execute_skill_tool_call(
        request=request,
        state=state,
        tool_call=tool_call,
    )
    assert tool_result["ok"] is False
    assert "未声明字段" in str(tool_result.get("error"))


def test_declared_tool_honors_sensitive_confirmation_policy(monkeypatch) -> None:
    request = ChatStreamRequest(
        user_message_id="u1",
        conversation_id="c1",
        model="qwen3-coder-next:latest",
        messages=[ChatMessageInput(role="user", content="生成文档")],
        attachment_ids=[],
        skill_id="incident-report",
        confirm_sensitive_actions=False,
    )
    state = SkillConversationState(
        conversation_id="c1",
        skill_id="incident-report",
        system_prompt="test",
    )
    tool_call = {
        "function": {
            "name": "generate_incident_report",
            "arguments": json.dumps({"report_data": {"x": 1}}, ensure_ascii=False),
        }
    }

    sensitive_tool = SkillToolConfig.model_validate(
        {
            "name": "generate_incident_report",
            "description": "生成事故报告",
            "kind": "script",
            "path": "scripts/generate_incident_report.py",
            "parameters": {
                "type": "object",
                "properties": {"report_data": {"type": "object"}},
                "required": ["report_data"],
                "additionalProperties": False,
            },
            "execution": {
                "runtime": "python",
                "arg_bindings": {
                    "report_data": {"flag": "--json", "serializer": "json_file"},
                },
            },
            "security": {
                "risk_level": "high",
                "requires_confirmation": True,
            },
        }
    )

    monkeypatch.setattr(
        tool_loop_module,
        "get_skill_tool_config",
        lambda _skill_id, _tool_name: sensitive_tool,
    )
    monkeypatch.setattr(
        tool_loop_module.settings,
        "skill_sensitive_operation_policy",
        "confirm",
    )

    tool_result, _attachments = tool_loop_module.execute_skill_tool_call(
        request=request,
        state=state,
        tool_call=tool_call,
    )
    assert tool_result["ok"] is False
    assert "需要确认" in str(tool_result.get("error"))


def test_builtin_tool_without_required_field_does_not_raise() -> None:
    request = ChatStreamRequest(
        user_message_id="u1",
        conversation_id="c1",
        model="qwen3-coder-next:latest",
        messages=[ChatMessageInput(role="user", content="列目录")],
        attachment_ids=[],
        skill_id="document-assistant",
    )
    state = SkillConversationState(
        conversation_id="c1",
        skill_id="document-assistant",
        system_prompt="test",
    )
    tool_call = {
        "function": {
            "name": "list_skill_directory",
            "arguments": json.dumps({}, ensure_ascii=False),
        }
    }
    tool_result, _attachments = tool_loop_module.execute_skill_tool_call(
        request=request,
        state=state,
        tool_call=tool_call,
    )
    assert tool_result["ok"] is True
    assert isinstance(tool_result.get("entries"), list)
