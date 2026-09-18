"""RAGFlow HTTP 客户端——知识库所有读写的唯一出口。

对接的接口（与本项目 ``6999`` 之外的 RAGFlow 服务端约定）：

| 能力 | 方法 + 路径 |
|---|---|
| 列出 / 新建 / 改名 / 删除 dataset | ``GET|POST|PUT|DELETE /api/v1/datasets`` |
| 列出 dataset 内的文件夹 | ``GET /api/v1/datasets/{id}/documents/folders`` |
| 列出 / 上传 / 删除 dataset 内的文档 | ``GET|POST|DELETE /api/v1/datasets/{id}/documents`` |
| 触发解析 | ``POST /api/v1/datasets/{id}/chunks`` |
| 检索 | ``POST /api/v1/retrieval`` |

实测纪律（别凭直觉改）：
- ``code != 0`` 一律视为失败，返回空容器 / ``False``，**绝不抛异常**阻断调用方；
- ``folders`` 端点在 dataset **没有**文件夹时返回 ``code=102 "The dataset not own the
  document folders."``——这不是错误，应翻译成"空列表"（数据集文档是平铺的）；
- ``/api/v1/retrieval`` 的 ``data`` 是**对象**而非数组：``{"chunks": [...], "total": N}``，
  旧代码按数组解析过，导致检索永远 0 条，这里两种形状都兼容；
- 不要传 ``cross_languages``（会触发 LLM 翻译，实测 5~13s 且不确定）；
- 检索后处理：strip HTML → 丢弃过短碎片 → 按文档去重 → 过滤低于阈值的片段。
"""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_MIN_CHUNK_CHARACTERS = 40
# RAGFlow 用它表示"dataset 内没有文件夹"，本项目翻译为空列表（文档平铺）
_NO_FOLDERS_CODE = 102
_DEFAULT_PAGE_SIZE = 100


def _strip_html(text: str) -> str:
    return _HTML_TAG_RE.sub("", text or "").strip()


def extract_chunks(body: dict[str, Any]) -> list[dict[str, Any]]:
    """从 `/api/v1/retrieval` 响应中取出片段列表，兼容 ``data`` 为对象 / 数组两种形状。"""
    data = body.get("data")
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        chunks = data.get("chunks")
        if isinstance(chunks, list):
            return [item for item in chunks if isinstance(item, dict)]
    return []


