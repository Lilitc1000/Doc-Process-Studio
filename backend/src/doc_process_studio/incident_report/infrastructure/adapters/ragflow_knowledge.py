"""RAGFlow 检索适配器。

实现 KnowledgeRetrieverPort，对接 RAGFlow `/api/v1/retrieval`。

**凭据是运行期解析的**：本适配器不再在构造时持有 base_url / api_key，而是在每次
``retrieve()`` 时向 ``RagflowConfigProvider`` 要一份当前生效的配置。这样才能做到
"管理员在设置页改完密钥、下一次报告生成就生效"，而不是等重启进程。

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

from ....settings.application.ports import RagflowConfigProvider
from ...application.ports import KnowledgeChunk, KnowledgeRetrieverPort

logger = logging.getLogger(__name__)

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_MIN_CHUNK_CHARACTERS = 40


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
    """解析 ``{"scope": ["dataset_id", ...]}``。

    只接受**数组**值：字符串值会被忽略（这一点由
    ``tests/incident_report/unit/test_ragflow_knowledge.py`` 固化为预期行为）。
    """
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
    """基于 RAGFlow 的知识素材检索实现。

    凭据来源有两条路：

    - **生产装配**只传 ``config_provider``，每次 ``retrieve()`` 时按库里的系统设置解析。
    - 传 ``base_url`` / ``api_key`` 则使用静态凭据（供单元测试与特殊场景直接构造）。
      静态凭据优先于 provider。
    """

    def __init__(
        self,
        *,
        config_provider: RagflowConfigProvider | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout_seconds: float = 15.0,
        similarity_threshold: float = 0.70,
        top_k: int = 3,
        datasets_json: str = "",
        max_chunks_per_document: int = 2,
    ) -> None:
        self._provider = config_provider
        self._static_base_url = (base_url or "").rstrip("/")
        self._static_api_key = api_key or ""
        self._has_static = bool(self._static_base_url and self._static_api_key)
        self._timeout = timeout_seconds
        self._threshold = similarity_threshold
        self._top_k = top_k
        self._datasets = _parse_datasets_json(datasets_json)
        self._max_chunks_per_document = max(1, int(max_chunks_per_document or 1))

    @property
    def enabled(self) -> bool:
        """**仅**反映"静态凭据 + dataset 配置"这一层。

        带 ``config_provider`` 时凭据在运行期才解析，无法同步判断，
        因此这里返回 False 不代表检索不可用 —— 请以 :meth:`retrieve` 的实际返回为准。
        本属性保留是为了兼容既有单元测试与"静态构造"这一用法。
        """
        return bool(self._static_base_url and self._static_api_key and self._datasets)

    async def _resolve_credentials(self) -> tuple[str, str]:
        """解析出 (base_url, api_key)；不可用时返回两个空串。"""
        runtime = await self._resolve_runtime()
        return runtime[0], runtime[1]

    async def _resolve_runtime(
        self,
    ) -> tuple[str, str, dict[str, list[str]], float, int, float, int]:
        """解析出 (base_url, api_key, datasets, threshold, top_k, timeout, max_chunks)。

        dataset 映射与召回参数支持管理员在设置页调整并立即生效：
        provider 解析出的值优先于构造时的快照；库里没配则回落构造时传入的
        快照默认值，保证单测 / 特殊场景的静态构造行为不变。
        """
        fallback_datasets = self._datasets
        fallback_threshold = self._threshold
        fallback_top_k = self._top_k
        fallback_timeout = self._timeout
        fallback_max_chunks = self._max_chunks_per_document

        if self._has_static:
            # 静态凭据（单测 / 特殊场景）优先，参数也一律用构造时快照
            return (
                self._static_base_url,
                self._static_api_key,
                fallback_datasets,
                fallback_threshold,
                fallback_top_k,
                fallback_timeout,
                fallback_max_chunks,
            )
        if self._provider is None:
            return "", "", fallback_datasets, fallback_threshold, fallback_top_k, fallback_timeout, fallback_max_chunks

        config = await self._provider.resolve(scope="system")
        if not config.enabled or not config.base_url or not config.api_key:
            return "", "", fallback_datasets, fallback_threshold, fallback_top_k, fallback_timeout, fallback_max_chunks

        datasets = _parse_datasets_json(config.datasets_json) or fallback_datasets
        # RagflowConfig 上的类型已经收窄为 float | None / int | None，这里只做"未配置则回落"
        threshold = config.similarity_threshold if config.similarity_threshold is not None else fallback_threshold
        top_k = config.top_k if config.top_k is not None else fallback_top_k
        timeout = config.timeout_seconds if config.timeout_seconds is not None else fallback_timeout
        max_chunks = (
            config.max_chunks_per_document if config.max_chunks_per_document is not None else fallback_max_chunks
        )
        return config.base_url, config.api_key, datasets, threshold, top_k, timeout, max_chunks

    async def retrieve(
        self,
        *,
        query: str,
        scope: str,
        top_k: int,
    ) -> list[KnowledgeChunk]:
        base_url, api_key, datasets, threshold, configured_top_k, timeout, max_chunks = await self._resolve_runtime()
        if not base_url or not api_key:
            logger.debug("RAGFlow retriever unavailable (no usable credentials), skip retrieval")
            return []

        dataset_ids = datasets.get(scope, [])
        if not dataset_ids:
            logger.debug("No RAGFlow dataset configured for scope=%s", scope)
            return []

        requested = max(1, top_k or configured_top_k)
        payload = {
            "question": query,
            "dataset_ids": dataset_ids,
            "page": 1,
            "page_size": requested,
            "similarity_threshold": threshold,
            "vector_similarity_weight": 1.0,
            "top_k": requested * 4,
        }
        headers = {"Authorization": f"Bearer {api_key}"}
        url = f"{base_url}/api/v1/retrieval"

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(timeout)) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                body = resp.json()
        except Exception as exc:  # noqa: BLE001 - 远端不可用时降级，不阻断报告生成
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
        per_document_counts: dict[str, int] = {}
        for item in raw_chunks:
            if not isinstance(item, dict):
                continue
            content = _strip_html(str(item.get("content", "")))
            if len(content) < _MIN_CHUNK_CHARACTERS:
                continue
            doc_id = str(item.get("document_id", ""))
            # 同一文档最多保留 N 个片段。
            # 原实现按 document_id 整体去重，导致单文档语料时每次只注入 1 个片段，
            # top_k 形同虚设；语料铺开后更会让召回内容被头部文档独占。
            if doc_id:
                used = per_document_counts.get(doc_id, 0)
                if used >= max_chunks:
                    continue
                per_document_counts[doc_id] = used + 1
            try:
                score = float(item.get("similarity", 0.0))
            except (TypeError, ValueError):
                score = 0.0
            if score < threshold:
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
