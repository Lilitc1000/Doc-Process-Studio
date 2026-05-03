import json
import asyncio

import pytest

from doc_process_studio.chat.schemas.request import ChatMessageInput, ChatStreamRequest
from doc_process_studio.skill.schemas.catalog import SkillToolConfig
from doc_process_studio.skill.schemas.runtime import SkillConversationState
from doc_process_studio.skill.service import tool_loop as tool_loop_module
from doc_process_studio.skill.service.tool_loop import _coerce_json_file_argument, _restructure_doc_plan, _try_repair_truncated_json
from doc_process_studio.skill.service.tool_loop import tool_exec as _tool_exec_module


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


def test_coerce_json_file_argument_accepts_json_string_with_chinese_punctuation() -> None:
    payload = (
        '[{"title":"1. 概述","content":"正文一"}，'
        '{"title":"2. 架构","content":"正文二"}]'
    )
    parsed = _coerce_json_file_argument("doc_plan", payload)
    assert isinstance(parsed, list)
    assert len(parsed) == 2
    assert parsed[0]["title"] == "1. 概述"
    assert parsed[1]["title"] == "2. 架构"


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


def test_coerce_json_file_argument_rejects_invalid_json_like_even_with_text_normalizer() -> None:
    payload = (
        '{"chapters":[{"title":"1. 概述","content":"正文"}]，'
        '{"title":"2. 架构","content":"正文二"}}'
    )
    with pytest.raises(ValueError, match="看起来是 JSON"):
        _coerce_json_file_argument(
            "doc_plan",
            payload,
            text_normalizer="chaptered_document",
        )