class RagflowClient:
    """RAGFlow HTTP 客户端。

    所有方法在"未配置 / 网络异常 / 业务失败"时都返回安全值（空列表 / ``None`` / ``False``），
    由上层决定降级方式；只有调用方的参数错误才会显式抛出。
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout_seconds: float = 15.0,
        parse_timeout_seconds: float = 60.0,
        similarity_threshold: float = 0.55,
        top_k: int = 6,
        page_size: int = _DEFAULT_PAGE_SIZE,
    ) -> None:
        self._base_url = (base_url or "").rstrip("/")
        self._api_key = api_key or ""
        self._timeout = timeout_seconds
        self._parse_timeout = parse_timeout_seconds
        self._threshold = similarity_threshold
        self._top_k = top_k
        self._page_size = page_size

    @property
    def enabled(self) -> bool:
        return bool(self._base_url and self._api_key)

    # ------------------------------------------------------------------ 内部工具

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}"}

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        files: Any = None,
        params: dict[str, Any] | None = None,
        timeout_seconds: float | None = None,
    ) -> dict[str, Any] | None:
        """发出请求并返回响应体；任何失败都返回 ``None`` 并记日志。"""
        if not self.enabled:
            logger.warning("RAGFlow request skipped: base_url/api_key not configured")
            return None

        url = f"{self._base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(timeout_seconds or self._timeout)) as client:
                resp = await client.request(
                    method,
                    url,
                    headers=self._headers(),
                    json=json_body,
                    files=files,
                    params=params,
                )
                resp.raise_for_status()
                body = resp.json()
        except Exception as exc:  # noqa: BLE001 - 远端不可用时降级，不阻断调用方
            logger.warning("RAGFlow %s %s failed: %s", method, path, exc)
            return None

        if not isinstance(body, dict):
            logger.warning("RAGFlow %s %s returned non-object body", method, path)
            return None
        return body

    @staticmethod
    def _items(body: dict[str, Any] | None, *keys: str) -> list[dict[str, Any]]:
        """取出列表型载荷，兼容 ``data`` 为对象或数组。

        不同端点把列表放在不同的键下（``docs`` / ``datasets`` / ``folders``），
        这里按给定候选键依次尝试，取不到就当空列表——宁可少读也不误判为错误。
        """
        if body is None or body.get("code", -1) != 0:
            return []
        data = body.get("data")
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        if isinstance(data, dict):
            for key in keys:
                items = data.get(key)
                if isinstance(items, list):
                    return [item for item in items if isinstance(item, dict)]
        return []

    # ------------------------------------------------------------------ dataset（项目）

    async def list_datasets(self) -> list[dict[str, Any]]:
        body = await self._request(
            "GET",
            "/api/v1/datasets",
            params={"page": 1, "page_size": self._page_size},
        )
        return self._items(body, "datasets", "kbs", "docs")

    async def probe_connection(self) -> tuple[bool, str, int]:
        """连通性自检：返回 ``(是否可用, 说明, 可访问 dataset 数量)``。

        与读路径一样坚持"不抛异常"：任何失败都翻译成 ``(False, 原因, 0)``，
        方便设置页的"测试连接"直接展示具体原因（401 / DNS / 超时各自不同）。
        """
        if not self.enabled:
            return False, "未配置 base_url 或 api_key", 0

        body = await self._request(
            "GET",
            "/api/v1/datasets",
            params={"page": 1, "page_size": self._page_size},
        )
        if body is None:
            return False, "无法连接 RAGFlow（网络不通或地址错误），详见服务端日志", 0

        code = body.get("code", -1)
        if code != 0:
            message = str(body.get("message") or "无附加消息")
            return False, f"RAGFlow 返回 code={code}：{message}", 0

        items = self._items(body, "datasets", "kbs", "docs")
        return True, f"连接成功，可访问 {len(items)} 个知识库", len(items)

    async def get_dataset(self, dataset_id: str) -> dict[str, Any] | None:
        body = await self._request("GET", f"/api/v1/datasets/{dataset_id}")
        return body.get("data") if isinstance(body, dict) and body.get("code", -1) == 0 else None

    async def create_dataset(self, name: str, description: str = "") -> dict[str, Any] | None:
        payload: dict[str, Any] = {"name": name}
        if description:
            payload["description"] = description
        body = await self._request("POST", "/api/v1/datasets", json_body=payload)
        return body.get("data") if isinstance(body, dict) and body.get("code", -1) == 0 else None

    async def update_dataset(self, dataset_id: str, new_name: str) -> dict[str, Any] | None:
        body = await self._request(
            "PUT",
            f"/api/v1/datasets/{dataset_id}",
            json_body={"name": new_name},
        )
        return body.get("data") if isinstance(body, dict) and body.get("code", -1) == 0 else None

    async def delete_dataset(self, dataset_id: str) -> bool:
        body = await self._request("DELETE", "/api/v1/datasets", json_body={"ids": [dataset_id]})
        if body is None or body.get("code", -1) != 0:
            logger.warning("RAGFlow dataset delete failed: %s", body.get("message") if body else "unreachable")
            return False
        return True

    # ------------------------------------------------------------------ 文件夹 / 文档

    async def list_folders(self, dataset_id: str) -> list[dict[str, Any]]:
        """列出 dataset 内的文件夹；``102``（无文件夹）按空列表处理。"""
        body = await self._request("GET", f"/api/v1/datasets/{dataset_id}/documents/folders")
        if body is None:
            return []
        if body.get("code", -1) == _NO_FOLDERS_CODE:
            return []
        return self._items(body, "folders")

    async def list_documents(self, dataset_id: str) -> list[dict[str, Any]]:
        body = await self._request(
            "GET",
            f"/api/v1/datasets/{dataset_id}/documents",
            params={"page": 1, "page_size": self._page_size},
        )
        return self._items(body, "docs")

    async def get_document(self, dataset_id: str, document_id: str) -> dict[str, Any] | None:
        body = await self._request(
            "GET",
            f"/api/v1/datasets/{dataset_id}/documents",
            params={"id": document_id},
        )
        docs = self._items(body, "docs")
        return docs[0] if docs else None

    async def upload_document(self, dataset_id: str, file_name: str, file_bytes: bytes) -> dict[str, Any] | None:
        """上传文档并返回 RAGFlow 侧文档对象；失败返回 ``None``。"""
        body = await self._request(
            "POST",
            f"/api/v1/datasets/{dataset_id}/documents",
            files={"file": (file_name or "upload.bin", file_bytes)},
        )
        uploaded = self._items(body, "docs", "documents")
        return uploaded[0] if uploaded else None

    async def trigger_parse(self, dataset_id: str, document_ids: list[str]) -> bool:
        body = await self._request(
            "POST",
            f"/api/v1/datasets/{dataset_id}/chunks",
            json_body={"document_ids": document_ids},
            timeout_seconds=self._parse_timeout,
        )
        if body is None or body.get("code", -1) != 0:
            logger.warning(
                "RAGFlow parse trigger failed (docs=%s): %s",
                document_ids,
                body.get("message") if body else "unreachable",
            )
            return False
        return True

    async def delete_documents(self, dataset_id: str, document_ids: list[str]) -> bool:
        body = await self._request(
            "DELETE",
            f"/api/v1/datasets/{dataset_id}/documents",
            json_body={"ids": document_ids},
        )
        if body is None or body.get("code", -1) != 0:
            logger.warning(
                "RAGFlow document delete failed (docs=%s): %s",
                document_ids,
                body.get("message") if body else "unreachable",
            )
            return False
        return True

    # ------------------------------------------------------------------ 检索

    async def retrieve_chunks(
        self,
        dataset_ids: list[str],
        query: str,
        top_k: int | None = None,
    ) -> list[dict[str, Any]]:
        if not self.enabled or not query.strip() or not dataset_ids:
            return []

        requested = max(1, int(top_k or self._top_k))
        body = await self._request(
            "POST",
            "/api/v1/retrieval",
            json_body={
                "question": query,
                "dataset_ids": dataset_ids,
                "page": 1,
                "page_size": requested,
                "similarity_threshold": self._threshold,
                "vector_similarity_weight": 1.0,
                "top_k": requested * 4,
            },
        )
        if body is None or body.get("code", -1) != 0:
            logger.warning(
                "RAGFlow retrieval failed (datasets=%s): %s",
                dataset_ids,
                body.get("message") if body else "unreachable",
            )
            return []
        return self._filter_chunks(extract_chunks(body))

    def _filter_chunks(self, raw_chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        filtered: list[dict[str, Any]] = []
        seen_doc_ids: set[str] = set()
        for item in raw_chunks:
            content = _strip_html(str(item.get("content", "")))
            if len(content) < _MIN_CHUNK_CHARACTERS:
                continue
            doc_id = str(item.get("document_id", "") or "")
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
            source = str(item.get("document_keyword") or doc_id or "未知文档")
            filtered.append(
                {
                    "content": content,
                    "score": score,
                    "document_id": doc_id,
                    "source": source,
                    "file_name": source,
                }
            )
        return filtered
