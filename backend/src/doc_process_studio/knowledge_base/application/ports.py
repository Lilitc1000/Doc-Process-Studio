"""知识库应用层端口。

定义数据访问和外部服务抽象，由 infrastructure 层实现。
"""

from abc import ABC, abstractmethod
from typing import Any, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas import (
    KBDocumentResponse,
    KBFolderResponse,
    KBProjectResponse,
    KBTreeNode,
)
from ..schemas.common import KBChunkPayload


class KnowledgeBaseRepository(ABC):
    """知识库数据访问端口。

    封装项目/文件夹/文档的 CRUD、树构建、统计更新、文档上传与索引编排。
    所有写操作仅 flush 不 commit，由调用方控制事务边界。
    """

    @abstractmethod
    async def list_projects(self, db: AsyncSession) -> list[KBProjectResponse]: ...

    @abstractmethod
    async def get_project(self, db: AsyncSession, project_id: str) -> KBProjectResponse | None: ...

    @abstractmethod
    async def create_project(self, db: AsyncSession, name: str, description: str) -> KBProjectResponse: ...

    @abstractmethod
    async def rename_project(
        self, db: AsyncSession, project_id: str, new_name: str
    ) -> KBProjectResponse | None: ...

    @abstractmethod
    async def delete_project(self, db: AsyncSession, project_id: str) -> bool: ...

    @abstractmethod
    async def list_simple_projects(self, db: AsyncSession) -> list[dict[str, str]]: ...

    @abstractmethod
    async def create_folder(
        self,
        db: AsyncSession,
        project_id: str,
        name: str,
        parent_id: str | None = None,
    ) -> KBFolderResponse | None: ...

    @abstractmethod
    async def rename_folder(
        self, db: AsyncSession, folder_id: str, new_name: str
    ) -> KBFolderResponse | None: ...

    @abstractmethod
    async def delete_folder(self, db: AsyncSession, folder_id: str) -> bool: ...

    @abstractmethod
    async def build_tree(self, db: AsyncSession, project_id: str) -> list[KBTreeNode]: ...

    @abstractmethod
    async def update_project_stats(self, db: AsyncSession, project_id: str) -> None: ...

    @abstractmethod
    async def upload_document(
        self,
        db: AsyncSession,
        project_id: str,
        folder_id: str | None,
        file_name: str,
        file_bytes: bytes,
    ) -> KBDocumentResponse | None: ...

    @abstractmethod
    async def index_document(
        self,
        db: AsyncSession,
        document_id: str,
        project_name: str,
        file_bytes: bytes,
    ) -> int: ...

    @abstractmethod
    async def delete_document(self, db: AsyncSession, document_id: str) -> bool: ...


class VectorStore(ABC):
    """向量存储端口。"""

    @abstractmethod
    def delete_project_vectors(self, project_name: str) -> int: ...

    @abstractmethod
    def delete_document_vectors(self, document_id: str) -> int: ...

    @abstractmethod
    def upsert_chunks(
        self,
        project_name: str,
        document_id: str,
        chunks: Sequence[KBChunkPayload],
        vectors: Sequence[list[float]],
    ) -> int: ...

    @abstractmethod
    def search(
        self,
        project_name: str,
        query_vector: list[float],
        top_k: int | None = None,
    ) -> list[dict[str, Any]]: ...


class EmbeddingService(ABC):
    """文本向量化端口。"""

    @abstractmethod
    async def embed_texts(self, texts: Sequence[str], model: str | None = None) -> list[list[float]]: ...
