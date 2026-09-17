"""RAGFlow 仓储单元测试。

用 ``FakeClient`` 替换 HTTP 客户端，并用内存字典替换 Redis 缓存，
因此不依赖网络与 Redis 实例。
"""

from __future__ import annotations

from typing import Any, cast

import pytest

from doc_process_studio.knowledge_base.application.dtos import KBTreeNodeFolder
from doc_process_studio.knowledge_base.infrastructure.ragflow_client import RagflowClient
from doc_process_studio.knowledge_base.infrastructure.ragflow_repository import (
    RagflowKnowledgeBaseRepository,
)

_FAKE_REDIS: dict[str, Any] = {}
_FAKE_TTL: dict[str, int | None] = {}


class FakeClient:
    """按仓储需要的最小接口实现，记录调用以便断言缓存效果。"""

    def __init__(self, **payloads: Any) -> None:
        self.datasets: list[dict[str, Any]] = payloads.get("datasets", [])
        self.folders: dict[str, list[dict[str, Any]]] = payloads.get("folders", {})
        self.documents: dict[str, list[dict[str, Any]]] = payloads.get("documents", {})
        self.created: dict[str, Any] = payloads.get("created", {})
        self.calls: list[str] = []

    async def list_datasets(self) -> list[dict[str, Any]]:
        self.calls.append("list_datasets")
        return self.datasets

    async def get_dataset(self, dataset_id: str) -> dict[str, Any] | None:
        self.calls.append("get_dataset")
        return next((d for d in self.datasets if d.get("id") == dataset_id), None)  # noqa: ARG002

    async def create_dataset(self, name: str, description: str = "") -> dict[str, Any] | None:
        self.calls.append("create_dataset")
        return {"id": self.created.get("id", "ds-new"), "name": name, "description": description or None}

    async def update_dataset(self, dataset_id: str, new_name: str) -> dict[str, Any] | None:
        self.calls.append("update_dataset")
        dataset = await self.get_dataset(dataset_id)
        return {**(dataset or {"id": dataset_id}), "name": new_name} if dataset else None

    async def delete_dataset(self, dataset_id: str) -> bool:
        self.calls.append("delete_dataset")
        return any(d.get("id") == dataset_id for d in self.datasets)

    async def list_folders(self, dataset_id: str) -> list[dict[str, Any]]:
        self.calls.append(f"list_folders:{dataset_id}")
        return self.folders.get(dataset_id, [])

    async def list_documents(self, dataset_id: str) -> list[dict[str, Any]]:
        self.calls.append(f"list_documents:{dataset_id}")
        return self.documents.get(dataset_id, [])

    async def upload_document(
        self,
        _dataset_id: str,
        file_name: str,
        file_bytes: bytes,
    ) -> dict[str, Any] | None:
        self.calls.append("upload_document")
        return {
            "id": "doc-new",
            "name": file_name,
            "size": len(file_bytes),
            "create_time": 1789112148521,
        }

    async def trigger_parse(self, _dataset_id: str, _document_ids: list[str]) -> bool:
        self.calls.append("trigger_parse")
        return True

    async def get_document(self, _dataset_id: str, document_id: str) -> dict[str, Any] | None:
        self.calls.append("get_document")
        return {"id": document_id, "name": "report.pdf", "chunk_count": 12, "size": 2048, "create_time": 1789112148521}

    async def delete_documents(self, _dataset_id: str, document_ids: list[str]) -> bool:
        self.calls.append("delete_documents")
        return document_ids == ["doc-1"]

    async def retrieve_chunks(
        self,
        _dataset_ids: list[str],
        _query: str,
        _top_k: int | None = None,
    ) -> list[dict[str, Any]]:
        self.calls.append("retrieve_chunks")
        return [
            {
                "content": "片段",
                "score": 0.9,
                "document_id": "doc-1",
                "source": "report.pdf",
                "file_name": "report.pdf",
            }
        ]


@pytest.fixture(autouse=True)
def _clean_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    _FAKE_REDIS.clear()
    _FAKE_TTL.clear()
    repo_module = RagflowKnowledgeBaseRepository.__module__
    monkeypatch.setattr(f"{repo_module}.get_json", _fake_get_json)
    monkeypatch.setattr(f"{repo_module}.set_json", _fake_set_json)
    monkeypatch.setattr(f"{repo_module}.delete_key", _fake_delete_key)


async def _fake_get_json(key: str) -> Any:
    return _FAKE_REDIS.get(key)


async def _fake_set_json(key: str, payload: Any, ttl_seconds: int | None = None) -> None:
    _FAKE_REDIS[key] = payload
    _FAKE_TTL[key] = ttl_seconds


async def _fake_delete_key(key: str) -> int:
    return 1 if _FAKE_REDIS.pop(key, None) is not None else 0


def _repository(**payloads: Any) -> RagflowKnowledgeBaseRepository:
    return RagflowKnowledgeBaseRepository(cast(RagflowClient, FakeClient(**payloads)))


_DATASETS = [
    {"id": "ds-1", "name": "事故库", "document_count": 3, "create_time": 1789112148521, "update_time": 1789112148999},
    {"id": "ds-2", "name": "出租车平台", "document_count": 1},
]


# ── 项目映射 ──


