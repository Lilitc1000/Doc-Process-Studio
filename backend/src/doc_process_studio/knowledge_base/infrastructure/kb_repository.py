"""SQLAlchemy 知识库仓储实现。

实现 KnowledgeBaseRepository 端口，委托基础设施层函数完成数据访问与索引编排。
"""

from sqlalchemy.ext.asyncio import AsyncSession

from ..application.ports import KnowledgeBaseRepository
from ..router.schemas import (
    KBDocumentResponse,
    KBFolderResponse,
    KBProjectResponse,
    KBTreeNode,
)
from .documents import delete_document as _delete_document
from .documents import index_document as _index_document
from .documents import upload_document as _upload_document
from .folders import build_tree as _build_tree
from .folders import create_folder as _create_folder
from .folders import delete_folder as _delete_folder
from .folders import rename_folder as _rename_folder
from .projects import create_project as _create_project
from .projects import delete_project as _delete_project
from .projects import get_project as _get_project
from .projects import list_projects as _list_projects
from .projects import list_simple_projects as _list_simple_projects
from .projects import rename_project as _rename_project
from .projects import update_project_stats as _update_project_stats


class SqlKnowledgeBaseRepository(KnowledgeBaseRepository):
    """基于 SQLAlchemy 的知识库仓储。"""

    async def list_projects(self, db: AsyncSession) -> list[KBProjectResponse]:
        return await _list_projects(db)

    async def get_project(self, db: AsyncSession, project_id: str) -> KBProjectResponse | None:
        return await _get_project(db, project_id)

    async def create_project(self, db: AsyncSession, name: str, description: str) -> KBProjectResponse:
        return await _create_project(db, name, description)

    async def rename_project(self, db: AsyncSession, project_id: str, new_name: str) -> KBProjectResponse | None:
        return await _rename_project(db, project_id, new_name)

    async def delete_project(self, db: AsyncSession, project_id: str) -> bool:
        return await _delete_project(db, project_id)

    async def list_simple_projects(self, db: AsyncSession) -> list[dict[str, str]]:
        return await _list_simple_projects(db)

    async def create_folder(
        self,
        db: AsyncSession,
        project_id: str,
        name: str,
        parent_id: str | None = None,
    ) -> KBFolderResponse | None:
        return await _create_folder(db, project_id, name, parent_id)

    async def rename_folder(self, db: AsyncSession, folder_id: str, new_name: str) -> KBFolderResponse | None:
        return await _rename_folder(db, folder_id, new_name)

    async def delete_folder(self, db: AsyncSession, folder_id: str) -> bool:
        return await _delete_folder(db, folder_id)

    async def build_tree(self, db: AsyncSession, project_id: str) -> list[KBTreeNode]:
        return await _build_tree(db, project_id)

    async def update_project_stats(self, db: AsyncSession, project_id: str) -> None:
        await _update_project_stats(db, project_id)

    async def upload_document(
        self,
        db: AsyncSession,
        project_id: str,
        folder_id: str | None,
        file_name: str,
        file_bytes: bytes,
    ) -> KBDocumentResponse | None:
        return await _upload_document(db, project_id, folder_id, file_name, file_bytes)

    async def index_document(
        self,
        db: AsyncSession,
        document_id: str,
        project_name: str,
        file_bytes: bytes,
    ) -> int:
        return await _index_document(db, document_id, project_name, file_bytes)

    async def delete_document(self, db: AsyncSession, document_id: str) -> bool:
        return await _delete_document(db, document_id)
