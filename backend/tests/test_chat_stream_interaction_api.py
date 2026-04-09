import json
from datetime import datetime

from fastapi.testclient import TestClient

import doc_process_studio.main as main_module
import doc_process_studio.services.chat.stream as chat_stream_module
from doc_process_studio.models.conversation.attachments import ChatAttachment
from doc_process_studio.models.skill.interaction import SkillInteractionConfig
from doc_process_studio.models.skill.runtime import SkillConversationState


def _parse_sse_events(response_text: str) -> list[dict]:
    events: list[dict] = []
    for chunk in response_text.split("\n\n"):
        chunk = chunk.strip()
        if not chunk.startswith("data:"):
            continue
        payload_text = chunk[len("data:") :].strip()
        if not payload_text:
            continue
        events.append(json.loads(payload_text))
    return events


def _patch_common_chat_stream_dependencies(monkeypatch) -> None:
    async def fake_prepare_uploaded_files(**_kwargs):
        return [], None

    def fake_build_persisted_uploaded_files_context(_attachment_ids) -> str | None:
        return None

    async def fake_ensure_skill_context_for_request(request):
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
        assert state.skill_id == "incident-report"
        return None

    async def fake_load_interaction_state(_conversation_id: str, _skill_id: str):
        return None

    monkeypatch.setattr(
        chat_stream_module.settings,
        "ollama_base_url",
        "http://ollama.test",
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
        "load_interaction_state",
        fake_load_interaction_state,
    )


def test_api_chat_stream_returns_interaction_required_when_model_calls_wizard_tool(
    monkeypatch,
) -> None:
    _patch_common_chat_stream_dependencies(monkeypatch)

    interaction_config = SkillInteractionConfig.model_validate(
        {
            "enabled": True,
            "intro_message": "进入交互向导。",
            "steps": [
                {
                    "id": "step-1",
                    "title": "步骤 1",
                    "prompt": "请选择事故类型",
                    "field_path": "incident.type",
                    "kind": "single_select",
                    "options": [
                        {"value": "system_outage", "label": "系统中断"},
                    ],
                }
            ],
        }
    )

    monkeypatch.setattr(
        chat_stream_module,
        "get_skill_interaction_config",
        lambda _skill_id: interaction_config,
    )

    async def fake_start_or_resume_interaction(*, request, config):
        assert request.skill_id == "incident-report"
        assert config.enabled is True
        return object(), {
            "sessionId": "sess-1",
            "stepId": "step-1",
            "title": "步骤 1",
            "prompt": "请选择事故类型",
            "kind": "single_select",
            "allowCustom": False,
            "required": True,
            "placeholder": None,
            "currentStep": 1,
            "totalSteps": 1,
            "options": [
                {"value": "system_outage", "label": "系统中断", "description": None}
            ],
        }

    async def fake_submit_interaction_answer(*_args, **_kwargs):
        raise AssertionError("无 interaction_answer 时不应提交步骤答案。")

    async def fake_stream_chat_completion(**_kwargs):
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
                                    "name": "start_skill_interaction",
                                    "arguments": "{}",
                                },
                            }
                        ]
                    },
                    "finish_reason": None,
                }
            ]
        }
        yield {"choices": [{"delta": {}, "finish_reason": "tool_calls"}]}

    monkeypatch.setattr(
        chat_stream_module,
        "start_or_resume_interaction",
        fake_start_or_resume_interaction,
    )
    monkeypatch.setattr(
        chat_stream_module,
        "submit_interaction_answer",
        fake_submit_interaction_answer,
    )
    monkeypatch.setattr(
        chat_stream_module,
        "stream_chat_completion",
        fake_stream_chat_completion,
    )

    client = TestClient(main_module.app)
    response = client.post(
        "/api/chat/stream",
        data={
            "payload": json.dumps(
                {
                    "user_message_id": "user-1",
                    "conversation_id": "conv-1",
                    "model": "qwen3-coder-next:latest",
                    "skill_id": "incident-report",
                    "selected_skill_ids": ["incident-report"],
                    "messages": [{"role": "user", "content": "请生成事故报告"}],
                    "attachment_ids": [],
                },
                ensure_ascii=False,
            )
        },
    )

    assert response.status_code == 200
    events = _parse_sse_events(response.text)
    assert all(event.get("type") != "error" for event in events)

    assert {
        "type": "delta",
        "content": "进入交互向导。",
    } in events

    interaction_events = [
        event
        for event in events
        if event.get("type") == "interaction" and event.get("status") == "required"
    ]
    assert len(interaction_events) == 1
    assert interaction_events[0]["interaction"]["sessionId"] == "sess-1"
    assert interaction_events[0]["interaction"]["stepId"] == "step-1"

    tool_status_events = [event for event in events if event.get("type") == "tool-status"]
    assert len(tool_status_events) == 2
    assert tool_status_events[0].get("tool_name") == "start_skill_interaction"
    assert tool_status_events[0].get("phase") == "start"
    assert tool_status_events[1].get("phase") == "finish"

    done_events = [event for event in events if event.get("type") == "done"]
    assert len(done_events) == 1
    assert done_events[0].get("finish_reason") == "interaction_required"


