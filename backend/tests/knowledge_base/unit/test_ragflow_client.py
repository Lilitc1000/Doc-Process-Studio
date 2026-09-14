"""RAGFlow 客户端单元测试。

全部用例用 monkeypatch 替换 ``_request``，不发起真实网络请求。
"""

from __future__ import annotations

from typing import Any

import pytest

from doc_process_studio.knowledge_base.infrastructure.ragflow_client import (
    RagflowClient,
    extract_chunks,
)


@pytest.fixture()
def client() -> RagflowClient:
    return RagflowClient(base_url="http://ragflow.test", api_key="ragflow-key-xxx")


def _install(
    client: RagflowClient,
    monkeypatch: pytest.MonkeyPatch,
    body: Any,
) -> list[tuple[str, str, dict[str, Any]]]:
    calls: list[tuple[str, str, dict[str, Any]]] = []

    async def fake_request(method: str, path: str, **kwargs: Any) -> Any:
        calls.append((method, path, kwargs))
        return body(method, path, kwargs) if callable(body) else body

    monkeypatch.setattr(client, "_request", fake_request)
    return calls


# ── 未配置时的降级 ──


async def test_disabled_client_reads_return_empty() -> None:
    disabled = RagflowClient(base_url="", api_key="")
    assert disabled.enabled is False
    assert await disabled.list_datasets() == []
    assert await disabled.list_folders("ds-1") == []
    assert await disabled.list_documents("ds-1") == []
    assert await disabled.retrieve_chunks(["ds-1"], "anything") == []
    assert await disabled.upload_document("ds-1", "a.pdf", b"x") is None


# ── 响应解析 ──


def test_extract_chunks_supports_object_and_array_payload() -> None:
    assert len(extract_chunks({"data": {"chunks": [{"content": "a" * 60}]}})) == 1
    assert len(extract_chunks({"data": [{"content": "b"}]})) == 1
    assert extract_chunks({"data": {"total": 0}}) == []
    assert extract_chunks({"data": None}) == []


async def test_list_datasets_reads_list_payload(client: RagflowClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _install(client, monkeypatch, {"code": 0, "data": [{"id": "ds-1", "name": "事故库"}]})
    datasets = await client.list_datasets()
    assert [item["id"] for item in datasets] == ["ds-1"]


async def test_list_folders_treats_102_as_empty(client: RagflowClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _install(client, monkeypatch, {"code": 102, "message": "The dataset not own the document folders."})
    assert await client.list_folders("ds-1") == []


async def test_list_folders_reads_folders(client: RagflowClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _install(client, monkeypatch, {"code": 0, "data": {"folders": [{"id": "f-1", "name": "子目录"}]}})
    folders = await client.list_folders("ds-1")
    assert folders[0]["name"] == "子目录"


async def test_upload_document_returns_first_item(client: RagflowClient, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _install(client, monkeypatch, {"code": 0, "data": [{"id": "doc-1", "name": "a.pdf"}]})
    uploaded = await client.upload_document("ds-1", "a.pdf", b"bytes")
    assert uploaded is not None and uploaded["id"] == "doc-1"
    assert calls[0][0] == "POST"
    assert calls[0][1] == "/api/v1/datasets/ds-1/documents"


async def test_trigger_parse_posts_document_ids(client: RagflowClient, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _install(client, monkeypatch, {"code": 0})
    assert await client.trigger_parse("ds-1", ["doc-1"]) is True
    assert calls[0][2]["json_body"] == {"document_ids": ["doc-1"]}


async def test_delete_documents_failure_is_safe(client: RagflowClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _install(client, monkeypatch, {"code": 102, "message": "You don't own the dataset"})
    assert await client.delete_documents("ds-1", ["doc-1"]) is False


async def test_delete_dataset_builds_ids_payload(client: RagflowClient, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _install(client, monkeypatch, {"code": 0})
    assert await client.delete_dataset("ds-1") is True
    assert calls[0][0] == "DELETE"
    assert calls[0][2]["json_body"] == {"ids": ["ds-1"]}


# ── 检索后处理 ──


async def test_retrieve_filters_short_duplicate_and_low_score(
    client: RagflowClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = {
        "code": 0,
        "data": {
            "chunks": [
                {
                    "content": "<p>这是一段足够长的检索内容片段，需要超过四十个字符才不会被丢弃。</p>",
                    "similarity": 0.9,
                    "document_id": "doc-1",
                },
                {"content": "太短", "similarity": 0.9, "document_id": "doc-1"},
                {
                    "content": "同一文档的第二个片段应该被去重规则去掉，篇幅同样是足够的，这里也补上一些说明文字。",
                    "similarity": 0.8,
                    "document_id": "doc-1",
                },
                {
                    "content": "低于相似度阈值的片段应该被过滤掉，篇幅同样是足够的，这里也补上一些说明文字。",
                    "similarity": 0.1,
                    "document_id": "doc-2",
                },
            ]
        },
    }
    _install(client, monkeypatch, payload)
    chunks = await client.retrieve_chunks(["ds-1"], "查询")
    assert len(chunks) == 1
    assert chunks[0]["document_id"] == "doc-1"
    assert "<p>" not in chunks[0]["content"]


async def test_retrieve_skips_empty_query(client: RagflowClient, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _install(client, monkeypatch, {"code": 0, "data": {"chunks": []}})
    assert await client.retrieve_chunks(["ds-1"], "   ") == []
    assert calls == []
