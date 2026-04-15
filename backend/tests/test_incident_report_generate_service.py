import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

import doc_process_studio.services.chat.incident_reports as incident_reports_module
from doc_process_studio.models.conversation.attachments import ChatAttachment
from doc_process_studio.models.conversation.incident_report import (
    IncidentReportSessionDetail,
    IncidentReportSessionSnapshot,
    IncidentReportSessionSummary,
)


class _FakeRecorder:
    def __init__(self, **_kwargs):
        self.events: list[dict] = []
        self.final: dict[str, str | None] = {}

    def add_event(self, *, event_type: str, detail: dict) -> None:
        self.events.append({"event_type": event_type, "detail": detail})

    def set_final(self, *, done_reason: str | None, error: str | None) -> None:
        self.final = {
            "done_reason": done_reason,
            "error": error,
        }

    async def flush(self) -> None:
        return None


def _build_detail() -> IncidentReportSessionDetail:
    now = datetime.now(UTC)
    return IncidentReportSessionDetail(
        id="incident-session-1",
        title="事故报告-2026/04/14 12:30",
        status="draft",
        created_at=now,
        updated_at=now,
        snapshot=IncidentReportSessionSnapshot(
            form_answers={},
            report_data=None,
            generated_attachment=None,
            generated_trace_id=None,
            generated_at=None,
            is_locked=False,
            fallback_used=False,
            polish_error=None,
        ),
    )


def _build_docx_attachment(attachment_id: str, name: str) -> ChatAttachment:
    return ChatAttachment(
        attachmentId=attachment_id,
        name=name,
        source="generated",
        mimeType="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        sizeBytes=64 * 1024,
        sizeLabel="64 KB",
        downloadUrl=f"/api/attachments/{attachment_id}/download",
        expiresAt=datetime.now(UTC),
    )


