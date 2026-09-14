import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from ...common.security.security import get_current_user_id
from ..application.kb_service import KnowledgeBaseService
from ..domain.errors import (
    DocumentNotFoundError,
    FileTooLargeError,
    KnowledgeBaseError,
    ProjectNotFoundError,
    UnsupportedFileTypeError,
)
from ..infrastructure.dependencies import get_kb_service
from .schemas import (
    KBDocumentResponse,
    KBProjectCreateRequest,
    KBProjectListResponse,
    KBProjectListSimpleResponse,
    KBProjectRenameRequest,
    KBProjectResponse,
    KBTreeResponse,
)

_logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/knowledge-base",
    tags=["knowledge-base"],
    dependencies=[Depends(get_current_user_id)],
)


def _handle_kb_error(exc: KnowledgeBaseError) -> HTTPException:
    if isinstance(exc, ProjectNotFoundError):
        _logger.warning("KB project not found: %s", exc)
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, DocumentNotFoundError):
        _logger.warning("KB document not found: %s", exc)
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, FileTooLargeError):
        _logger.warning("KB file too large: %s", exc)
        return HTTPException(status_code=413, detail=str(exc))
    if isinstance(exc, UnsupportedFileTypeError):
        _logger.warning("KB unsupported file: %s", exc)
        return HTTPException(status_code=400, detail=str(exc))
    _logger.warning("KB error (400): %s", exc)
    return HTTPException(status_code=400, detail=str(exc))


@router.get("/projects", response_model=KBProjectListResponse)
async def list_kb_projects(
    service: KnowledgeBaseService = Depends(get_kb_service),
) -> KBProjectListResponse:
    return await service.list_projects()


@router.post("/projects", response_model=KBProjectResponse, status_code=201)
async def create_kb_project(
    body: KBProjectCreateRequest,
    service: KnowledgeBaseService = Depends(get_kb_service),
) -> KBProjectResponse:
    return await service.create_project(body.name, body.description)


@router.get("/projects-simple", response_model=KBProjectListSimpleResponse)
async def list_kb_projects_simple(
    service: KnowledgeBaseService = Depends(get_kb_service),
) -> KBProjectListSimpleResponse:
    return await service.list_simple_projects()


@router.get("/projects/{project_id}", response_model=KBProjectResponse)
async def get_kb_project(
    project_id: str,
    service: KnowledgeBaseService = Depends(get_kb_service),
) -> KBProjectResponse:
    try:
        return await service.get_project(project_id)
    except KnowledgeBaseError as exc:
        raise _handle_kb_error(exc) from exc


@router.put("/projects/{project_id}/rename", response_model=KBProjectResponse)
async def rename_kb_project(
    project_id: str,
    body: KBProjectRenameRequest,
    service: KnowledgeBaseService = Depends(get_kb_service),
) -> KBProjectResponse:
    try:
        return await service.rename_project(project_id, body.name)
    except KnowledgeBaseError as exc:
        raise _handle_kb_error(exc) from exc


@router.delete("/projects/{project_id}", status_code=204)
async def delete_kb_project(
    project_id: str,
    service: KnowledgeBaseService = Depends(get_kb_service),
) -> None:
    try:
        await service.delete_project(project_id)
    except KnowledgeBaseError as exc:
        raise _handle_kb_error(exc) from exc


@router.get("/projects/{project_id}/tree", response_model=KBTreeResponse)
async def get_kb_tree(
    project_id: str,
    service: KnowledgeBaseService = Depends(get_kb_service),
) -> KBTreeResponse:
    try:
        return await service.build_tree(project_id)
    except KnowledgeBaseError as exc:
        raise _handle_kb_error(exc) from exc


@router.post("/projects/{project_id}/documents/upload", response_model=KBDocumentResponse, status_code=201)
async def upload_kb_document(
    project_id: str,
    file: UploadFile = File(...),
    service: KnowledgeBaseService = Depends(get_kb_service),
) -> KBDocumentResponse:
    content = await file.read()
    try:
        return await service.upload_document(project_id, file.filename or "unknown", content)
    except KnowledgeBaseError as exc:
        raise _handle_kb_error(exc) from exc


@router.delete("/documents/{document_id}", status_code=204)
async def delete_kb_document(
    document_id: str,
    service: KnowledgeBaseService = Depends(get_kb_service),
) -> None:
    try:
        await service.delete_document(document_id)
    except KnowledgeBaseError as exc:
        raise _handle_kb_error(exc) from exc
