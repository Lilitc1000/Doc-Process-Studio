from fastapi.testclient import TestClient

import doc_process_studio.main as main_module
import doc_process_studio.services.chat.stream as chat_stream_module
from doc_process_studio.models.conversation.attachments import ChatAttachment
from doc_process_studio.models.skill.runtime import SkillConversationState


def test_api_chat_stream_returns_attachment_and_text_events(monkeypatch) -> None:
    async def fake_prepare_uploaded_files(**_kwargs):
        return [], None

    def fake_build_persisted_uploaded_files_context(_attachment_ids) -> str | None:
        return None

    async def fake_ensure_skill_context_for_request(request):
        assert request.skill_id == "project-architecture-docx"
        return (
            SkillConversationState(
                conversation_id=request.conversation_id,
                skill_id=request.skill_id,
                system_prompt="test",
                loaded_chunk_ids=[],
            ),
            None,
        )

    async def fake_sync_skill_context_state(*, model: str, state) -> str | None:
        assert model == "qwen3-coder-next:latest"
        assert state.skill_id == "project-architecture-docx"
        return None

    call_counter = {"value": 0}

    async def fake_stream_chat_completion(*, model, messages, tools=None):
        assert model == "qwen3-coder-next:latest"
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
                                "name": "generate_architecture_doc",
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
        return [{"type": "function", "function": {"name": "generate_architecture_doc"}}]

    def fake_execute_skill_tool_call(*, request, state, tool_call):
        assert request.skill_id == "project-architecture-docx"
        assert state.skill_id == "project-architecture-docx"
        assert tool_call["function"]["name"] == "generate_architecture_doc"
        return (
            {
                "ok": True,
                "attachment": {
                    "attachmentId": "attachment-1",
                    "name": "系统架构与设计文档.docx",
                },
            },
            [
                ChatAttachment(
                    attachmentId="attachment-1",
                    name="系统架构与设计文档.docx",
                    source="generated",
                    sizeLabel="24 KB",
                    sizeBytes=24 * 1024,
                    downloadUrl="/api/attachments/attachment-1/download",
                    mimeType="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    expiresAt="2026-04-14T00:00:00Z",
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
        "ensure_skill_context_for_request",
        fake_ensure_skill_context_for_request,
    )
    monkeypatch.setattr(
        chat_stream_module,
        "sync_skill_context_state",
        fake_sync_skill_context_state,
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
                '"skill_id":"project-architecture-docx",'
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
    assert '"downloadUrl": "/api/attachments/attachment-1/download"' in response_text
    assert "文件已生成，可直接下载。" in response_text
    assert '"done": true' in response_text
