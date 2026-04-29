from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from doc_process_studio.core.security import create_access_token
from doc_process_studio.incident_report.router.reports import router as reports_router
from doc_process_studio.incident_report.schemas.response import IncidentReportDetail


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


def test_report_status_transitions():
    app = _create_test_app()

    async def _fake_has_permission(user_id, permission):
        return True

    async def _fake_create(**kwargs):
        return _mock_report()

    async def _fake_submit(**kwargs):
        return _mock_report(status="pending", submitted_at="2026-04-20T01:00:00Z")

    async def _fake_create_audit_log(**kwargs):
        return None

    async def _fake_load_orm(report_id):
        from types import SimpleNamespace
        return SimpleNamespace(form_data={}, reporter_id="usr_test")

    def _fake_validate(form_data):
        return []

    with patch(
        "doc_process_studio.incident_report.router.reports.has_permission",
        _fake_has_permission,
    ), patch(
        "doc_process_studio.incident_report.router.reports.create_report",
        _fake_create,
    ), patch(
        "doc_process_studio.incident_report.router.reports.submit_report",
        _fake_submit,
    ), patch(
        "doc_process_studio.incident_report.service.report.create_audit_log",
        _fake_create_audit_log,
    ), patch(
        "doc_process_studio.incident_report.service.report_store.load_report_orm",
        _fake_load_orm,
    ), patch(
        "doc_process_studio.incident_report.service.form_validation.validate_form_data_for_submit",
        _fake_validate,
    ):
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

    async def _fake_list_logs(report_id):
        return []

    with patch(
        "doc_process_studio.incident_report.router.reports.list_audit_logs",
        _fake_list_logs,
    ), patch(
        "doc_process_studio.incident_report.router.reports.audit_orm_to_entry",
        lambda r: [],
    ):
        client = TestClient(app)
        logs_resp = client.get(
            "/api/incident-report/reports/rep-1/audit-logs",
            headers=_auth_headers(),
        )
        assert logs_resp.status_code == 200


def test_report_comments():
    app = _create_test_app()
    from datetime import UTC, datetime

    now = datetime.now(UTC)

    async def _fake_create(**kwargs):
        from doc_process_studio.incident_report.models.incident_report_orm import IncidentComment

        return IncidentComment(
            id="cmt-1",
            report_id="rep-1",
            author_id="usr_test",
            content="测试评论",
            parent_id=None,
            created_at=now,
        )

    async def _fake_list(report_id):
        return []

    with patch(
        "doc_process_studio.incident_report.router.reports.create_comment_record",
        _fake_create,
    ), patch(
        "doc_process_studio.incident_report.router.reports.list_comment_records",
        _fake_list,
    ):
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
