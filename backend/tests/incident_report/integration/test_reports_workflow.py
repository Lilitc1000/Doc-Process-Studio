from datetime import UTC, datetime
from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from doc_process_studio.core.security import create_access_token
from doc_process_studio.incident_report.infrastructure.dependencies import (
    get_audit_query_service,
    get_comment_service,
    get_report_application_service,
)
from doc_process_studio.incident_report.router.reports import router as reports_router
from doc_process_studio.incident_report.schemas.response import (
    IncidentCommentEntry,
    IncidentReportDetail,
)


def _create_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(reports_router)
    return app


def _auth_headers(user_id: str = "usr_test", username: str = "testuser") -> dict:
    token = create_access_token(user_id, username)
    return {"Authorization": f"Bearer {token}"}


def _mock_report(**overrides) -> IncidentReportDetail:
    defaults = dict(
        id="rep-1",
        ref_no="DAS-001",
        title="工作流测试报告",
        status="draft",
        severity=None,
        reporter_id="usr_test",
        reporter_name=None,
        assignee_id=None,
        assignee_name=None,
        verifier_id=None,
        verifier_name=None,
        fault_date=None,
        created_at="2026-04-20T00:00:00Z",
        updated_at="2026-04-20T00:00:00Z",
    )
    defaults.update(overrides)
    return IncidentReportDetail(**defaults)


def _override_service(app: FastAPI, service: AsyncMock) -> None:
    """用 FastAPI 官方 dependency_overrides 覆盖 application service 依赖。"""
    app.dependency_overrides[get_report_application_service] = lambda: service


def test_report_status_transitions():
    app = _create_test_app()

    fake_service = AsyncMock()
    fake_service.create.return_value = _mock_report(status="draft")
    fake_service.submit.return_value = _mock_report(
        status="pending", submitted_at="2026-04-20T01:00:00Z"
    )
    _override_service(app, fake_service)

    client = TestClient(app)

    create_resp = client.post(
        "/api/incident-report/reports",
        json={"title": "工作流测试报告", "form_data": {}},
        headers=_auth_headers(),
    )
    assert create_resp.status_code == 200
    assert create_resp.json()["status"] == "draft"

    submit_resp = client.post(
        "/api/incident-report/reports/rep-1/submit",
        headers=_auth_headers(),
    )
    assert submit_resp.status_code == 200
    assert submit_resp.json()["status"] == "pending"


def test_report_audit_logs():
    app = _create_test_app()

    fake_audit_service = AsyncMock()
    fake_audit_service.list_audit_logs.return_value = []
    app.dependency_overrides[get_audit_query_service] = lambda: fake_audit_service

    client = TestClient(app)
    logs_resp = client.get(
        "/api/incident-report/reports/rep-1/audit-logs",
        headers=_auth_headers(),
    )
    assert logs_resp.status_code == 200


def test_report_comments():
    app = _create_test_app()

    now = datetime.now(UTC)

    fake_comment_service = AsyncMock()
    fake_comment_service.add_comment.return_value = IncidentCommentEntry(
        id="cmt-1",
        report_id="rep-1",
        author_id="usr_test",
        author_name="testuser",
        content="测试评论",
        parent_id=None,
        created_at=now.isoformat(),
    )
    fake_comment_service.list_comments.return_value = []
    app.dependency_overrides[get_comment_service] = lambda: fake_comment_service

    client = TestClient(app)

    comment_resp = client.post(
        "/api/incident-report/reports/rep-1/comments",
        json={"content": "测试评论"},
        headers=_auth_headers(),
    )
    assert comment_resp.status_code == 200
    assert comment_resp.json()["content"] == "测试评论"

    list_resp = client.get(
        "/api/incident-report/reports/rep-1/comments",
        headers=_auth_headers(),
    )
    assert list_resp.status_code == 200
