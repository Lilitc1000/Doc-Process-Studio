"""解析状态相关 service 层单元测试（纯委托 + 错误转换）。"""

from __future__ import annotations

from typing import cast

import pytest

from doc_process_studio.knowledge_base.application.dtos import KBDocumentParseDetail
from doc_process_studio.knowledge_base.application.kb_service import KnowledgeBaseService
from doc_process_studio.knowledge_base.application.ports import KnowledgeBaseRepository
from doc_process_studio.knowledge_base.domain.errors import DocumentNotFoundError


class _FakeRepo:
    """只实现解析状态两个方法，其余端口方法不关心。"""

    def __init__(
        self,
        detail: KBDocumentParseDetail | None = None,
        trigger: bool = True,
    ) -> None:
        self.detail = detail
        self.trigger = trigger
        self.calls: list[tuple[str, str]] = []

    async def get_document_parse_detail(self, document_id: str) -> KBDocumentParseDetail | None:
        self.calls.append(("detail", document_id))
        return self.detail

    async def trigger_document_parse(self, document_id: str) -> bool:
        self.calls.append(("trigger", document_id))
        return self.trigger


def _service(detail: KBDocumentParseDetail | None = None, trigger: bool = True) -> KnowledgeBaseService:
    return KnowledgeBaseService(repository=cast(KnowledgeBaseRepository, _FakeRepo(detail, trigger)))


async def test_service_get_parse_detail_returns_dto() -> None:
    svc = _service(detail=KBDocumentParseDetail(document_id="d1", file_name="x.pdf"))
    detail = await svc.get_parse_detail("d1")
    assert detail.document_id == "d1"
    assert ("detail", "d1") in svc._repo.calls  # type: ignore[attr-defined]


async def test_service_get_parse_detail_raises_when_none() -> None:
    svc = _service(detail=None)
    with pytest.raises(DocumentNotFoundError):
        await svc.get_parse_detail("d1")


async def test_service_reparse_raises_when_false() -> None:
    svc = _service(trigger=False)
    with pytest.raises(DocumentNotFoundError):
        await svc.reparse_document("d1")
    assert ("trigger", "d1") in svc._repo.calls  # type: ignore[attr-defined]


async def test_service_reparse_succeeds() -> None:
    svc = _service(trigger=True)
    await svc.reparse_document("d1")
    assert ("trigger", "d1") in svc._repo.calls  # type: ignore[attr-defined]
