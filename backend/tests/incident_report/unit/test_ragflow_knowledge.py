"""RAGFlow 检索适配器单元测试。

重点覆盖：未配置降级、后处理（HTML 清洗 / 碎片过滤 / 去重 / 阈值）、异常与 code!=0 降级。
不依赖真实 RAGFlow 服务，httpx.AsyncClient 通过 monkeypatch 模拟。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from doc_process_studio.incident_report.infrastructure.adapters.ragflow_knowledge import (
    RagflowKnowledgeRetriever,
    _parse_datasets_json,
    _strip_html,
)


def test_strip_html_removes_tags() -> None:
    assert _strip_html("<table><tr><td>hello</td></tr></table>") == "hello"
    assert _strip_html("plain text") == "plain text"
    assert _strip_html("") == ""


def test_parse_datasets_json_variants() -> None:
    assert _parse_datasets_json("") == {}
    assert _parse_datasets_json("not-json") == {}
    assert _parse_datasets_json('{"history":["a","b"]}') == {"history": ["a", "b"]}
    # 非 dict / 非 list 值被忽略
    assert _parse_datasets_json('{"history":"a"}') == {}


async def test_unconfigured_retriever_disabled() -> None:
    r = RagflowKnowledgeRetriever()
    assert r.enabled is False
    assert await r.retrieve(query="x", scope="history", top_k=3) == []


def test_enabled_requires_base_url_api_key_and_datasets() -> None:
    assert RagflowKnowledgeRetriever(base_url="http://x", api_key="k").enabled is False
    assert (
        RagflowKnowledgeRetriever(base_url="http://x", api_key="k", datasets_json='{"history":["d1"]}').enabled is True
    )


def _make_retriever(datasets_json: str = '{"history":["d1"]}') -> RagflowKnowledgeRetriever:
    return RagflowKnowledgeRetriever(
        base_url="http://ragflow.test",
        api_key="secret",
        datasets_json=datasets_json,
        similarity_threshold=0.5,
        top_k=2,
    )


def _fake_client_with_response(payload: dict) -> AsyncMock:
    resp = MagicMock()
    resp.json.return_value = payload
    resp.raise_for_status = MagicMock()
    client = AsyncMock()
    client.post = AsyncMock(return_value=resp)
    client.__aenter__.return_value = client
    client.__aexit__.return_value = False
    return client


async def test_retrieve_parses_and_filters(monkeypatch: pytest.MonkeyPatch) -> None:
    retriever = _make_retriever()
    payload = {
        "code": 0,
        "data": [
            {
                "content": "<table><tr><td>NAS2 shutdown at 20:35 due to I/O overload</td></tr></table>",
                "document_id": "d1",
                "document_keyword": "report.md",
                "similarity": 0.9,
            },
            {"content": "tiny", "document_id": "d2", "similarity": 0.8},
            {"content": "another long chunk from same doc", "document_id": "d1", "similarity": 0.85},
            {"content": "low score chunk content here", "document_id": "d3", "similarity": 0.1},
        ],
    }
    client = _fake_client_with_response(payload)
    monkeypatch.setattr(httpx, "AsyncClient", lambda *_a, **_k: client)

    chunks = await retriever.retrieve(query="incident NAS failure", scope="history", top_k=2)

    # tiny(<40) 丢弃；d1 去重保留首条；d3 (0.1<0.5) 丢弃
    assert len(chunks) == 1
    assert chunks[0].document_id == "d1"
    assert "table" not in chunks[0].content
    assert chunks[0].score == 0.9
    assert chunks[0].source == "report.md"


async def test_retrieve_supports_object_shaped_data(monkeypatch: pytest.MonkeyPatch) -> None:
    """服务端实际返回 data 为对象：{"chunks": [...], "doc_aggs": [...], "total": N}。

    按数组解析时遍历到的是三个字符串键，会被全部过滤，导致检索永远 0 条。
    """
    retriever = _make_retriever()
    payload = {
        "code": 0,
        "data": {
            "chunks": [
                {
                    "content": "CHT: toll point site identifier; NAS1 and NAS2 form an HA storage cluster.",
                    "document_id": "d1",
                    "document_keyword": "DAS2-015.md",
                    "similarity": 0.7087406,
                }
            ],
            "doc_aggs": [],
            "total": 1,
        },
    }
    client = _fake_client_with_response(payload)
    monkeypatch.setattr(httpx, "AsyncClient", lambda *_a, **_k: client)

    chunks = await retriever.retrieve(query="impact section", scope="history", top_k=2)

    assert len(chunks) == 1
    assert chunks[0].document_id == "d1"
    assert chunks[0].score == 0.7087406


async def test_retrieve_code_not_zero_returns_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    retriever = _make_retriever()
    client = _fake_client_with_response({"code": 102, "message": "permission"})
    monkeypatch.setattr(httpx, "AsyncClient", lambda *_a, **_k: client)

    chunks = await retriever.retrieve(query="x", scope="history", top_k=2)
    assert chunks == []


async def test_retrieve_http_error_returns_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    retriever = _make_retriever()
    client = AsyncMock()
    client.post = AsyncMock(side_effect=httpx.ConnectError("boom"))
    client.__aenter__.return_value = client
    client.__aexit__.return_value = False
    monkeypatch.setattr(httpx, "AsyncClient", lambda *_a, **_k: client)

    chunks = await retriever.retrieve(query="x", scope="history", top_k=2)
    assert chunks == []


async def test_retrieve_unknown_scope_returns_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    retriever = _make_retriever()
    client = _fake_client_with_response({"code": 0, "data": []})
    monkeypatch.setattr(httpx, "AsyncClient", lambda *_a, **_k: client)

    chunks = await retriever.retrieve(query="x", scope="specs", top_k=2)
    assert chunks == []
    # specs 无配置 -> 不应发起请求
    client.post.assert_not_called()
