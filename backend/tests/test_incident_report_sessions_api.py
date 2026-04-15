from datetime import UTC, datetime

from fastapi.testclient import TestClient

import doc_process_studio.main as main_module
import doc_process_studio.routers.conversation.incident_reports as incident_router_module
from doc_process_studio.models.conversation.incident_report import (
    IncidentReportGenerateResponse,
    IncidentReportSessionDetail,
    IncidentReportSessionListResponse,
    IncidentReportSessionSnapshot,
    IncidentReportSessionSummary,
)


def _build_summary(
    *,
    session_id: str = "incident-session-1",
    status: str = "draft",
) -> IncidentReportSessionSummary:
    now = datetime.now(UTC)
    return IncidentReportSessionSummary(
        id=session_id,
        title="事故报告-2026/04/14 12:30",
        status=status,  # type: ignore[arg-type]
        created_at=now,
        updated_at=now,
    )


def _build_snapshot() -> IncidentReportSessionSnapshot:
    return IncidentReportSessionSnapshot(
        form_answers={},
        report_data=None,
        generated_attachment=None,
        generated_trace_id=None,
        generated_at=None,
        is_locked=False,
        fallback_used=False,
        polish_error=None,
    )


def test_api_incident_report_sessions_list(monkeypatch) -> None:
    async def fake_list_incident_report_sessions() -> IncidentReportSessionListResponse:
        return IncidentReportSessionListResponse(
            sessions=[_build_summary()],
        )

    monkeypatch.setattr(
        incident_router_module,
        "list_incident_report_sessions",
        fake_list_incident_report_sessions,
    )

    client = TestClient(main_module.app)
    response = client.get("/api/incident-report/sessions")

    assert response.status_code == 200
    assert response.json()["sessions"][0]["id"] == "incident-session-1"


def test_api_incident_report_session_update(monkeypatch) -> None:
    async def fake_update_incident_report_session_snapshot(**kwargs) -> IncidentReportSessionDetail:
        assert kwargs["session_id"] == "incident-session-1"
        return IncidentReportSessionDetail(
            **_build_summary().model_dump(),
            snapshot=_build_snapshot(),
        )

    monkeypatch.setattr(
        incident_router_module,
        "update_incident_report_session_snapshot",
        fake_update_incident_report_session_snapshot,
    )

    client = TestClient(main_module.app)
    response = client.put(
        "/api/incident-report/sessions/incident-session-1",
        json={
            "snapshot": {
                "form_answers": {},
            }
        },
    )

    assert response.status_code == 200
    assert response.json()["id"] == "incident-session-1"


def test_api_incident_report_generate(monkeypatch) -> None:
    async def fake_generate_incident_report_session_attachment(**kwargs) -> IncidentReportGenerateResponse:
        assert kwargs["session_id"] == "incident-session-1"
        assert kwargs["model"] == "qwen3-coder-next:latest"
        assert kwargs["reranker_model"] == "nomic-embed-text:latest"
        summary = _build_summary(status="generated")
        snapshot = _build_snapshot()
        return IncidentReportGenerateResponse(
            session=summary,
            snapshot=snapshot,
            trace_id="trace-incident-1",
        )

    monkeypatch.setattr(
        incident_router_module,
        "generate_incident_report_session_attachment",
        fake_generate_incident_report_session_attachment,
    )

    client = TestClient(main_module.app)
    response = client.post(
        "/api/incident-report/sessions/incident-session-1/generate",
        json={
            "model": "qwen3-coder-next:latest",
            "reranker_model": "nomic-embed-text:latest",
        },
    )

    assert response.status_code == 200
    assert response.json()["trace_id"] == "trace-incident-1"
