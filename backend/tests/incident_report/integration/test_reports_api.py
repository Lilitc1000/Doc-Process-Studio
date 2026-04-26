from unittest.mock import patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from doc_process_studio.core.security import create_access_token
from doc_process_studio.incident_report.router.reports import router as reports_router
from doc_process_studio.incident_report.router.roles import router as roles_router
from doc_process_studio.incident_report.router.dependencies import (
    require_verifier_or_admin,
)
from doc_process_studio.incident_report.schemas.response import (
    IncidentReportDetail,
    IncidentReportListResponse,
)


def _create_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(reports_router)
    app.include_router(roles_router)
    return app


def _auth_headers(user_id: str = "usr_test", username: str = "testuser") -> dict:
    token = create_access_token(user_id, username)
    return {"Authorization": f"Bearer {token}"}


def _mock_report(**overrides) -> IncidentReportDetail:
    defaults = dict(
        id="rep-1",
        ref_no="DAS-001",
        title="测试报告",
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


def test_list_reports_returns_structure():
    app = _create_test_app()

    async def _fake_list(**kwargs):
        return IncidentReportListResponse(total=0, items=[])

    with patch(
        "doc_process_studio.incident_report.router.reports.list_incident_reports",
        _fake_list,
    ):
        client = TestClient(app)
        resp = client.get("/api/incident-report/reports", headers=_auth_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "items" in data


def test_get_report_detail_not_found():
    app = _create_test_app()

    async def _fake_get(report_id):
        return None

    with patch(
        "doc_process_studio.incident_report.router.reports.get_report",
        _fake_get,
    ):
        client = TestClient(app)
        resp = client.get(
            "/api/incident-report/reports/nonexistent-id",
            headers=_auth_headers(),
        )
        assert resp.status_code == 404


def test_submit_report_requires_auth():
    app = _create_test_app()
    client = TestClient(app)
    resp = client.post("/api/incident-report/reports/test-id/submit")
    assert resp.status_code in (401, 403)


def test_get_my_roles():
    app = _create_test_app()

    async def _fake_get_roles(user_id):
        return {"reporter"}

    with patch(
        "doc_process_studio.incident_report.router.roles.get_user_incident_roles",
        _fake_get_roles,
    ):
        client = TestClient(app)
        resp = client.get("/api/incident-report/roles/me", headers=_auth_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert "roles" in data


def test_create_report_success():
    app = _create_test_app()

    async def _fake_has_role(user_id, role):
        return True

    async def _fake_get_roles(user_id):
        return {"reporter"}

    async def _fake_create(**kwargs):
        return _mock_report()

    with patch(
        "doc_process_studio.incident_report.router.reports.has_incident_role",
        _fake_has_role,
    ), patch(
        "doc_process_studio.incident_report.router.reports.get_user_incident_roles",
        _fake_get_roles,
    ), patch(
        "doc_process_studio.incident_report.router.reports.create_report",
        _fake_create,
    ):
        client = TestClient(app)
        resp = client.post(
            "/api/incident-report/reports",
            json={"title": "测试报告", "form_data": {}},
            headers=_auth_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "测试报告"
        assert data["status"] == "draft"


def test_approve_report_requires_verifier_role():
    app = _create_test_app()

    async def _reject():
        raise HTTPException(status_code=403, detail="需要审核人或管理员权限")

    app.dependency_overrides[require_verifier_or_admin] = _reject

    client = TestClient(app)
    resp = client.post(
        "/api/incident-report/reports/test-id/approve",
        json={"comment": "通过"},
        headers=_auth_headers(),
    )
    assert resp.status_code == 403
