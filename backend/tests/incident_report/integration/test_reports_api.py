from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from doc_process_studio.common.security.security import create_access_token
from doc_process_studio.incident_report.application.dtos import (
    IncidentReportDetail,
    IncidentReportListResponse,
)
from doc_process_studio.incident_report.domain.values.errors import PermissionDeniedError
from doc_process_studio.incident_report.infrastructure.dependencies import (
    get_report_application_service,
    get_role_service,
)
from doc_process_studio.incident_report.router.reports import router as reports_router
from doc_process_studio.incident_report.router.roles import router as roles_router


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


def _override_service(app: FastAPI, service: AsyncMock) -> None:
    """用 FastAPI 官方 dependency_overrides 覆盖 application service 依赖。"""
    app.dependency_overrides[get_report_application_service] = lambda: service


def test_list_reports_returns_structure():
    app = _create_test_app()

    fake_service = AsyncMock()
    fake_service.list.return_value = IncidentReportListResponse(total=0, items=[])
    _override_service(app, fake_service)

    client = TestClient(app)
    resp = client.get("/api/incident-report/reports", headers=_auth_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "items" in data


def test_get_report_detail_not_found():
    app = _create_test_app()

    fake_service = AsyncMock()
    fake_service.get.return_value = None
    _override_service(app, fake_service)

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

    from doc_process_studio.incident_report.application.dtos import (
        IncidentUserPermissionsResponse,
    )

    fake_role_service = AsyncMock()
    fake_role_service.get_my_permissions.return_value = IncidentUserPermissionsResponse(
        user_id="usr_test",
        roles=["reporter"],
        permissions=["report:view"],
    )
    app.dependency_overrides[get_role_service] = lambda: fake_role_service

    client = TestClient(app)
    resp = client.get("/api/incident-report/roles/me", headers=_auth_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert "roles" in data


def test_create_report_success():
    app = _create_test_app()

    fake_service = AsyncMock()
    fake_service.create.return_value = _mock_report()
    _override_service(app, fake_service)

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

    fake_service = AsyncMock()
    fake_service.approve.side_effect = PermissionDeniedError("需要审核人权限")
    _override_service(app, fake_service)

    client = TestClient(app)
    resp = client.post(
        "/api/incident-report/reports/test-id/approve",
        json={"comment": "通过"},
        headers=_auth_headers(),
    )
    assert resp.status_code == 403
