"""知识库应用服务。

用例编排：项目/文件夹/文档 CRUD、树构建、文档上传与索引、简单项目列表。
所有写操作由 router 层在用例返回后调用 db.commit() 提交事务。
"""

from sqlalchemy.ext.asyncio import AsyncSession

from ...common.infrastructure.config import settings
from ..domain.errors import (
    DocumentNotFoundError,
    FileTooLargeError,
    FolderNotFoundError,
    ProjectNotFoundError,
    UnsupportedFileTypeError,
)
from ..router.schemas import (
    KBDocumentResponse,
    KBFolderResponse,
    KBProjectListResponse,
    KBProjectListSimpleResponse,
    KBProjectResponse,
    KBProjectSimpleItem,
    KBTreeResponse,
)
from .ports import KnowledgeBaseRepository, VectorStore


class KnowledgeBaseService:
    """知识库用例服务。"""

    def __init__(
        self,
        *,
        repository: KnowledgeBaseRepository,
        vector_store: VectorStore,
    ) -> None:
        self._repo = repository
        self._vectors = vector_store

    async def list_projects(self, db: AsyncSession) -> KBProjectListResponse:
        projects = await self._repo.list_projects(db)
        return KBProjectListResponse(projects=projects)

    async def create_project(self, db: AsyncSession, name: str, description: str = "") -> KBProjectResponse:
        return await self._repo.create_project(db, name, description)

    async def get_project(self, db: AsyncSession, project_id: str) -> KBProjectResponse:
        project = await self._repo.get_project(db, project_id)
        if project is None:
            raise ProjectNotFoundError("Project not found")
        return project

    async def rename_project(self, db: AsyncSession, project_id: str, new_name: str) -> KBProjectResponse:
        project = await self._repo.rename_project(db, project_id, new_name)
        if project is None:
            raise ProjectNotFoundError("Project not found")
        return project

    async def delete_project(self, db: AsyncSession, project_id: str) -> None:
        project = await self._repo.get_project(db, project_id)
        if project is None:
            raise ProjectNotFoundError("Project not found")
        self._vectors.delete_project_vectors(project.name)
        await self._repo.delete_project(db, project_id)

    async def list_simple_projects(self, db: AsyncSession) -> KBProjectListSimpleResponse:
        rows = await self._repo.list_simple_projects(db)
        projects = [KBProjectSimpleItem(id=row["id"], name=row["name"]) for row in rows]
        return KBProjectListSimpleResponse(projects=projects)

    async def create_folder(
        self,
        db: AsyncSession,
        project_id: str,
        name: str,
        parent_id: str | None = None,
    ) -> KBFolderResponse:
        folder = await self._repo.create_folder(db, project_id, name, parent_id)
        if folder is None:
            raise ProjectNotFoundError("Project or parent folder not found")
        await self._repo.update_project_stats(db, project_id)
        return folder

    async def rename_folder(self, db: AsyncSession, folder_id: str, new_name: str) -> KBFolderResponse:
        folder = await self._repo.rename_folder(db, folder_id, new_name)
        if folder is None:
            raise FolderNotFoundError("Folder not found")
        return folder

    async def delete_folder(self, db: AsyncSession, folder_id: str) -> None:
        success = await self._repo.delete_folder(db, folder_id)
        if not success:
            raise FolderNotFoundError("Folder not found")

    async def build_tree(self, db: AsyncSession, project_id: str) -> KBTreeResponse:
        project = await self._repo.get_project(db, project_id)
        if project is None:
            raise ProjectNotFoundError("Project not found")
        tree = await self._repo.build_tree(db, project_id)
        return KBTreeResponse(
            project_id=project.id,
            project_name=project.name,
            tree=tree,
        )

    async def upload_document(
        self,
        db: AsyncSession,
        project_id: str,
        folder_id: str | None,
        file_name: str,
        file_bytes: bytes,
    ) -> KBDocumentResponse:
        if len(file_bytes) > settings.kb_max_upload_size_bytes:
            raise FileTooLargeError("File size exceeds 100MB limit")

        doc = await self._repo.upload_document(db, project_id, folder_id, file_name, file_bytes)
        if doc is None:
            raise UnsupportedFileTypeError("Unsupported file format or project not found")

        project = await self._repo.get_project(db, project_id)
        if project and not doc.is_indexed and doc.file_type != "archive":
            chunk_count = await self._repo.index_document(db, doc.id, project.name, file_bytes)
            doc.is_indexed = True
            doc.chunk_count = chunk_count

        await self._repo.update_project_stats(db, project_id)
        return doc

    async def delete_document(self, db: AsyncSession, document_id: str) -> None:
        success = await self._repo.delete_document(db, document_id)
        if not success:
            raise DocumentNotFoundError("Document not found")
