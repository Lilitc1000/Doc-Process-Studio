"""RAGFlow 检索适配器。

实现 KnowledgeRetrieverPort，对接 RAGFlow `/api/v1/retrieval`。

约束（来自项目交接实测，务必遵守，别凭直觉改）：
- 未启用 / 未配置 / 无对应 dataset → 返回 []
- 超时 15s，任何异常 → 记日志 + 返回 []，绝不阻断报告生成
- `page_size` = 请求的条数；`top_k` = 条数 × 4（召回深度）；`vector_similarity_weight` = 1.0
- `similarity_threshold` 用配置值
- 不要传 `cross_languages`（会触发 LLM 翻译，5~13s 且不确定）
- 响应必须校验 `code`，`code != 0` 视为失败
- `data` 可能是对象（`{"chunks": [...], "doc_aggs": [...], "total": N}`）也可能是数组，两种都要兼容

后处理：
- strip HTML（chunk 里可能有 <table><tr><td>）
- 丢弃清洗后 <40 字符的碎片块
- 按 document_id 去重
- 相似度 < 配置阈值丢弃
"""

from __future__ import annotations

import json
import logging
import re

import httpx

from ...application.ports import KnowledgeChunk, KnowledgeRetrieverPort

logger = logging.getLogger(__name__)

_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return _HTML_TAG_RE.sub("", text or "").strip()


def _extract_chunks(body: dict) -> list[dict]:
    """从 `/api/v1/retrieval` 响应中取出片段列表。

    实测（2026-09-16）：``data`` 是**对象**而非数组——
    ``{"code": 0, "data": {"chunks": [...], "doc_aggs": [...], "total": N}}``。
    按数组解析时会遍历到三个字符串键，全部被过滤掉，导致检索永远返回 0 条。
    这里两种形状都兼容。
    """
    data = body.get("data")
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        chunks = data.get("chunks")
        if isinstance(chunks, list):
            return [item for item in chunks if isinstance(item, dict)]
    return []


def _parse_datasets_json(raw: str | None) -> dict[str, list[str]]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        logger.warning("Invalid ragflow_datasets_json, ignored: %r", raw)
        return {}
    if not isinstance(data, dict):
        return {}
    result: dict[str, list[str]] = {}
    for scope, ids in data.items():
        if isinstance(ids, list):
            result[str(scope)] = [str(i) for i in ids if i]
    return result


class RagflowKnowledgeRetriever(KnowledgeRetrieverPort):
    """基于 RAGFlow 的知识素材检索实现。"""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout_seconds: float = 15.0,
        similarity_threshold: float = 0.70,
        top_k: int = 3,
        datasets_json: str = "",
    ) -> None:
        self._base_url = (base_url or "").rstrip("/")
        self._api_key = api_key or ""
        self._timeout = timeout_seconds
        self._threshold = similarity_threshold
        self._top_k = top_k
        self._datasets = _parse_datasets_json(datasets_json)

    @property
    def enabled(self) -> bool:
        """是否已配置可用的检索后端。"""
        return bool(self._base_url and self._api_key and self._datasets)

    async def retrieve(
        self,
        *,
        query: str,
        scope: str,
        top_k: int,
    ) -> list[KnowledgeChunk]:
        if not self.enabled:
            logger.debug("RAGFlow retriever disabled or unconfigured, skip retrieval")
            return []
        dataset_ids = self._datasets.get(scope, [])
        if not dataset_ids:
            logger.debug("No RAGFlow dataset configured for scope=%s", scope)
            return []

        requested = max(1, top_k)
        payload = {
            "question": query,
            "dataset_ids": dataset_ids,
            "page": 1,
            "page_size": requested,
            "similarity_threshold": self._threshold,
            "vector_similarity_weight": 1.0,
            "top_k": requested * 4,
        }
        headers = {"Authorization": f"Bearer {self._api_key}"}
        url = f"{self._base_url}/api/v1/retrieval"

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(self._timeout)) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                body = resp.json()
        except Exception as exc:
            logger.warning("RAGFlow retrieval failed (scope=%s): %s", scope, exc)
            return []

        if not isinstance(body, dict):
            logger.warning("RAGFlow retrieval returned unexpected body type")
            return []
        if body.get("code", -1) != 0:
            logger.warning(
                "RAGFlow retrieval returned code=%s message=%s",
                body.get("code"),
                body.get("message"),
            )
            return []

        raw_chunks = _extract_chunks(body)
        chunks: list[KnowledgeChunk] = []
        seen_doc_ids: set[str] = set()
        for item in raw_chunks:
            if not isinstance(item, dict):
                continue
            content = _strip_html(str(item.get("content", "")))
            if len(content) < 40:
                continue
            doc_id = str(item.get("document_id", ""))
            if doc_id and doc_id in seen_doc_ids:
                continue
            if doc_id:
                seen_doc_ids.add(doc_id)
            try:
                score = float(item.get("similarity", 0.0))
            except (TypeError, ValueError):
                score = 0.0
            if score < self._threshold:
                continue
            source = str(item.get("document_keyword") or doc_id or "unknown")
            chunks.append(
                KnowledgeChunk(
                    content=content,
                    scope=scope,
                    source=source,
                    document_id=doc_id,
                    score=score,
                )
            )
        return chunks