def test_api_chat_stream_interaction_completion_runs_final_tool(monkeypatch) -> None:
    _patch_common_chat_stream_dependencies(monkeypatch)

    interaction_config = SkillInteractionConfig.model_validate(
        {
            "enabled": True,
            "completion_message": "交互完成，已生成附件。",
            "steps": [
                {
                    "id": "step-1",
                    "title": "步骤 1",
                    "prompt": "请选择事故类型",
                    "field_path": "incident.type",
                    "kind": "single_select",
                    "options": [{"value": "system_outage", "label": "系统中断"}],
                }
            ],
            "final_tool": {
                "name": "generate_incident_report",
                "argument_name": "report_data",
                "output_name_template": "incident-{doc_id}.docx",
                "static_arguments": {},
            },
        }
    )

    monkeypatch.setattr(
        chat_stream_module,
        "get_skill_interaction_config",
        lambda _skill_id: interaction_config,
    )

    async def fake_start_or_resume_interaction(*_args, **_kwargs):
        raise AssertionError("已提交 interaction_answer 时不应走 start_or_resume。")

    async def fake_submit_interaction_answer(*, request, config, answer):
        assert request.skill_id == "incident-report"
        assert config.final_tool is not None
        assert answer.step_id == "step-1"
        return None, {"doc_id": "001", "incident_type": "system_outage"}

    def fake_execute_skill_tool_call(*, request, state, tool_call):
        assert request.skill_id == "incident-report"
        assert state.skill_id == "incident-report"
        assert tool_call["function"]["name"] == "generate_incident_report"
        tool_arguments = json.loads(tool_call["function"]["arguments"])
        assert tool_arguments["report_data"]["doc_id"] == "001"
        assert tool_arguments["output_name"] == "incident-001.docx"
        return (
            {"ok": True, "message": "ok"},
            [
                ChatAttachment(
                    attachmentId="attachment-interaction-1",
                    name="incident-001.docx",
                    source="generated",
                    mimeType="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    sizeBytes=1024,
                    sizeLabel="1 KB",
                    downloadUrl="/api/attachments/attachment-interaction-1/download",
                    expiresAt=datetime.fromisoformat("2026-04-20T00:00:00+00:00"),
                )
            ],
        )

    async def fake_stream_chat_completion(**_kwargs):
        raise AssertionError("final_tool 完成分支不应继续调用模型流。")
        yield None

    monkeypatch.setattr(
        chat_stream_module,
        "start_or_resume_interaction",
        fake_start_or_resume_interaction,
    )
    monkeypatch.setattr(
        chat_stream_module,
        "submit_interaction_answer",
        fake_submit_interaction_answer,
    )
    monkeypatch.setattr(
        chat_stream_module,
        "execute_skill_tool_call",
        fake_execute_skill_tool_call,
    )
    monkeypatch.setattr(
        chat_stream_module,
        "stream_chat_completion",
        fake_stream_chat_completion,
    )

    client = TestClient(main_module.app)
    response = client.post(
        "/api/chat/stream",
        data={
            "payload": json.dumps(
                {
                    "user_message_id": "user-1",
                    "conversation_id": "conv-1",
                    "model": "qwen3-coder-next:latest",
                    "skill_id": "incident-report",
                    "selected_skill_ids": ["incident-report"],
                    "messages": [{"role": "user", "content": "请生成事故报告"}],
                    "attachment_ids": [],
                    "interaction_answer": {
                        "session_id": "sess-1",
                        "step_id": "step-1",
                        "value": "system_outage",
                    },
                },
                ensure_ascii=False,
            )
        },
    )

    assert response.status_code == 200
    events = _parse_sse_events(response.text)
    assert all(event.get("type") != "error" for event in events)

    assert {"type": "interaction", "status": "completed"} in events

    tool_status_events = [
        event for event in events if event.get("type") == "tool-status"
    ]
    assert len(tool_status_events) == 2
    assert tool_status_events[0].get("phase") == "start"
    assert tool_status_events[1].get("phase") == "finish"

    attachment_events = [event for event in events if event.get("type") == "attachment"]
    assert len(attachment_events) == 1
    assert (
        attachment_events[0]["attachment"]["downloadUrl"]
        == "/api/attachments/attachment-interaction-1/download"
    )

    assert {"type": "delta", "content": "交互完成，已生成附件。"} in events

    done_events = [event for event in events if event.get("type") == "done"]
    assert len(done_events) == 1
    assert done_events[0].get("finish_reason") == "stop"


