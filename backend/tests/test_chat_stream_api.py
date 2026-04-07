from fastapi.testclient import TestClient

import doc_process_studio.main as main_module
import doc_process_studio.services.chat.stream as chat_stream_module
from doc_process_studio.models.conversation.artifacts import GeneratedArtifact
from doc_process_studio.models.skill.runtime import SkillConversationState


def test_api_chat_stream_returns_artifact_and_text_events(monkeypatch) -> None:
    async def fake_build_uploaded_files_context(_files) -> str | None:
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

    async def fake_stream_chat_completion(*, model, messages, tools=None, tool_choice=None):
        assert model == "qwen3-coder-next:latest"
        assert tools
        assert tool_choice == "auto"
        call_counter["value"] += 1

        if call_counter["value"] == 1:
            yield {
                "choices": [
                    {
                        "delta": {
                            "tool_calls": [
                                {
                                    "index": 0,
                                    "id": "call-1",
                                    "type": "function",
                                    "function": {
                                        "name": "generate_architecture_doc",
                                        "arguments": (
                                            '{"system_name":"交通系统","document_title":"系统设计文档","doc_plan":{"chapters":[]}}'
                                        ),
                                    },
                                }
                            ]
                        },
                        "finish_reason": None,
                    }
                ]
            }
            yield {
                "choices": [
                    {
                        "delta": {},
                        "finish_reason": "tool_calls",
                    }
                ]
            }
            yield None
            return

        yield {
            "choices": [
                {
                    "delta": {
                        "content": "文件已生成，可直接下载。",
                    },
                    "finish_reason": None,
                }
            ]
        }
        yield {
            "choices": [
                {
                    "delta": {},
                    "finish_reason": "stop",
                }
            ]
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
                "artifact": {
                    "artifactId": "artifact-1",
                    "name": "系统架构与设计文档.docx",
                },
            },
            [
                GeneratedArtifact(
                    artifactId="artifact-1",
                    name="系统架构与设计文档.docx",
                    sizeLabel="24 KB",
                    sizeBytes=24 * 1024,
                    downloadUrl="/api/artifacts/artifact-1/download",
                    mimeType="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    expiresAt="2026-04-14T00:00:00Z",
                )
            ],
            "已生成 Word 文档。",
        )

    monkeypatch.setattr(
        chat_stream_module,
        "build_uploaded_files_context",
        fake_build_uploaded_files_context,
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
                '{"conversation_id":"conversation-1","model":"qwen3-coder-next:latest",'
                '"skill_id":"project-architecture-docx",'
                '"messages":[{"role":"user","content":"请生成架构设计文档"}]}'
            )
        },
    )

    assert response.status_code == 200
    response_text = response.text
    assert '"type": "tool-status"' in response_text
    assert '"type": "artifact"' in response_text
    assert '"downloadUrl": "/api/artifacts/artifact-1/download"' in response_text
    assert "文件已生成，可直接下载。" in response_text
    assert '"type": "done"' in response_text