async def test_list_projects_maps_dataset_fields() -> None:
    repo = _repository(datasets=_DATASETS)
    projects = await repo.list_projects()
    assert [p.id for p in projects] == ["ds-1", "ds-2"]
    assert projects[0].name == "事故库"
    assert projects[0].document_count == 3
    assert projects[0].created_at.year == 2026


async def test_list_projects_always_reflects_ragflow() -> None:
    """dataset 列表不缓存：RAGFlow 侧新增后，下一次读取必须能看到。"""
    client = FakeClient(datasets=_DATASETS)
    repo = RagflowKnowledgeBaseRepository(cast(RagflowClient, client))
    first = await repo.list_projects()
    client.datasets = [*client.datasets, {"id": "ds-3", "name": "新库", "document_count": 0}]
    second = await repo.list_projects()
    assert [p.id for p in first] == ["ds-1", "ds-2"]
    assert [p.id for p in second] == ["ds-1", "ds-2", "ds-3"]
    assert client.calls.count("list_datasets") == 2


async def test_list_projects_reflects_deletion_in_ragflow() -> None:
    """RAGFlow 侧删除 dataset 后，应用侧必须同步消失（回归用例）。"""
    client = FakeClient(datasets=_DATASETS)
    repo = RagflowKnowledgeBaseRepository(cast(RagflowClient, client))
    await repo.list_projects()
    client.datasets = [d for d in client.datasets if d["id"] != "ds-1"]
    projects = await repo.list_projects()
    assert [p.id for p in projects] == ["ds-2"]


async def test_get_project_returns_none_when_missing() -> None:
    repo = _repository(datasets=_DATASETS)
    assert await repo.get_project("ds-404") is None
    assert (await repo.get_project("ds-1")) is not None


async def test_create_project_invalidates_cache() -> None:
    client = FakeClient(datasets=_DATASETS, created={"id": "ds-3"})
    repo = RagflowKnowledgeBaseRepository(cast(RagflowClient, client))
    await repo.list_projects()
    project = await repo.create_project("新库", "描述")
    assert project.id == "ds-3"
    await repo.list_projects()
    assert client.calls.count("list_datasets") == 2


# ── 树构建 ──


async def test_build_tree_is_flat_when_no_folders() -> None:
    repo = _repository(
        datasets=_DATASETS,
        documents={"ds-1": [{"id": "doc-1", "name": "a.pdf", "chunk_count": 5}]},
    )
    tree = await repo.build_tree("ds-1")
    assert len(tree) == 1
    assert tree[0].type == "document"


async def test_build_tree_nests_folders_when_present() -> None:
    repo = _repository(
        datasets=_DATASETS,
        folders={"ds-1": [{"id": "f-1", "name": "根目录"}, {"id": "f-2", "name": "子目录", "parent_id": "f-1"}]},
        documents={"ds-1": [{"id": "doc-1", "name": "a.pdf"}]},
    )
    tree = await repo.build_tree("ds-1")
    assert len(tree) == 2  # 根文件夹 + 未归属文档
    folder = next(node for node in tree if isinstance(node, KBTreeNodeFolder) and node.id == "f-1")
    assert [child.id for child in folder.children] == ["f-2"]


# ── 上传 / 删除 ──


async def test_upload_document_rejects_unsupported_extension() -> None:
    repo = _repository(datasets=_DATASETS)
    assert await repo.upload_document("ds-1", "image.png", b"x") is None


async def test_upload_document_triggers_parse_and_invalidates_cache() -> None:
    client = FakeClient(datasets=_DATASETS, documents={"ds-1": []})
    repo = RagflowKnowledgeBaseRepository(cast(RagflowClient, client))
    await repo.build_tree("ds-1")  # 先填充缓存
    document = await repo.upload_document("ds-1", "report.pdf", b"pdf-bytes")
    assert document is not None
    assert document.id == "doc-new"
    assert document.is_indexed is True
    assert "trigger_parse" in client.calls
    # 写操作后文档列表缓存应被清掉
    await repo.build_tree("ds-1")
    assert client.calls.count("list_documents:ds-1") == 2


async def test_delete_document_resolves_dataset_from_documents() -> None:
    client = FakeClient(
        datasets=_DATASETS,
        documents={"ds-1": [{"id": "doc-1", "name": "a.pdf"}]},
    )
    repo = RagflowKnowledgeBaseRepository(cast(RagflowClient, client))
    assert await repo.delete_document("doc-1") is True
    assert "delete_documents" in client.calls


async def test_delete_unknown_document_returns_false() -> None:
    repo = _repository(datasets=_DATASETS, documents={"ds-1": [{"id": "doc-1"}]})
    assert await repo.delete_document("doc-404") is False


# ── 检索 ──


async def test_search_maps_hits_to_dto() -> None:
    repo = _repository(datasets=_DATASETS)
    hits = await repo.search(project_id="ds-1", query="事故")
    assert len(hits) == 1
    assert hits[0].document_id == "doc-1"
    assert hits[0].score == 0.9


# ── $ 提及列表 ──


async def test_list_simple_projects_contains_dataset_ids() -> None:
    repo = _repository(datasets=_DATASETS)
    rows = await repo.list_simple_projects()
    assert rows[0] == {"id": "ds-1", "name": "事故库"}