def test_generate_incident_attachment_runs_skill_chat_with_uploaded_json(monkeypatch) -> None:
    detail = _build_detail()
    generated_attachment = _build_docx_attachment(
        "generated-attachment-1",
        "incident-report.docx",
    )
    uploaded_attachment = _build_docx_attachment(
        "uploaded-attachment-1",
        "incident_data.json",
    ).model_copy(
        update={
            "source": "uploaded",
            "mime_type": "application/json",
        }
    )

    draft_report_data = {
        "detailed_description": "payment timeout",
        "root_cause": "db lock",
    }
    polished_report_data = {
        "detailed_description": "Payment timeout occurred during peak traffic.",
        "root_cause": "Database lock contention after deployment.",
    }
    captured = {
        "saved_summaries": [],
        "saved_snapshots": [],
        "stream_calls": 0,
    }

    async def fake_get_incident_report_session(session_id: str):
        assert session_id == "incident-session-1"
        return detail

    def fake_build_incident_interaction_config():
        return SimpleNamespace(steps=[object(), object()])

    def fake_build_report_data_from_snapshot(*, config, snapshot):
        assert len(config.steps) == 2
        assert snapshot is detail.snapshot
        return draft_report_data, []

    async def fake_save_incident_session_summary(summary: IncidentReportSessionSummary) -> None:
        captured["saved_summaries"].append(summary)

    async def fake_save_incident_session_snapshot(session_id: str, snapshot: IncidentReportSessionSnapshot) -> None:
        assert session_id == "incident-session-1"
        captured["saved_snapshots"].append(snapshot)

    async def fake_touch_incident_session_index(session_id: str, score: float) -> None:
        assert session_id == "incident-session-1"
        assert score > 0

    def fake_save_uploaded_attachment(
        *,
        raw_bytes: bytes,
        conversation_id: str,
        skill_id: str,
        file_name: str,
        mime_type: str | None,
        extracted_text: str | None = None,
    ):
        assert conversation_id == "incident-session-1"
        assert skill_id == "incident-report"
        assert file_name == "incident_data.json"
        assert mime_type == "application/json"
        assert raw_bytes.decode("utf-8").strip().startswith("{")
        assert extracted_text and '"detailed_description"' in extracted_text
        return uploaded_attachment

    def fake_build_persisted_uploaded_files_context(attachment_ids: list[str]) -> str | None:
        assert attachment_ids == ["uploaded-attachment-1"]
        return "uploaded-context"

    def fake_get_skill_interface(_skill_id: str):
        return SimpleNamespace(default_prompt="incident prompt")

    def fake_build_upstream_messages_for_skills(
        *,
        request,
        active_skill_ids,
        explicit_skill_ids,
        uploaded_files_context=None,
        extra_messages=None,
        **_kwargs,
    ):
        assert active_skill_ids == ["incident-report"]
        assert explicit_skill_ids == ["incident-report"]
        messages = [{"role": "system", "content": "incident prompt"}]
        if uploaded_files_context:
            messages.append({"role": "user", "content": uploaded_files_context})
        messages.extend([message.model_dump() for message in request.messages])
        if extra_messages:
            messages.extend(extra_messages)
        return messages

    def fake_build_skill_tools(_skill_id: str):
        return [{"type": "function", "function": {"name": "generate_incident_report"}}]

    async def fake_stream_chat_completion(*, model: str, messages: list[dict], tools):
        captured["stream_calls"] += 1
        assert model == "qwen3-coder-next:latest"
        assert any(message.get("content") == "uploaded-context" for message in messages)
        assert any("incident_data.json" in str(message.get("content", "")) for message in messages)
        assert tools
        yield {
            "message": {
                "role": "assistant",
                "content": "已完成润色并准备调用工具。",
                "tool_calls": [
                    {
                        "id": "tool-generate-1",
                        "function": {
                            "name": "generate_incident_report",
                            "arguments": {
                                "report_data": polished_report_data,
                                "output_name": "incident-report.docx",
                            },
                        },
                    }
                ],
            },
            "done": False,
        }
        yield {
            "message": {"role": "assistant", "content": ""},
            "done": True,
            "done_reason": "tool_calls",
        }
        yield None

    def fake_execute_skill_tool_call(*, request, state, tool_call):
        assert request.conversation_id == "incident-session-1"
        assert request.attachment_ids == ["uploaded-attachment-1"]
        assert request.reranker_model == "nomic-embed-text:latest"
        assert state.skill_id == "incident-report"
        assert tool_call["function"]["name"] == "generate_incident_report"
        return {"ok": True}, [generated_attachment]

    monkeypatch.setattr(incident_reports_module, "AgentTraceRecorder", _FakeRecorder)
    monkeypatch.setattr(incident_reports_module, "get_incident_report_session", fake_get_incident_report_session)
    monkeypatch.setattr(incident_reports_module, "_build_incident_interaction_config", fake_build_incident_interaction_config)
    monkeypatch.setattr(incident_reports_module, "_build_report_data_from_snapshot", fake_build_report_data_from_snapshot)
    monkeypatch.setattr(incident_reports_module, "save_incident_session_summary", fake_save_incident_session_summary)
    monkeypatch.setattr(incident_reports_module, "save_incident_session_snapshot", fake_save_incident_session_snapshot)
    monkeypatch.setattr(incident_reports_module, "touch_incident_session_index", fake_touch_incident_session_index)
    monkeypatch.setattr(incident_reports_module, "save_uploaded_attachment", fake_save_uploaded_attachment)
    monkeypatch.setattr(
        incident_reports_module,
        "build_persisted_uploaded_files_context",
        fake_build_persisted_uploaded_files_context,
    )
    monkeypatch.setattr(incident_reports_module, "get_skill_interface", fake_get_skill_interface)
    monkeypatch.setattr(
        incident_reports_module,
        "build_upstream_messages_for_skills",
        fake_build_upstream_messages_for_skills,
    )
    monkeypatch.setattr(incident_reports_module, "build_skill_tools", fake_build_skill_tools)
    monkeypatch.setattr(incident_reports_module, "stream_chat_completion", fake_stream_chat_completion)
    monkeypatch.setattr(incident_reports_module, "execute_skill_tool_call", fake_execute_skill_tool_call)
    monkeypatch.setattr(incident_reports_module.settings, "ollama_base_url", "http://ollama.local")
    monkeypatch.setattr(incident_reports_module.settings, "skill_tool_max_iterations", 3)

    result = asyncio.run(
        incident_reports_module.generate_incident_report_session_attachment(
            session_id="incident-session-1",
            model="qwen3-coder-next:latest",
            reranker_model="nomic-embed-text:latest",
        )
    )

    assert result is not None
    assert result.session.status == "generated"
    assert result.snapshot.is_locked is True
    assert result.snapshot.generated_attachment is not None
    assert result.snapshot.generated_attachment.attachment_id == "generated-attachment-1"
    assert result.snapshot.report_data == polished_report_data
    assert captured["stream_calls"] == 1
    assert captured["saved_summaries"][-1].status == "generated"
    assert captured["saved_snapshots"][-1].report_data == polished_report_data


