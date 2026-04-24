from datetime import UTC, datetime

from fastapi.testclient import TestClient

import doc_process_studio.main as main_module
import doc_process_studio.incident_report.router.incident_reports as incident_router_module
from doc_process_studio.incident_report.models.incident_report import (
    IncidentReportSessionSnapshot,
    IncidentReportSessionSummary,
)
from doc_process_studio.incident_report.schemas.response import (
    IncidentReportPreviewResponse,
    IncidentReportSessionDetail,
    IncidentReportSessionListResponse,
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


def test_api_incident_report_preview(monkeypatch) -> None:
    async def fake_preview_incident_report_attachment(**kwargs) -> IncidentReportPreviewResponse:
        assert kwargs["session_id"] == "incident-session-1"
        assert kwargs["version"] == 1
        return IncidentReportPreviewResponse(
            source="version",
            version=1,
            label="V1 2026-04-14 12:40:00",
            html="<p>preview</p>",
            warnings=[],
        )

    monkeypatch.setattr(
        incident_router_module,
        "preview_incident_report_attachment",
        fake_preview_incident_report_attachment,
    )

    client = TestClient(main_module.app)
    response = client.post(
        "/api/incident-report/sessions/incident-session-1/preview",
        json={"version": 1},
    )

    assert response.status_code == 200
    assert response.json()["source"] == "version"
    assert response.json()["html"] == "<p>preview</p>"
