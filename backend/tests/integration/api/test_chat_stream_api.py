from datetime import UTC, datetime

from fastapi.testclient import TestClient

import doc_process_studio.main as main_module
import doc_process_studio.chat.service.stream as chat_stream_module
from doc_process_studio.chat.models.attachment import ChatAttachment
from doc_process_studio.skill.models.runtime import SkillPlanDecision


def test_api_chat_stream_returns_attachment_and_text_events(monkeypatch) -> None:
    async def fake_prepare_uploaded_files(**_kwargs):
        return [], None

    def fake_build_persisted_uploaded_files_context(_attachment_ids) -> str | None:
        return None

    async def fake_sync_skill_context_state(*, model: str, state) -> str | None:
        assert model == "qwen3-coder-next:latest"
        assert state.skill_id in {"project-architecture-docx", "document-assistant"}
        return None

    async def fake_load_conversation_state(
        _conversation_id: str,
        tenant_id: str = "default",
    ):
        assert tenant_id == "default"
        return None

    async def fake_save_conversation_state(_state, tenant_id: str = "default"):
        assert tenant_id == "default"
        return None

    call_counter = {"value": 0}
    observed_tools: list[object] = []

    async def fake_stream_chat_completion(*, model, messages, tools=None):
        assert model == "qwen3-coder-next:latest"
        observed_tools.append(tools)
        if call_counter["value"] == 0:
            assert tools
        call_counter["value"] += 1

        if call_counter["value"] == 1:
            yield {
                "model": model,
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "function": {
                                "name": "generate_document",
                                "arguments": {
                                    "system_name": "交通系统",
                                    "document_title": "系统设计文档",
                                    "doc_plan": {"chapters": []},
                                },
                            }
                        }
                    ],
                },
                "done": False,
            }
            yield {
                "model": model,
                "message": {"role": "assistant", "content": ""},
                "done": True,
                "done_reason": "tool_calls",
            }
            yield None
            return

        yield {
            "model": model,
            "message": {
                "role": "assistant",
                "content": "文件已生成，可直接下载。",
            },
            "done": False,
        }
        yield {
            "model": model,
            "message": {"role": "assistant", "content": ""},
            "done": True,
            "done_reason": "stop",
        }
        yield None

    def fake_build_skill_tools(skill_id: str):
        assert skill_id == "project-architecture-docx"
        return [{"type": "function", "function": {"name": "generate_document"}}]

    def fake_execute_skill_tool_call(*, request, state, tool_call):
        assert request.selected_skill_ids == ["project-architecture-docx"]
        assert state.skill_id == "project-architecture-docx"
        assert tool_call["function"]["name"] == "generate_document"
        return (
            {
                "ok": True,
                "attachment": {
                    "attachment_id": "attachment-1",
                    "name": "系统架构与设计文档.docx",
                },
            },
            [
                ChatAttachment(
                    attachment_id="attachment-1",
                    name="系统架构与设计文档.docx",
                    source="generated",
                    size_label="24 KB",
                    size_bytes=24 * 1024,
                    download_url="/api/attachments/attachment-1/download",
                    mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    expires_at="2026-04-14T00:00:00Z",
                )
            ],
        )

    monkeypatch.setattr(
        chat_stream_module,
        "prepare_uploaded_files",
        fake_prepare_uploaded_files,
    )
    monkeypatch.setattr(
        chat_stream_module,
        "build_persisted_uploaded_files_context",
        fake_build_persisted_uploaded_files_context,
    )
    monkeypatch.setattr(
        chat_stream_module,
        "sync_skill_context_state",
        fake_sync_skill_context_state,
    )
    monkeypatch.setattr(
        chat_stream_module,
        "load_conversation_state",
        fake_load_conversation_state,
    )
    monkeypatch.setattr(
        chat_stream_module,
        "save_conversation_state",
        fake_save_conversation_state,
    )
    monkeypatch.setattr(
        chat_stream_module,
        "stream_chat_completion",
        fake_stream_chat_completion,
    )
    monkeypatch.setattr(
        chat_stream_module,
        "build_skill_tools",
        fake_build_skill_tools,
    )
    async def fake_select_for_chat_skills(**_kwargs):
        return SkillPlanDecision(
            planner_model="qwen3-coder-next:latest",
            required_skill_ids=["project-architecture-docx"],
            optional_skill_ids=[],
            missing_explicit_skill_ids=[],
            active_skill_ids=["project-architecture-docx", "document-assistant"],
            primary_skill_id="project-architecture-docx",
            confidence=0.9,
            reasons={},
            candidates=[],
            created_at=datetime.now(UTC),
        )

    monkeypatch.setattr(
        chat_stream_module,
        "select_for_chat_skills",
        fake_select_for_chat_skills,
    )
    monkeypatch.setattr(
        chat_stream_module,
        "execute_skill_tool_call",
        fake_execute_skill_tool_call,
    )

    client = TestClient(main_module.app)
    response = client.post(
        "/api/chat/stream",
        data={
            "payload": (
                '{"user_message_id":"user-1","conversation_id":"conversation-1",'
                '"model":"qwen3-coder-next:latest",'
                '"selected_skill_ids":["project-architecture-docx"],'
                '"messages":[{"role":"user","content":"请生成架构设计文档"}],'
                '"attachment_ids":[]}'
            )
        },
    )

    assert response.status_code == 200
    response_text = response.text
    assert '"type": "tool-status"' in response_text
    assert '"type": "attachment"' in response_text
    assert '"download_url": "/api/attachments/attachment-1/download"' in response_text
    assert "文件已生成，可直接下载。" in response_text
    assert '"done": true' in response_text
    assert observed_tools
    assert observed_tools[0]
