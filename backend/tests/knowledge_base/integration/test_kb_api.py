"""知识库 API 接口层的鉴权契约测试。

知识库已不依赖本地数据库，这里只校验"未登录时一律拒绝"这一契约，
不涉及具体后端实现。
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from doc_process_studio.common.security.security import create_access_token
from doc_process_studio.knowledge_base.router.projects import router as kb_router


def _create_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(kb_router)
    return app


def _auth_headers(user_id: str = "usr_test") -> dict:
    token = create_access_token(user_id, "testuser")
    return {"Authorization": f"Bearer {token}"}


# ── 项目 ──


def test_list_projects_requires_auth() -> None:
    resp = TestClient(_create_test_app()).get("/api/knowledge-base/projects")
    assert resp.status_code in (401, 403)


def test_create_project_requires_auth() -> None:
    resp = TestClient(_create_test_app()).post(
        "/api/knowledge-base/projects",
        json={"name": "test", "description": ""},
    )
    assert resp.status_code in (401, 403)


def test_get_project_requires_auth() -> None:
    resp = TestClient(_create_test_app()).get("/api/knowledge-base/projects/ds-123")
    assert resp.status_code in (401, 403)


def test_rename_project_requires_auth() -> None:
    resp = TestClient(_create_test_app()).put(
        "/api/knowledge-base/projects/ds-123/rename",
        json={"name": "new-name"},
    )
    assert resp.status_code in (401, 403)


def test_delete_project_requires_auth() -> None:
    resp = TestClient(_create_test_app()).delete("/api/knowledge-base/projects/ds-123")
    assert resp.status_code in (401, 403)


def test_get_tree_requires_auth() -> None:
    resp = TestClient(_create_test_app()).get("/api/knowledge-base/projects/ds-123/tree")
    assert resp.status_code in (401, 403)


# ── 文档 ──


def test_upload_document_requires_auth() -> None:
    resp = TestClient(_create_test_app()).post("/api/knowledge-base/projects/ds-123/documents/upload")
    assert resp.status_code in (401, 403)


def test_delete_document_requires_auth() -> None:
    resp = TestClient(_create_test_app()).delete("/api/knowledge-base/documents/doc-123")
    assert resp.status_code in (401, 403)


# ── $ 提及列表 ──


def test_projects_simple_requires_auth() -> None:
    resp = TestClient(_create_test_app()).get("/api/knowledge-base/projects-simple")
    assert resp.status_code in (401, 403)


def test_folder_endpoints_are_removed() -> None:
    """文件夹由 RAGFlow 派生，本服务不再提供文件夹写接口。"""

    app = _create_test_app()
    resp = TestClient(app).post(
        "/api/knowledge-base/projects/ds-123/folders",
        json={"name": "folder1"},
        headers=_auth_headers(),
    )
    assert resp.status_code == 404
