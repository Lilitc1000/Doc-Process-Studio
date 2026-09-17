"""解析状态接口的行为契约测试（鉴权 + 正常返回 + 错误映射）。"""

from __future__ import annotations

from typing import cast

from fastapi import FastAPI
from fastapi.testclient import TestClient

from doc_process_studio.common.security.security import create_access_token
from doc_process_studio.knowledge_base.application.dtos import KBDocumentParseDetail
from doc_process_studio.knowledge_base.application.kb_service import KnowledgeBaseService
from doc_process_studio.knowledge_base.application.ports import KnowledgeBaseRepository
from doc_process_studio.knowledge_base.infrastructure.dependencies import get_kb_service
from doc_process_studio.knowledge_base.router.projects import router as kb_router


def _auth_headers(user_id: str = "usr_test") -> dict:
    token = create_access_token(user_id, "testuser")
    return {"Authorization": f"Bearer {token}"}


class _FakeRepo:
    def __init__(
        self,
        detail: KBDocumentParseDetail | None = None,
        trigger: bool = True,
    ) -> None:
        self.detail = detail
        self.trigger = trigger

    async def get_document_parse_detail(self, _document_id: str) -> KBDocumentParseDetail | None:
        return self.detail

    async def trigger_document_parse(self, _document_id: str) -> bool:
        return self.trigger


def _fake_service(detail: KBDocumentParseDetail | None = None, trigger: bool = True) -> KnowledgeBaseService:
    return KnowledgeBaseService(repository=cast(KnowledgeBaseRepository, _FakeRepo(detail, trigger)))


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(kb_router)
    app.dependency_overrides[get_kb_service] = lambda: _fake_service()
    return app


def test_parse_detail_requires_auth() -> None:
    resp = TestClient(_app()).get("/api/knowledge-base/documents/doc-1/parse-detail")
    assert resp.status_code in (401, 403)


def test_reparse_requires_auth() -> None:
    resp = TestClient(_app()).post("/api/knowledge-base/documents/doc-1/parse")
    assert resp.status_code in (401, 403)


def test_get_parse_detail_returns_dto() -> None:
    app = _app()
    app.dependency_overrides[get_kb_service] = lambda: _fake_service(
        detail=KBDocumentParseDetail(
            document_id="doc-1",
            file_name="report.pdf",
            parse_status="FAIL",
            is_indexed=False,
            progress=-1.0,
            chunk_count=0,
            token_count=0,
            process_duration=None,
            message="[ERROR] model not found",
            updated_at=None,
        )
    )
    resp = TestClient(app).get(
        "/api/knowledge-base/documents/doc-1/parse-detail",
        headers=_auth_headers(),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["document_id"] == "doc-1"
    assert body["parse_status"] == "FAIL"
    assert "[ERROR]" in body["message"]


def test_reparse_returns_202() -> None:
    resp = TestClient(_app()).post(
        "/api/knowledge-base/documents/doc-1/parse",
        headers=_auth_headers(),
    )
    assert resp.status_code == 202


def test_reparse_unknown_document_404() -> None:
    app = _app()
    app.dependency_overrides[get_kb_service] = lambda: _fake_service(trigger=False)
    resp = TestClient(app).post(
        "/api/knowledge-base/documents/doc-404/parse",
        headers=_auth_headers(),
    )
    assert resp.status_code == 404
