"""RAGFlow 版知识库仓储——把 RAGFlow 的数据模型翻译成应用契约。

映射关系（全量以 RAGFlow 为真相源）：

| 应用侧 | RAGFlow |
|---|---|
| 项目（``KBProject``） | dataset |
| 文件夹（``KBTreeNodeFolder``） | dataset 内的 folder |
| 文档（``KBDocument``） | dataset 内的 document |

要点：
- **文件夹只读**：本实例的 dataset 接口不支持新建 / 删除文件夹，因此本仓储只提供
  读：无 folder 时返回扁平文档列表，有 folder 时返回层级树。将来 RAGFlow 支持了
  或用户在网页端建了文件夹，这里无需改代码即可显示树。
- **缓存（默认关闭）**：RAGFlow 是外部真相源，用户在 RAGFlow 网页端的增删我们
  收不到通知，因此 **dataset 列表永不缓存**，保证"有哪些项目"始终与 RAGFlow 一致；
  folder / document 列表可按 ``kb_cache_ttl_seconds`` 缓存（``<=0`` 表示不缓存，默认 0）。
  任何写操作成功后立即失效对应键；Redis 不可用时自动降级为直连 RAGFlow。
- **读路径不抛异常**：未配置 / 网络失败 / 资源不存在一律返回空容器。
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from functools import partial
from typing import Any

from ...common.infrastructure.cache import build_cache_key, delete_key, get_json, set_json
from ..application.dtos import (
    KBDocument,
    KBIndexHit,
    KBProject,
    KBTreeNode,
    KBTreeNodeDocument,
    KBTreeNodeFolder,
)
from ..application.ports import KnowledgeBaseRepository
from .parser import extract_archive
from .parsing import detect_file_type, is_archive
from .ragflow_client import RagflowClient

logger = logging.getLogger(__name__)

_DEFAULT_CACHE_TTL_SECONDS = 300


def _timestamp(value: Any) -> datetime:
    """把 RAGFlow 的毫秒时间戳转成 datetime；缺失或非法时回落到当前时间。"""
    if isinstance(value, (int, float)) and value > 0:
        return datetime.fromtimestamp(value / 1000, tz=UTC)
    return datetime.now(UTC)


def _datasets_key() -> str:
    return build_cache_key("kb", "datasets")


def _folders_key(dataset_id: str) -> str:
    return build_cache_key("kb", "ds", dataset_id, "folders")


def _documents_key(dataset_id: str) -> str:
    return build_cache_key("kb", "ds", dataset_id, "documents")


class RagflowKnowledgeBaseRepository(KnowledgeBaseRepository):
    """知识库仓储：结构、文档与检索全部走 RAGFlow。"""

    def __init__(
        self,
        client: RagflowClient,
        *,
        cache_ttl_seconds: int = _DEFAULT_CACHE_TTL_SECONDS,
    ) -> None:
        self._client = client
        self._cache_ttl = cache_ttl_seconds

    # ------------------------------------------------------------------ 缓存辅助

    async def _read_cache(self, key: str) -> list[dict[str, Any]] | None:
        try:
            payload = await get_json(key)
        except Exception as exc:  # noqa: BLE001 - Redis 不可用时降级为直连
            logger.debug("KB cache read failed (key=%s): %s", key, exc)
            return None
        return payload if isinstance(payload, list) else None

    async def _write_cache(self, key: str, payload: list[dict[str, Any]]) -> None:
        try:
            await set_json(key, payload, ttl_seconds=self._cache_ttl)
        except Exception as exc:  # noqa: BLE001 - 写缓存失败不影响主流程
            logger.debug("KB cache write failed (key=%s): %s", key, exc)

    async def _drop_cache(self, *keys: str) -> None:
        for key in keys:
            try:
                await delete_key(key)
            except Exception as exc:  # noqa: BLE001
                logger.debug("KB cache invalidate failed (key=%s): %s", key, exc)

    async def _cached_list(
        self,
        key: str,
        loader: Callable[[], Awaitable[list[dict[str, Any]]]],
    ) -> list[dict[str, Any]]:
        if self._cache_ttl <= 0:
            return list(await loader())
        cached = await self._read_cache(key)
        if cached is not None:
            return cached
        payload: list[dict[str, Any]] = list(await loader())
        await self._write_cache(key, payload)
        return payload

    async def _datasets(self) -> list[dict[str, Any]]:
        """dataset 列表（= 项目清单）。

        RAGFlow 侧的增删（用户在网页端建/删 dataset）不会通知本服务，缓存会让
        "有哪些项目"与真相源脱节，因此这里**永不缓存**，每次都直连 RAGFlow。
        """
        return await self._client.list_datasets()

    # ------------------------------------------------------------------ 结构映射

    @staticmethod
    def _project_from_dataset(dataset: dict[str, Any]) -> KBProject:
        return KBProject(
            id=str(dataset.get("id", "") or ""),
            name=str(dataset.get("name", "") or ""),
            description=dataset.get("description") or None,
            document_count=int(dataset.get("document_count", 0) or 0),
            created_at=_timestamp(dataset.get("create_time")),
            updated_at=_timestamp(dataset.get("update_time")),
        )

    @staticmethod
    def _document_from_payload(dataset_id: str, document: dict[str, Any]) -> KBDocument:
        file_name = str(document.get("name", "") or "")
        chunk_count = int(document.get("chunk_count", 0) or 0)
        return KBDocument(
            id=str(document.get("id", "") or ""),
            project_id=dataset_id,
            file_name=file_name,
            file_type=detect_file_type(file_name) or "other",
            file_size=int(document.get("size", 0) or 0),
            chunk_count=chunk_count,
            is_indexed=chunk_count > 0,
            uploaded_at=_timestamp(document.get("create_time")),
        )

    @staticmethod
    def _document_node(document: dict[str, Any]) -> KBTreeNodeDocument:
        file_name = str(document.get("name", "") or "")
        chunk_count = int(document.get("chunk_count", 0) or 0)
        return KBTreeNodeDocument(
            id=str(document.get("id", "") or ""),
            name=file_name,
            file_type=detect_file_type(file_name) or "other",
            file_size=int(document.get("size", 0) or 0),
            chunk_count=chunk_count,
            is_indexed=chunk_count > 0,
            uploaded_at=_timestamp(document.get("create_time")),
        )

    @staticmethod
    def _build_tree_nodes(
        folders: list[dict[str, Any]],
        documents: list[dict[str, Any]],
    ) -> list[KBTreeNode]:
        """把 folder + document 组装成树。

        dataset 文档若不与任何 folder 关联（本版本 RAGFlow 的行为），则挂在根节点下，
        与"扁平列表"时的表现一致。
        """
        folder_nodes: dict[str, KBTreeNodeFolder] = {
            str(folder.get("id", "") or ""): KBTreeNodeFolder(
                id=str(folder.get("id", "") or ""),
                name=str(folder.get("name", "") or ""),
                children=[],
            )
            for folder in folders
        }

        root_children: list[KBTreeNode] = []
        attached_folder_ids: set[str] = set()

        for folder in folders:
            node = folder_nodes[str(folder.get("id", "") or "")]
            parent_id = folder.get("parent_id") or folder.get("parentId")
            if parent_id and str(parent_id) in folder_nodes and str(parent_id) != node.id:
                folder_nodes[str(parent_id)].children.append(node)
                attached_folder_ids.add(node.id)
            else:
                root_children.append(node)

        for document in documents:
            document_node: KBTreeNode = RagflowKnowledgeBaseRepository._document_node(document)
            parent_id = document.get("parent_id") or document.get("parentId")
            target = folder_nodes.get(str(parent_id)) if parent_id else None
            if target is not None:
                target.children.append(document_node)
            else:
                root_children.append(document_node)

        return root_children

    # ------------------------------------------------------------------ 端口实现

    async def list_projects(self) -> list[KBProject]:
        datasets = await self._datasets()
        return [self._project_from_dataset(dataset) for dataset in datasets if dataset.get("id")]

    async def get_project(self, project_id: str) -> KBProject | None:
        dataset = await self._client.get_dataset(project_id)
        if not dataset:
            return None
        return self._project_from_dataset(dataset)

    async def create_project(self, name: str, description: str = "") -> KBProject:
        created = await self._client.create_dataset(name, description)
        await self._drop_cache(_datasets_key())
        return self._project_from_dataset(created or {"name": name, "description": description or None})

    async def rename_project(self, project_id: str, new_name: str) -> KBProject | None:
        updated = await self._client.update_dataset(project_id, new_name)
        await self._drop_cache(_datasets_key())
        return self._project_from_dataset(updated) if updated else None

    async def delete_project(self, project_id: str) -> bool:
        deleted = await self._client.delete_dataset(project_id)
        if deleted:
            await self._drop_cache(_datasets_key(), _folders_key(project_id), _documents_key(project_id))
        return deleted

    async def list_simple_projects(self) -> list[dict[str, str]]:
        datasets = await self._datasets()
        return [
            {"id": str(d.get("id", "") or ""), "name": str(d.get("name", "") or "")} for d in datasets if d.get("id")
        ]

    async def build_tree(self, project_id: str) -> list[KBTreeNode]:
        folders = await self._cached_list(_folders_key(project_id), lambda: self._client.list_folders(project_id))
        documents = await self._cached_list(_documents_key(project_id), lambda: self._client.list_documents(project_id))
        return self._build_tree_nodes(folders, documents)

    async def upload_document(
        self,
        project_id: str,
        file_name: str,
        file_bytes: bytes,
    ) -> KBDocument | None:
        if is_archive(file_name):
            return await self._upload_archive(project_id, file_name, file_bytes)

        file_type = detect_file_type(file_name)
        if not file_type:
            logger.info("Ignoring unsupported file: %s", file_name)
            return None

        uploaded = await self._client.upload_document(project_id, file_name, file_bytes)
        if not uploaded:
            return None

        external_id = str(uploaded.get("id", "") or "")
        parsed = await self._client.trigger_parse(project_id, [external_id]) if external_id else False
        if not parsed:
            logger.warning("Document %s uploaded but parsing not triggered", external_id)

        fresh = await self._client.get_document(project_id, external_id) if external_id else None
        await self._drop_cache(_documents_key(project_id), _folders_key(project_id))
        return self._document_from_payload(project_id, fresh or uploaded)

    async def _upload_archive(
        self,
        project_id: str,
        archive_name: str,
        file_bytes: bytes,
    ) -> KBDocument | None:
        extracted_files = extract_archive(file_bytes, archive_name)
        if not extracted_files:
            logger.info("No supported files found in archive: %s", archive_name)
            return None

        # 压缩包本身不落成文档，只上传其中的成员；返回首份文档作为代表。
        representative: KBDocument | None = None
        for extracted in extracted_files:
            document = await self.upload_document(project_id, extracted.file_name, extracted.file_bytes)
            if document and representative is None:
                representative = document
        return representative

    async def delete_document(self, document_id: str) -> bool:
        dataset_id = await self._resolve_dataset_for_document(document_id)
        if not dataset_id:
            logger.warning("Cannot locate dataset for document %s", document_id)
            return False

        deleted = await self._client.delete_documents(dataset_id, [document_id])
        if deleted:
            await self._drop_cache(_documents_key(dataset_id), _folders_key(dataset_id))
        return deleted

    async def _resolve_dataset_for_document(self, document_id: str) -> str:  # noqa: D401
        """定位文档所属 dataset。

        RAGFlow 的删除接口要求 dataset id，但 UI 只持有文档 id，因此先扫描各
        dataset 的文档列表（走缓存）定位归属。
        """
        datasets = await self._datasets()
        for dataset in datasets:
            dataset_id = str(dataset.get("id", "") or "")
            if not dataset_id:
                continue
            documents = await self._cached_list(
                _documents_key(dataset_id),
                partial(self._client.list_documents, dataset_id),
            )
            if any(str(doc.get("id", "") or "") == document_id for doc in documents):
                return dataset_id
        return ""

    async def search(
        self,
        *,
        project_id: str,
        query: str,
        top_k: int | None = None,
    ) -> list[KBIndexHit]:
        chunks = await self._client.retrieve_chunks([project_id], query, top_k)
        return [KBIndexHit(**chunk) for chunk in chunks]
