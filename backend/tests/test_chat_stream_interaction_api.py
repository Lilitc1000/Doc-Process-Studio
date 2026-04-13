import json
from datetime import datetime

from fastapi.testclient import TestClient

import doc_process_studio.main as main_module
import doc_process_studio.services.chat.stream as chat_stream_module
from doc_process_studio.models.conversation.attachments import ChatAttachment
from doc_process_studio.models.skill.interaction import SkillInteractionConfig
from doc_process_studio.models.skill.runtime import SkillPlanDecision


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


def _collect_assistant_contents(events: list[dict]) -> list[str]:
    contents: list[str] = []
    for event in events:
        message = event.get("message")
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if isinstance(content, str) and content:
            contents.append(content)
    return contents


def _collect_done_events(events: list[dict]) -> list[dict]:
    return [event for event in events if event.get("done") is True]


def _patch_common_chat_stream_dependencies(monkeypatch) -> None:
    async def fake_prepare_uploaded_files(**_kwargs):
        return [], None

    def fake_build_persisted_uploaded_files_context(_attachment_ids) -> str | None:
        return None

    async def fake_sync_skill_context_state(*, model: str, state) -> str | None:
        assert model == "qwen3-coder-next:latest"
        assert state.skill_id in {"incident-report", "document-assistant"}
        return None

    async def fake_load_interaction_state(
        _conversation_id: str,
        _skill_id: str,
        tenant_id: str = "default",
    ):
        assert tenant_id == "default"
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

    async def fake_plan_skill_activation(**_kwargs):
        return SkillPlanDecision(
            planner_model="qwen3-coder-next:latest",
            required_skill_ids=["incident-report"],
            optional_skill_ids=[],
            missing_explicit_skill_ids=[],
            active_skill_ids=["incident-report", "document-assistant"],
            primary_skill_id="incident-report",
            confidence=0.9,
            reasons={},
            candidates=[],
            created_at=datetime.now(),
        )

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
        "load_interaction_state",
        fake_load_interaction_state,
    )
    monkeypatch.setattr(
        chat_stream_module,
        "plan_skill_activation",
        fake_plan_skill_activation,
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
            "model": "qwen3-coder-next:latest",
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "start_skill_interaction",
                            "arguments": {},
                        }
                    }
                ],
            },
            "done": False,
        }
        yield {
            "model": "qwen3-coder-next:latest",
            "message": {"role": "assistant", "content": ""},
            "done": True,
            "done_reason": "tool_calls",
        }

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

    assert "进入交互向导。" in _collect_assistant_contents(events)

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

    done_events = _collect_done_events(events)
    assert len(done_events) == 1
    assert done_events[0].get("done_reason") == "interaction_required"


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

    interaction_completed_index = next(
        index
        for index, event in enumerate(events)
        if event.get("type") == "interaction" and event.get("status") == "completed"
    )
    tool_start_index = next(
        index
        for index, event in enumerate(events)
        if event.get("type") == "tool-status" and event.get("phase") == "start"
    )
    attachment_index = next(
        index for index, event in enumerate(events) if event.get("type") == "attachment"
    )
    tool_finish_index = next(
        index
        for index, event in enumerate(events)
        if event.get("type") == "tool-status" and event.get("phase") == "finish"
    )
    done_index = next(
        index for index, event in enumerate(events) if event.get("done") is True
    )
    assert (
        interaction_completed_index
        < tool_start_index
        < attachment_index
        < tool_finish_index
        < done_index
    )

    assert "交互完成，已生成附件。" in _collect_assistant_contents(events)

    done_events = _collect_done_events(events)
    assert len(done_events) == 1
    assert done_events[0].get("done_reason") == "stop"


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
            "model": "qwen3-coder-next:latest",
            "message": {"role": "assistant", "content": "已识别到完整信息，开始生成报告。"},
            "done": False,
        }
        yield {
            "model": "qwen3-coder-next:latest",
            "message": {"role": "assistant", "content": ""},
            "done": True,
            "done_reason": "stop",
        }

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

    assert "已识别到完整信息，开始生成报告。" in _collect_assistant_contents(events)

    done_events = _collect_done_events(events)
    assert len(done_events) == 1
    assert done_events[0].get("done_reason") == "stop"


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

    async def fake_load_interaction_state(
        _conversation_id: str,
        _skill_id: str,
        tenant_id: str = "default",
    ):
        assert tenant_id == "default"
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

    done_events = _collect_done_events(events)
    assert len(done_events) == 1
    assert done_events[0].get("done_reason") == "interaction_required"