def test_api_chat_stream_no_forced_interaction_when_model_not_call_wizard_tool(
    monkeypatch,
) -> None:
    _patch_common_chat_stream_dependencies(monkeypatch)

    interaction_config = SkillInteractionConfig.model_validate(
        {
            "enabled": True,
            "steps": [
                {
                    "id": "step-1",
                    "title": "步骤 1",
                    "prompt": "请选择事故类型",
                    "field_path": "incident.type",
                    "kind": "single_select",
                    "options": [{"value": "system_outage", "label": "系统中断"}],
                }
            ],
        }
    )

    monkeypatch.setattr(
        chat_stream_module,
        "get_skill_interaction_config",
        lambda _skill_id: interaction_config,
    )

    async def fake_start_or_resume_interaction(*_args, **_kwargs):
        raise AssertionError("信息已充足时不应进入交互向导。")

    async def fake_submit_interaction_answer(*_args, **_kwargs):
        raise AssertionError("未提交 interaction_answer 时不应调用提交接口。")

    async def fake_stream_chat_completion(**_kwargs):
        yield {
            "choices": [
                {
                    "delta": {"content": "已识别到完整信息，开始生成报告。"},
                    "finish_reason": None,
                }
            ]
        }
        yield {"choices": [{"delta": {}, "finish_reason": "stop"}]}

    monkeypatch.setattr(
        chat_stream_module,
        "start_or_resume_interaction",
        fake_start_or_resume_interaction,
    )
    monkeypatch.setattr(
        chat_stream_module,
        "submit_interaction_answer",
        fake_submit_interaction_answer,
    )
    monkeypatch.setattr(
        chat_stream_module,
        "stream_chat_completion",
        fake_stream_chat_completion,
    )

    client = TestClient(main_module.app)
    response = client.post(
        "/api/chat/stream",
        data={
            "payload": json.dumps(
                {
                    "user_message_id": "user-1",
                    "conversation_id": "conv-1",
                    "model": "qwen3-coder-next:latest",
                    "skill_id": "incident-report",
                    "selected_skill_ids": ["incident-report"],
                    "messages": [
                        {
                            "role": "user",
                            "content": (
                                "Description of the Incident: payment service timeout\n"
                                "Affected Date: 08/04/2026 09:10\n"
                                "Event Sequence: monitor alert -> restart -> recovered\n"
                                "Impact: transaction failure in gateway\n"
                                "Root Cause: unhandled exception in worker\n"
                                "Follow-up Actions: add retry and alert tuning"
                            ),
                        }
                    ],
                    "attachment_ids": [],
                },
                ensure_ascii=False,
            )
        },
    )

    assert response.status_code == 200
    events = _parse_sse_events(response.text)
    assert all(event.get("type") != "error" for event in events)
    assert all(event.get("type") != "interaction" for event in events)

    assert {"type": "delta", "content": "已识别到完整信息，开始生成报告。"} in events

    done_events = [event for event in events if event.get("type") == "done"]
    assert len(done_events) == 1
    assert done_events[0].get("finish_reason") == "stop"


