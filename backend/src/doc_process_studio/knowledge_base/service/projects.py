import logging
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import KBDocument, KBFolder, KBProject
from ..schemas import KBProjectResponse

logger = logging.getLogger(__name__)


async def list_projects(db: AsyncSession) -> list[KBProjectResponse]:
    stmt = select(KBProject).order_by(KBProject.updated_at.desc())
    result = await db.execute(stmt)
    projects = result.scalars().all()
    return [KBProjectResponse.model_validate(p) for p in projects]


async def get_project(db: AsyncSession, project_id: str) -> KBProjectResponse | None:
    stmt = select(KBProject).where(KBProject.id == project_id)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        return None
    return KBProjectResponse.model_validate(project)


async def get_project_by_name(db: AsyncSession, name: str) -> KBProjectResponse | None:
    stmt = select(KBProject).where(KBProject.name == name)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        return None
    return KBProjectResponse.model_validate(project)


async def create_project(db: AsyncSession, name: str, description: str = "") -> KBProjectResponse:
    project = KBProject(name=name, description=description)
    db.add(project)
    await db.flush()
    return KBProjectResponse.model_validate(project)


async def rename_project(db: AsyncSession, project_id: str, new_name: str) -> KBProjectResponse | None:
    stmt = select(KBProject).where(KBProject.id == project_id)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        return None
    project.name = new_name
    await db.flush()
    return KBProjectResponse.model_validate(project)


async def delete_project(db: AsyncSession, project_id: str) -> bool:
    stmt = select(KBProject).where(KBProject.id == project_id)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        return False
    await db.delete(project)
    await db.flush()
    return True


async def update_project_stats(db: AsyncSession, project_id: str) -> None:
    folder_count_stmt = select(func.count()).select_from(KBFolder).where(KBFolder.project_id == project_id)
    doc_count_stmt = select(func.count()).select_from(KBDocument).where(KBDocument.project_id == project_id)
    folder_result = await db.execute(folder_count_stmt)
    doc_result = await db.execute(doc_count_stmt)
    folder_count = folder_result.scalar() or 0
    doc_count = doc_result.scalar() or 0
    await db.execute(
        update(KBProject)
        .where(KBProject.id == project_id)
        .values(
            folder_count=folder_count,
            document_count=doc_count,
            last_updated_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
    )
    await db.flush()


async def list_simple_projects(db: AsyncSession) -> list[dict]:
    stmt = select(KBProject.id, KBProject.name).order_by(KBProject.name)
    result = await db.execute(stmt)
    rows = result.all()
    return [{"id": row[0], "name": row[1]} for row in rows]
