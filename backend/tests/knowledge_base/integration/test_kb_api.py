from fastapi import FastAPI
from fastapi.testclient import TestClient

from doc_process_studio.core.security import create_access_token
from doc_process_studio.knowledge_base.router.projects import router as kb_router


def _create_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(kb_router)
    return app


def _auth_headers(user_id: str = "usr_test") -> dict:
    token = create_access_token(user_id, "testuser")
    return {"Authorization": f"Bearer {token}"}


def test_list_projects_requires_auth() -> None:
    app = _create_test_app()
    client = TestClient(app)
    resp = client.get("/api/knowledge-base/projects")
    assert resp.status_code == 401 or resp.status_code == 403


def test_create_project_requires_auth() -> None:
    app = _create_test_app()
    client = TestClient(app)
    resp = client.post(
        "/api/knowledge-base/projects",
        json={"name": "test", "description": ""},
    )
    assert resp.status_code == 401 or resp.status_code == 403


def test_get_project_requires_auth() -> None:
    app = _create_test_app()
    client = TestClient(app)
    resp = client.get("/api/knowledge-base/projects/proj-123")
    assert resp.status_code == 401 or resp.status_code == 403


def test_rename_project_requires_auth() -> None:
    app = _create_test_app()
    client = TestClient(app)
    resp = client.put(
        "/api/knowledge-base/projects/proj-123/rename",
        json={"name": "new-name"},
    )
    assert resp.status_code == 401 or resp.status_code == 403


def test_delete_project_requires_auth() -> None:
    app = _create_test_app()
    client = TestClient(app)
    resp = client.delete("/api/knowledge-base/projects/proj-123")
    assert resp.status_code == 401 or resp.status_code == 403


def test_create_folder_requires_auth() -> None:
    app = _create_test_app()
    client = TestClient(app)
    resp = client.post(
        "/api/knowledge-base/projects/proj-123/folders",
        json={"name": "folder1"},
    )
    assert resp.status_code == 401 or resp.status_code == 403


def test_rename_folder_requires_auth() -> None:
    app = _create_test_app()
    client = TestClient(app)
    resp = client.put(
        "/api/knowledge-base/folders/folder-123/rename",
        json={"name": "new-name"},
    )
    assert resp.status_code == 401 or resp.status_code == 403


def test_delete_folder_requires_auth() -> None:
    app = _create_test_app()
    client = TestClient(app)
    resp = client.delete("/api/knowledge-base/folders/folder-123")
    assert resp.status_code == 401 or resp.status_code == 403


def test_get_tree_requires_auth() -> None:
    app = _create_test_app()
    client = TestClient(app)
    resp = client.get("/api/knowledge-base/projects/proj-123/tree")
    assert resp.status_code == 401 or resp.status_code == 403


def test_upload_document_requires_auth() -> None:
    app = _create_test_app()
    client = TestClient(app)
    resp = client.post("/api/knowledge-base/projects/proj-123/documents/upload")
    assert resp.status_code == 401 or resp.status_code == 403


def test_delete_document_requires_auth() -> None:
    app = _create_test_app()
    client = TestClient(app)
    resp = client.delete("/api/knowledge-base/documents/doc-123")
    assert resp.status_code == 401 or resp.status_code == 403


def test_projects_simple_requires_auth() -> None:
    app = _create_test_app()
    client = TestClient(app)
    resp = client.get("/api/knowledge-base/projects-simple")
    assert resp.status_code == 401 or resp.status_code == 403
