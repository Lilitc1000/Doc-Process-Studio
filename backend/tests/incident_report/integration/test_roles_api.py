from unittest.mock import patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from doc_process_studio.core.security import create_access_token
from doc_process_studio.incident_report.router.roles import router as roles_router
from doc_process_studio.incident_report.router.dependencies import require_admin


def _create_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(roles_router)
    return app


def _auth_headers(user_id: str = "usr_test", username: str = "testuser") -> dict:
    token = create_access_token(user_id, username)
    return {"Authorization": f"Bearer {token}"}


def test_list_roles_requires_admin():
    app = _create_test_app()

    async def _reject_admin():
        raise HTTPException(status_code=403, detail="需要管理员权限")

    app.dependency_overrides[require_admin] = _reject_admin

    client = TestClient(app)
    resp = client.get("/api/incident-report/roles", headers=_auth_headers())
    assert resp.status_code == 403


def test_assign_role_requires_admin():
    app = _create_test_app()

    async def _reject_admin():
        raise HTTPException(status_code=403, detail="需要管理员权限")

    app.dependency_overrides[require_admin] = _reject_admin

    client = TestClient(app)
    resp = client.post(
        "/api/incident-report/roles",
        json={"user_id": "usr_test", "role": "reporter"},
        headers=_auth_headers(),
    )
    assert resp.status_code == 403


def test_revoke_role_requires_admin():
    app = _create_test_app()

    async def _reject_admin():
        raise HTTPException(status_code=403, detail="需要管理员权限")

    app.dependency_overrides[require_admin] = _reject_admin

    client = TestClient(app)
    resp = client.delete(
        "/api/incident-report/roles/usr_test/reporter",
        headers=_auth_headers(),
    )
    assert resp.status_code == 403
