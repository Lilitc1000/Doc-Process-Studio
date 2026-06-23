"""Qdrant 向量存储实现。

实现 VectorStore 端口，委托 service/qdrant_service.py 的纯函数。
"""

from collections.abc import Sequence
from typing import Any

from ..application.ports import VectorStore
from ..schemas.common import KBChunkPayload
from ..service.qdrant_service import (
    delete_document_vectors,
    delete_project_vectors,
    search_knowledge_base,
    upsert_chunks,
)


class QdrantVectorStore(VectorStore):
    """基于 Qdrant 的向量存储。"""

    def delete_project_vectors(self, project_name: str) -> int:
        return delete_project_vectors(project_name)

    def delete_document_vectors(self, document_id: str) -> int:
        return delete_document_vectors(document_id)

    def upsert_chunks(
        self,
        project_name: str,
        document_id: str,
        chunks: Sequence[KBChunkPayload],
        vectors: Sequence[list[float]],
    ) -> int:
        return upsert_chunks(project_name, document_id, chunks, vectors)

    def search(
        self,
        project_name: str,
        query_vector: list[float],
        top_k: int | None = None,
    ) -> list[dict[str, Any]]:
        return search_knowledge_base(project_name, query_vector, top_k=top_k)
