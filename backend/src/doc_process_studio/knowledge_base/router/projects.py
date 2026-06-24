import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.security import get_current_user_id
from ..application.kb_service import KnowledgeBaseService
from ..domain.errors import (
    DocumentNotFoundError,
    FileTooLargeError,
    FolderNotFoundError,
    KnowledgeBaseError,
    ProjectNotFoundError,
    UnsupportedFileTypeError,
)
from ..infrastructure.dependencies import get_kb_service
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

_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/knowledge-base", tags=["knowledge-base"])


def _handle_kb_error(exc: KnowledgeBaseError) -> HTTPException:
    if isinstance(exc, (ProjectNotFoundError, FolderNotFoundError, DocumentNotFoundError)):
        _logger.warning("KB error (404): %s", exc)
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, FileTooLargeError):
        _logger.warning("KB error (413): %s", exc)
        return HTTPException(status_code=413, detail=str(exc))
    if isinstance(exc, UnsupportedFileTypeError):
        _logger.warning("KB error (400): %s", exc)
        return HTTPException(status_code=400, detail=str(exc))
    _logger.warning("KB error (400): %s", exc)
    return HTTPException(status_code=400, detail=str(exc))


@router.get("/projects", response_model=KBProjectListResponse)
async def list_kb_projects(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    service: KnowledgeBaseService = Depends(get_kb_service),
) -> KBProjectListResponse:
    return await service.list_projects(db)


@router.post("/projects", response_model=KBProjectResponse, status_code=201)
async def create_kb_project(
    body: KBProjectCreateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    service: KnowledgeBaseService = Depends(get_kb_service),
) -> KBProjectResponse:
    project = await service.create_project(db, body.name, body.description)
    await db.commit()
    return project


@router.get("/projects/{project_id}", response_model=KBProjectResponse)
async def get_kb_project(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    service: KnowledgeBaseService = Depends(get_kb_service),
) -> KBProjectResponse:
    try:
        return await service.get_project(db, project_id)
    except KnowledgeBaseError as exc:
        raise _handle_kb_error(exc) from exc


@router.put("/projects/{project_id}/rename", response_model=KBProjectResponse)
async def rename_kb_project(
    project_id: str,
    body: KBProjectRenameRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    service: KnowledgeBaseService = Depends(get_kb_service),
) -> KBProjectResponse:
    try:
        project = await service.rename_project(db, project_id, body.name)
    except KnowledgeBaseError as exc:
        raise _handle_kb_error(exc) from exc
    await db.commit()
    return project


@router.delete("/projects/{project_id}", status_code=204)
async def delete_kb_project(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    service: KnowledgeBaseService = Depends(get_kb_service),
) -> None:
    try:
        await service.delete_project(db, project_id)
    except KnowledgeBaseError as exc:
        raise _handle_kb_error(exc) from exc
    await db.commit()


@router.post("/projects/{project_id}/folders", response_model=KBFolderResponse, status_code=201)
async def create_kb_folder(
    project_id: str,
    body: KBFolderCreateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    service: KnowledgeBaseService = Depends(get_kb_service),
) -> KBFolderResponse:
    try:
        folder = await service.create_folder(db, project_id, body.name, body.parent_id)
    except KnowledgeBaseError as exc:
        raise _handle_kb_error(exc) from exc
    await db.commit()
    return folder


@router.put("/folders/{folder_id}/rename", response_model=KBFolderResponse)
async def rename_kb_folder(
    folder_id: str,
    body: KBFolderRenameRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    service: KnowledgeBaseService = Depends(get_kb_service),
) -> KBFolderResponse:
    try:
        folder = await service.rename_folder(db, folder_id, body.name)
    except KnowledgeBaseError as exc:
        raise _handle_kb_error(exc) from exc
    await db.commit()
    return folder


@router.delete("/folders/{folder_id}", status_code=204)
async def delete_kb_folder(
    folder_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    service: KnowledgeBaseService = Depends(get_kb_service),
) -> None:
    try:
        await service.delete_folder(db, folder_id)
    except KnowledgeBaseError as exc:
        raise _handle_kb_error(exc) from exc
    await db.commit()


@router.get("/projects/{project_id}/tree", response_model=KBTreeResponse)
async def get_kb_tree(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    service: KnowledgeBaseService = Depends(get_kb_service),
) -> KBTreeResponse:
    try:
        return await service.build_tree(db, project_id)
    except KnowledgeBaseError as exc:
        raise _handle_kb_error(exc) from exc


@router.post("/projects/{project_id}/documents/upload", response_model=KBDocumentResponse, status_code=201)
async def upload_kb_document(
    project_id: str,
    file: UploadFile = File(...),
    folder_id: str | None = Form(None),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    service: KnowledgeBaseService = Depends(get_kb_service),
) -> KBDocumentResponse:
    content = await file.read()
    try:
        doc = await service.upload_document(
            db,
            project_id,
            folder_id,
            file.filename or "unknown",
            content,
        )
    except KnowledgeBaseError as exc:
        raise _handle_kb_error(exc) from exc
    await db.commit()
    return doc


@router.delete("/documents/{document_id}", status_code=204)
async def delete_kb_document(
    document_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    service: KnowledgeBaseService = Depends(get_kb_service),
) -> None:
    try:
        await service.delete_document(db, document_id)
    except KnowledgeBaseError as exc:
        raise _handle_kb_error(exc) from exc
    await db.commit()


@router.get("/projects-simple", response_model=KBProjectListSimpleResponse)
async def list_kb_projects_simple(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    service: KnowledgeBaseService = Depends(get_kb_service),
) -> KBProjectListSimpleResponse:
    return await service.list_simple_projects(db)
