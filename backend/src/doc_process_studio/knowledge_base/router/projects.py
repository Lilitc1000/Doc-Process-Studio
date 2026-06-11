from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...core.database import get_db
from ...core.security import get_current_user_id
from ..schemas import (
    KBDocumentResponse,
    KBFolderCreateRequest,
    KBFolderRenameRequest,
    KBFolderResponse,
    KBProjectCreateRequest,
    KBProjectListResponse,
    KBProjectListSimpleResponse,
    KBProjectRenameRequest,
    KBProjectResponse,
    KBTreeResponse,
)
from ..service import (
    build_tree,
    create_folder,
    create_project,
    delete_document,
    delete_folder,
    delete_project,
    get_project,
    index_document,
    list_projects,
    rename_folder,
    rename_project,
    update_project_stats,
    upload_document,
)
from ..service.qdrant_service import delete_project_vectors

router = APIRouter(prefix="/api/knowledge-base", tags=["knowledge-base"])


@router.get("/projects", response_model=KBProjectListResponse)
async def list_kb_projects(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> KBProjectListResponse:
    projects = await list_projects(db)
    return KBProjectListResponse(projects=projects)


@router.post("/projects", response_model=KBProjectResponse, status_code=201)
async def create_kb_project(
    body: KBProjectCreateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> KBProjectResponse:
    project = await create_project(db, body.name, body.description)
    await db.commit()
    return project


@router.get("/projects/{project_id}", response_model=KBProjectResponse)
async def get_kb_project(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> KBProjectResponse:
    project = await get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.put("/projects/{project_id}/rename", response_model=KBProjectResponse)
async def rename_kb_project(
    project_id: str,
    body: KBProjectRenameRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> KBProjectResponse:
    project = await rename_project(db, project_id, body.name)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await db.commit()
    return project


@router.delete("/projects/{project_id}", status_code=204)
async def delete_kb_project(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    project = await get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    delete_project_vectors(project.name)
    await delete_project(db, project_id)
    await db.commit()


@router.post("/projects/{project_id}/folders", response_model=KBFolderResponse, status_code=201)
async def create_kb_folder(
    project_id: str,
    body: KBFolderCreateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> KBFolderResponse:
    folder = await create_folder(db, project_id, body.name, body.parent_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Project or parent folder not found")
    await update_project_stats(db, project_id)
    await db.commit()
    return folder


@router.put("/folders/{folder_id}/rename", response_model=KBFolderResponse)
async def rename_kb_folder(
    folder_id: str,
    body: KBFolderRenameRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> KBFolderResponse:
    folder = await rename_folder(db, folder_id, body.name)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    await db.commit()
    return folder


@router.delete("/folders/{folder_id}", status_code=204)
async def delete_kb_folder(
    folder_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    success = await delete_folder(db, folder_id)
    if not success:
        raise HTTPException(status_code=404, detail="Folder not found")
    await db.commit()


@router.get("/projects/{project_id}/tree", response_model=KBTreeResponse)
async def get_kb_tree(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> KBTreeResponse:
    project = await get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    tree = await build_tree(db, project_id)
    return KBTreeResponse(
        project_id=project.id,
        project_name=project.name,
        tree=tree,
    )


@router.post("/projects/{project_id}/documents/upload", response_model=KBDocumentResponse, status_code=201)
async def upload_kb_document(
    project_id: str,
    file: UploadFile = File(...),
    folder_id: str | None = Form(None),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> KBDocumentResponse:
    content = await file.read()
    if len(content) > settings.kb_max_upload_size_bytes:
        raise HTTPException(status_code=413, detail="File size exceeds 100MB limit")

    doc = await upload_document(db, project_id, folder_id, file.filename or "unknown", content)
    if not doc:
        raise HTTPException(status_code=400, detail="Unsupported file format or project not found")

    # 上传后立即索引文档（解析 → 分块 → 向量化 → 写入 Qdrant）
    # archive 类型的文档在 _handle_archive_upload 中已对子文档逐一索引
    project = await get_project(db, project_id)
    if project and not doc.is_indexed and doc.file_type != "archive":
        chunk_count = await index_document(db, doc.id, project.name, content)
        doc.is_indexed = True
        doc.chunk_count = chunk_count

    await update_project_stats(db, project_id)
    await db.commit()
    return doc


@router.delete("/documents/{document_id}", status_code=204)
async def delete_kb_document(
    document_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    success = await delete_document(db, document_id)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")
    await db.commit()


@router.get("/projects-simple", response_model=KBProjectListSimpleResponse)
async def list_kb_projects_simple(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> KBProjectListSimpleResponse:
    from ..service import list_simple_projects
    projects = await list_simple_projects(db)
    return KBProjectListSimpleResponse(projects=projects)