def test_generate_incident_attachment_fails_when_skill_does_not_call_tool(monkeypatch) -> None:
    detail = _build_detail()
    draft_report_data = {
        "detailed_description": "payment timeout",
    }
    captured = {
        "saved_summaries": [],
        "saved_snapshots": [],
    }

    async def fake_get_incident_report_session(session_id: str):
        assert session_id == "incident-session-1"
        return detail

    def fake_build_incident_interaction_config():
        return SimpleNamespace(steps=[object()])

    def fake_build_report_data_from_snapshot(*_args, **_kwargs):
        return draft_report_data, []

    async def fake_save_incident_session_summary(summary: IncidentReportSessionSummary) -> None:
        captured["saved_summaries"].append(summary)

    async def fake_save_incident_session_snapshot(session_id: str, snapshot: IncidentReportSessionSnapshot) -> None:
        assert session_id == "incident-session-1"
        captured["saved_snapshots"].append(snapshot)

    async def fake_touch_incident_session_index(session_id: str, score: float) -> None:
        assert session_id == "incident-session-1"
        assert score > 0

    def fake_save_uploaded_attachment(**_kwargs):
        return _build_docx_attachment("uploaded-attachment-1", "incident_data.json").model_copy(
            update={"source": "uploaded", "mime_type": "application/json"}
        )

    def fake_build_persisted_uploaded_files_context(_attachment_ids: list[str]) -> str | None:
        return "uploaded-context"

    def fake_get_skill_interface(_skill_id: str):
        return SimpleNamespace(default_prompt="incident prompt")

    def fake_build_upstream_messages_for_skills(*, request, extra_messages=None, **_kwargs):
        messages = [{"role": "system", "content": "incident prompt"}]
        messages.extend([message.model_dump() for message in request.messages])
        if extra_messages:
            messages.extend(extra_messages)
        return messages

    def fake_build_skill_tools(_skill_id: str):
        return [{"type": "function", "function": {"name": "generate_incident_report"}}]

    async def fake_stream_chat_completion(*, model: str, messages: list[dict], tools):
        assert model == "qwen3-coder-next:latest"
        assert messages
        assert tools
        yield {
            "message": {
                "role": "assistant",
                "content": "我已经整理好了内容。",
            },
            "done": False,
        }
        yield {
            "message": {"role": "assistant", "content": ""},
            "done": True,
            "done_reason": "stop",
        }
        yield None

    monkeypatch.setattr(incident_reports_module, "AgentTraceRecorder", _FakeRecorder)
    monkeypatch.setattr(incident_reports_module, "get_incident_report_session", fake_get_incident_report_session)
    monkeypatch.setattr(incident_reports_module, "_build_incident_interaction_config", fake_build_incident_interaction_config)
    monkeypatch.setattr(incident_reports_module, "_build_report_data_from_snapshot", fake_build_report_data_from_snapshot)
    monkeypatch.setattr(incident_reports_module, "save_incident_session_summary", fake_save_incident_session_summary)
    monkeypatch.setattr(incident_reports_module, "save_incident_session_snapshot", fake_save_incident_session_snapshot)
    monkeypatch.setattr(incident_reports_module, "touch_incident_session_index", fake_touch_incident_session_index)
    monkeypatch.setattr(incident_reports_module, "save_uploaded_attachment", fake_save_uploaded_attachment)
    monkeypatch.setattr(
        incident_reports_module,
        "build_persisted_uploaded_files_context",
        fake_build_persisted_uploaded_files_context,
    )
    monkeypatch.setattr(incident_reports_module, "get_skill_interface", fake_get_skill_interface)
    monkeypatch.setattr(
        incident_reports_module,
        "build_upstream_messages_for_skills",
        fake_build_upstream_messages_for_skills,
    )
    monkeypatch.setattr(incident_reports_module, "build_skill_tools", fake_build_skill_tools)
    monkeypatch.setattr(incident_reports_module, "stream_chat_completion", fake_stream_chat_completion)
    monkeypatch.setattr(incident_reports_module.settings, "ollama_base_url", "http://ollama.local")
    monkeypatch.setattr(incident_reports_module.settings, "skill_tool_max_iterations", 2)

    with pytest.raises(RuntimeError, match="未触发 generate_incident_report 工具调用"):
        asyncio.run(
            incident_reports_module.generate_incident_report_session_attachment(
                session_id="incident-session-1",
                model="qwen3-coder-next:latest",
            )
        )

    assert captured["saved_summaries"][-1].status == "failed"
    assert captured["saved_snapshots"][-1].is_locked is False
    assert captured["saved_snapshots"][-1].generated_attachment is None
    assert captured["saved_snapshots"][-1].polish_error is not None