def test_builtin_tool_rejects_unknown_arguments() -> None:
    request = ChatStreamRequest(
        user_message_id="u1",
        conversation_id="c1",
        model="qwen3-coder-next:latest",
        messages=[ChatMessageInput(role="user", content="读取 skill 文件")],
        attachment_ids=[],
        selected_skill_ids=["document-assistant"],
    )
    state = SkillConversationState(
        skill_id="document-assistant",
        conversation_id="c1",
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
    tool_result, _attachments = asyncio.run(tool_loop_module.execute_skill_tool_call(
        request=request,
        state=state,
        tool_call=tool_call,
    ))
    assert tool_result["ok"] is False
    assert "未声明字段" in str(tool_result.get("error"))


def test_declared_tool_honors_sensitive_confirmation_policy(monkeypatch) -> None:
    request = ChatStreamRequest(
        user_message_id="u1",
        conversation_id="c1",
        model="qwen3-coder-next:latest",
        messages=[ChatMessageInput(role="user", content="生成文档")],
        attachment_ids=[],
        selected_skill_ids=["incident-report"],
        confirm_sensitive_actions=False,
    )
    state = SkillConversationState(
        skill_id="document-assistant",
        conversation_id="c1",
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
        _tool_exec_module,
        "get_skill_tool_config",
        lambda _skill_id, _tool_name: sensitive_tool,
    )
    monkeypatch.setattr(
        _tool_exec_module.settings,
        "skill_sensitive_operation_policy",
        "confirm",
    )

    tool_result, _attachments = asyncio.run(tool_loop_module.execute_skill_tool_call(
        request=request,
        state=state,
        tool_call=tool_call,
    ))
    assert tool_result["ok"] is False
    assert "需要确认" in str(tool_result.get("error"))


def test_builtin_tool_without_required_field_does_not_raise() -> None:
    request = ChatStreamRequest(
        user_message_id="u1",
        conversation_id="c1",
        model="qwen3-coder-next:latest",
        messages=[ChatMessageInput(role="user", content="列目录")],
        attachment_ids=[],
        selected_skill_ids=["document-assistant"],
    )
    state = SkillConversationState(
        skill_id="document-assistant",
        conversation_id="c1",
        system_prompt="test",
    )
    tool_call = {
        "function": {
            "name": "list_skill_directory",
            "arguments": json.dumps({}, ensure_ascii=False),
        }
    }
    tool_result, _attachments = asyncio.run(tool_loop_module.execute_skill_tool_call(
        request=request,
        state=state,
        tool_call=tool_call,
    ))
    assert tool_result["ok"] is True
    assert isinstance(tool_result.get("entries"), list)


def test_search_skill_context_limit_overflow_is_clamped(monkeypatch) -> None:
    request = ChatStreamRequest(
        user_message_id="u1",
        conversation_id="c1",
        model="qwen3-coder-next:latest",
        messages=[ChatMessageInput(role="user", content="检索技能上下文")],
        attachment_ids=[],
        selected_skill_ids=["document-assistant"],
    )
    state = SkillConversationState(
        skill_id="document-assistant",
        conversation_id="c1",
        system_prompt="test",
    )

    captured: dict[str, object] = {}

    async def fake_search_skill_context_chunks(
        skill_id: str,
        query: str,
        *,
        exclude_chunk_ids: set[str],
        limit: int | None = None,
        source_path_contains: str | None = None,
        reranker_model: str | None = None,
    ) -> list[object]:
        captured["skill_id"] = skill_id
        captured["query"] = query
        captured["limit"] = limit
        captured["source_path_contains"] = source_path_contains
        captured["reranker_model"] = reranker_model
        return []

    monkeypatch.setattr(
        _tool_exec_module,
        "search_skill_context_chunks",
        fake_search_skill_context_chunks,
    )
    monkeypatch.setattr(
        _tool_exec_module.settings,
        "skill_context_search_limit_max",
        16,
    )

    tool_call = {
        "function": {
            "name": "search_skill_context",
            "arguments": json.dumps(
                {"query": "交通行业经验", "limit": 20},
                ensure_ascii=False,
            ),
        }
    }
    tool_result, _attachments = asyncio.run(tool_loop_module.execute_skill_tool_call(
        request=request,
        state=state,
        tool_call=tool_call,
    ))

    assert tool_result["ok"] is True
    assert tool_result["limit"] == 16
    assert captured["limit"] == 16


def test_restructure_doc_plan_splits_flat_heading_outlines() -> None:
    flat = {
        "chapters": [
            {
                "title": "1. 文档概述",
                "content": "1.1 文档目的\n1.2 文档范围\n1.3 术语定义",
            },
            {
                "title": "2. 需求分析",
                "content": "2.1 业务需求\n2.2 功能需求",
            },
        ]
    }
    result = _restructure_doc_plan(flat)
    ch1 = result["chapters"][0]
    assert ch1["content"] == ""
    assert len(ch1["sections"]) == 3
    assert ch1["sections"][0]["title"] == "1.1 文档目的"
    assert ch1["sections"][1]["title"] == "1.2 文档范围"
    assert ch1["sections"][2]["title"] == "1.3 术语定义"

    ch2 = result["chapters"][1]
    assert len(ch2["sections"]) == 2


def test_restructure_doc_plan_preserves_real_content() -> None:
    good = {
        "chapters": [
            {
                "title": "1. 概述",
                "content": "本文档描述系统架构设计方案，覆盖核心模块与部署策略。",
                "sections": [
                    {"title": "1.1 背景", "content": "系统用于支撑业务场景。"},
                ],
            }
        ]
    }
    result = _restructure_doc_plan(good)
    ch = result["chapters"][0]
    assert ch["content"] == "本文档描述系统架构设计方案，覆盖核心模块与部署策略。"
    assert len(ch["sections"]) == 1
    assert ch["sections"][0]["title"] == "1.1 背景"


def test_restructure_doc_plan_content_list_not_restructured() -> None:
    data = {
        "chapters": [
            {
                "title": "1. 概述",
                "content": ["段落一", "段落二"],
            }
        ]
    }
    result = _restructure_doc_plan(data)
    ch = result["chapters"][0]
    assert ch["content"] == ["段落一", "段落二"]


def test_restructure_doc_plan_content_headings_with_existing_sections() -> None:
    data = {
        "chapters": [
            {
                "title": "1. 设计",
                "content": "1.1 原则\n1.2 方案",
                "sections": [
                    {"title": "1.0 总则", "content": "遵循标准。"},
                ],
            }
        ]
    }
    result = _restructure_doc_plan(data)
    ch = result["chapters"][0]
    assert ch["content"] == ""
    assert len(ch["sections"]) == 3
    assert ch["sections"][0]["title"] == "1.0 总则"
    assert ch["sections"][1]["title"] == "1.1 原则"
    assert ch["sections"][2]["title"] == "1.2 方案"


def test_restructure_doc_plan_recursive_sections() -> None:
    data = {
        "chapters": [
            {
                "title": "1. 概述",
                "content": "正文",
                "sections": [
                    {
                        "title": "1.1 背景",
                        "content": "1.1.1 历史\n1.1.2 现状",
                    },
                ],
            }
        ]
    }
    result = _restructure_doc_plan(data)
    sub = result["chapters"][0]["sections"][0]
    assert sub["content"] == ""
    assert len(sub["sections"]) == 2
    assert sub["sections"][0]["title"] == "1.1.1 历史"


def test_restructure_doc_plan_mixed_content_and_headings() -> None:
    mixed = {
        "chapters": [
            {
                "title": "1. 总体设计",
                "content": "系统采用微服务架构。\n1.1 架构原则\n1.2 技术选型",
            }
        ]
    }
    result = _restructure_doc_plan(mixed)
    ch = result["chapters"][0]
    assert ch["content"] == "系统采用微服务架构。"
    assert len(ch["sections"]) == 2
    assert ch["sections"][0]["title"] == "1.1 架构原则"


def test_restructure_doc_plan_single_heading_not_restructured() -> None:
    single = {
        "chapters": [
            {
                "title": "1. 概述",
                "content": "1.1 背景",
            }
        ]
    }
    result = _restructure_doc_plan(single)
    ch = result["chapters"][0]
    assert ch["content"] == "1.1 背景"
    assert "sections" not in ch or not ch.get("sections")


def test_restructure_doc_plan_array_form() -> None:
    flat_array = [
        {
            "title": "1. 概述",
            "content": "1.1 目的\n1.2 范围",
        }
    ]
    result = _restructure_doc_plan(flat_array)
    assert isinstance(result, list)
    assert len(result[0]["sections"]) == 2


def test_restructure_doc_plan_merges_titleless_chapters() -> None:
    split = {
        "chapters": [
            {"title": "1. 概述", "content": "本文档定义系统架构。"},
            {"title": "2. 整体架构", "content": "平台基于三级协同架构。"},
            {
                "content": "平台采用五层分层架构设计。",
                "sections": [
                    {"title": "2.1 设备接入层", "content": "支持多协议统一接入。"},
                    {"title": "2.2 通信传输层", "content": "保障双向稳定通信。"},
                ],
            },
            {"title": "3. 核心模块", "content": "平台核心模块包括设备管理。"},
            {
                "content": "详细模块描述。",
                "sections": [
                    {"title": "3.1 设备管理", "content": "全生命周期管理。"},
                ],
            },
        ]
    }
    result = _restructure_doc_plan(split)
    chapters = result["chapters"]
    assert len(chapters) == 3

    assert chapters[0]["title"] == "1. 概述"
    assert "sections" not in chapters[0] or not chapters[0].get("sections")

    assert chapters[1]["title"] == "2. 整体架构"
    assert len(chapters[1]["sections"]) == 2
    assert chapters[1]["sections"][0]["title"] == "2.1 设备接入层"

    assert chapters[2]["title"] == "3. 核心模块"
    assert len(chapters[2]["sections"]) == 1
    assert chapters[2]["sections"][0]["title"] == "3.1 设备管理"


def test_restructure_doc_plan_merges_titleless_chapter_content_only() -> None:
    data = {
        "chapters": [
            {"title": "1. 概述", "content": "简短摘要。"},
            {"content": "这是概述的详细正文内容，应该被合并到前一个章节。"},
        ]
    }
    result = _restructure_doc_plan(data)
    chapters = result["chapters"]
    assert len(chapters) == 1
    assert chapters[0]["title"] == "1. 概述"
    assert "简短摘要" in chapters[0]["content"]
    assert "详细正文内容" in chapters[0]["content"]


def test_restructure_doc_plan_titleless_first_chapter_kept() -> None:
    data = {
        "chapters": [
            {"content": "无标题的首章内容。", "sections": [{"title": "1.1 子节", "content": "子节内容。"}]},
            {"title": "2. 架构", "content": "架构内容。"},
        ]
    }
    result = _restructure_doc_plan(data)
    chapters = result["chapters"]
    assert len(chapters) == 2
    assert chapters[0].get("title", "") == ""
    assert len(chapters[0]["sections"]) == 1


def test_try_repair_truncated_json_array() -> None:
    truncated = '[{"title": "1. 概述", "content": "正文一"}, {"title": "2. 架构", "content": "正文二'
    result = _try_repair_truncated_json(truncated)
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["title"] == "1. 概述"
    assert result[1]["title"] == "2. 架构"


def test_try_repair_truncated_json_object() -> None:
    truncated = '{"chapters": [{"title": "1. 概述", "content": "正文"}, {"title": "2. 架构", "content": "架构内容'
    result = _try_repair_truncated_json(truncated)
    assert isinstance(result, dict)
    assert len(result["chapters"]) == 2


def test_try_repair_truncated_json_returns_none_for_valid_json() -> None:
    valid = '[{"title": "1. 概述", "content": "正文"}]'
    result = _try_repair_truncated_json(valid)
    assert result is None


def test_try_repair_truncated_json_returns_none_for_non_json() -> None:
    result = _try_repair_truncated_json("这是普通文本，不是JSON")
    assert result is None


def test_coerce_json_file_argument_repairs_truncated_json_string() -> None:
    truncated = '[{"title": "1. 概述", "content": "正文一"}, {"title": "2. 架构", "content": "正文二'
    result = _coerce_json_file_argument("doc_plan", truncated)
    assert isinstance(result, list)
    assert len(result) == 2
