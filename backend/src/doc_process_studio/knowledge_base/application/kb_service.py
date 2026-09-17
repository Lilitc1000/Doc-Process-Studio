"""知识库应用服务。

用例编排：项目的增删改查、树构建、文档上传与删除、单 dataset 检索。

知识库已无本地持久化：所有数据来自 RAGFlow，仓库 unavailable 时读路径返回空容器，
由本服务翻译成领域错误（404）或空列表，不在 Router 层做重试 / 降级判断。
"""

from ...common.infrastructure.config import settings
from ..domain.errors import (
    DocumentNotFoundError,
    FileTooLargeError,
    ProjectNotFoundError,
    UnsupportedFileTypeError,
)
from .dtos import (
    KBDocument,
    KBDocumentParseDetail,
    KBIndexHit,
    KBProject,
    KBProjectSimpleItem,
    KBProjectTree,
)
from .ports import KnowledgeBaseRepository


class KnowledgeBaseService:
    """知识库用例服务。"""

    def __init__(self, *, repository: KnowledgeBaseRepository) -> None:
        self._repo = repository

    async def list_projects(self) -> list[KBProject]:
        return await self._repo.list_projects()

    async def create_project(self, name: str, description: str = "") -> KBProject:
        return await self._repo.create_project(name, description)

    async def get_project(self, project_id: str) -> KBProject:
        project = await self._repo.get_project(project_id)
        if project is None:
            raise ProjectNotFoundError("Project not found")
        return project

    async def rename_project(self, project_id: str, new_name: str) -> KBProject:
        project = await self._repo.rename_project(project_id, new_name)
        if project is None:
            raise ProjectNotFoundError("Project not found")
        return project

    async def delete_project(self, project_id: str) -> None:
        success = await self._repo.delete_project(project_id)
        if not success:
            raise ProjectNotFoundError("Project not found")

    async def list_simple_projects(self) -> list[KBProjectSimpleItem]:
        rows = await self._repo.list_simple_projects()
        return [KBProjectSimpleItem(id=row["id"], name=row["name"]) for row in rows]

    async def build_tree(self, project_id: str) -> KBProjectTree:
        project = await self._repo.get_project(project_id)
        if project is None:
            raise ProjectNotFoundError("Project not found")
        tree = await self._repo.build_tree(project_id)
        return KBProjectTree(
            project_id=project.id,
            project_name=project.name,
            tree=tree,
        )

    async def upload_document(
        self,
        project_id: str,
        file_name: str,
        file_bytes: bytes,
    ) -> KBDocument:
        if len(file_bytes) > settings.kb_max_upload_size_bytes:
            raise FileTooLargeError("File size exceeds the configured upload limit")

        document = await self._repo.upload_document(project_id, file_name, file_bytes)
        if document is None:
            raise UnsupportedFileTypeError("Unsupported file format or dataset unavailable")
        return document

    async def delete_document(self, document_id: str) -> None:
        success = await self._repo.delete_document(document_id)
        if not success:
            raise DocumentNotFoundError("Document not found")

    async def get_parse_detail(self, document_id: str) -> KBDocumentParseDetail:
        detail = await self._repo.get_document_parse_detail(document_id)
        if detail is None:
            raise DocumentNotFoundError("Document not found")
        return detail

    async def reparse_document(self, document_id: str) -> None:
        success = await self._repo.trigger_document_parse(document_id)
        if not success:
            raise DocumentNotFoundError("Document not found")

    async def search_knowledge(
        self,
        *,
        project_id: str,
        query: str,
        top_k: int | None = None,
    ) -> list[KBIndexHit]:
        """供对话侧 ``search_knowledge_base`` 工具使用的单 dataset 检索。"""
        return await self._repo.search(project_id=project_id, query=query, top_k=top_k)


__all__ = ["KnowledgeBaseService"]