def test_api_chat_stream_resumes_existing_interaction_state(monkeypatch) -> None:
    _patch_common_chat_stream_dependencies(monkeypatch)

    interaction_config = SkillInteractionConfig.model_validate(
        {
            "enabled": True,
            "steps": [
                {
                    "id": "step-1",
                    "title": "步骤 1",
                    "prompt": "请选择事故类型",
                    "field_path": "incident.type",
                    "kind": "single_select",
                    "options": [{"value": "system_outage", "label": "系统中断"}],
                }
            ],
        }
    )

    monkeypatch.setattr(
        chat_stream_module,
        "get_skill_interaction_config",
        lambda _skill_id: interaction_config,
    )

    async def fake_load_interaction_state(_conversation_id: str, _skill_id: str):
        return object()

    async def fake_start_or_resume_interaction(*, request, config):
        assert request.skill_id == "incident-report"
        assert config.enabled is True
        return object(), {
            "sessionId": "sess-resume-1",
            "stepId": "step-1",
            "title": "步骤 1",
            "prompt": "请选择事故类型",
            "kind": "single_select",
            "allowCustom": False,
            "required": True,
            "placeholder": None,
            "currentStep": 1,
            "totalSteps": 1,
            "options": [
                {"value": "system_outage", "label": "系统中断", "description": None}
            ],
        }

    async def fake_stream_chat_completion(**_kwargs):
        raise AssertionError("恢复既有向导状态时不应调用模型流。")
        yield None

    monkeypatch.setattr(
        chat_stream_module,
        "load_interaction_state",
        fake_load_interaction_state,
    )
    monkeypatch.setattr(
        chat_stream_module,
        "start_or_resume_interaction",
        fake_start_or_resume_interaction,
    )
    monkeypatch.setattr(
        chat_stream_module,
        "stream_chat_completion",
        fake_stream_chat_completion,
    )

    client = TestClient(main_module.app)
    response = client.post(
        "/api/chat/stream",
        data={
            "payload": json.dumps(
                {
                    "user_message_id": "user-1",
                    "conversation_id": "conv-1",
                    "model": "qwen3-coder-next:latest",
                    "skill_id": "incident-report",
                    "selected_skill_ids": ["incident-report"],
                    "messages": [{"role": "user", "content": "继续"}],
                    "attachment_ids": [],
                },
                ensure_ascii=False,
            )
        },
    )

    assert response.status_code == 200
    events = _parse_sse_events(response.text)
    assert all(event.get("type") != "error" for event in events)

    interaction_events = [
        event
        for event in events
        if event.get("type") == "interaction" and event.get("status") == "required"
    ]
    assert len(interaction_events) == 1
    assert interaction_events[0]["interaction"]["sessionId"] == "sess-resume-1"

    done_events = [event for event in events if event.get("type") == "done"]
    assert len(done_events) == 1
    assert done_events[0].get("finish_reason") == "interaction_required"
