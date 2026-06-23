from datetime import datetime as dt
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from ...core.security import get_current_user_id
from ..application.audit_query_service import AuditQueryService
from ..application.commands import (
    ApproveReportCommand,
    AssignHandlerCommand,
    CloseReportCommand,
    CreateReportCommand,
    DeleteReportCommand,
    RejectReportCommand,
    ReopenReportCommand,
    SubmitReportCommand,
    UpdateReportCommand,
)
from ..application.comment_service import CommentService
from ..application.generation_service import GenerationService
from ..application.preview_service import PreviewService
from ..application.report_service import ReportApplicationService
from ..domain.errors import (
    DomainError,
    PermissionDeniedError,
    ReportNotFoundError,
)
from ..infrastructure.dependencies import (
    get_audit_query_service,
    get_comment_service,
    get_generation_service,
    get_preview_service,
    get_report_application_service,
)
from ..schemas.common import PermissionDenied
from ..schemas.request import (
    IncidentBodyQuickGenerateRequest,
    IncidentBodySectionGenerateRequest,
    IncidentCommentCreateRequest,
    IncidentReportApproveRequest,
    IncidentReportAssignRequest,
    IncidentReportCloseRequest,
    IncidentReportCreateRequest,
    IncidentReportPreviewRequest,
    IncidentReportRejectRequest,
    IncidentReportReopenRequest,
    IncidentReportSubmitRequest,
    IncidentReportUpdateRequest,
)
from ..schemas.response import (
    IncidentAuditLogEntry,
    IncidentBodyGenerateResponse,
    IncidentCommentEntry,
    IncidentReportDetail,
    IncidentReportListResponse,
    IncidentReportPreviewResponse,
)

router = APIRouter(prefix="/api/incident-report", tags=["incident-report"])


def _handle_domain_error(exc: DomainError) -> HTTPException:
    """领域异常 → HTTP 状态码映射。"""
    if isinstance(exc, PermissionDeniedError):
        return HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, ReportNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=400, detail=str(exc))


def _handle_service_error(exc: ValueError | DomainError) -> HTTPException:
    """将服务层异常映射为 HTTP 响应。"""
    if isinstance(exc, PermissionDenied):
        return HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, DomainError):
        return _handle_domain_error(exc)
    return HTTPException(status_code=400, detail=str(exc))


@router.get("/reports/schema")
async def get_report_form_schema(
    service: ReportApplicationService = Depends(get_report_application_service),
) -> dict[str, Any]:
    return service.get_form_schema()


@router.get("/reports", response_model=IncidentReportListResponse)
async def list_reports(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    search: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    user_id: str = Depends(get_current_user_id),
    service: ReportApplicationService = Depends(get_report_application_service),
) -> IncidentReportListResponse:
    sd = dt.fromisoformat(start_date) if start_date else None
    ed = dt.fromisoformat(end_date) if end_date else None
    return await service.list(
        user_id=user_id,
        page=page,
        page_size=page_size,
        status=status,
        severity=severity,
        search=search,
        start_date=sd,
        end_date=ed,
    )


@router.get("/reports/{report_id}", response_model=IncidentReportDetail)
async def get_report_detail(
    report_id: str,
    user_id: str = Depends(get_current_user_id),
    service: ReportApplicationService = Depends(get_report_application_service),
) -> IncidentReportDetail:
    try:
        report = await service.get(report_id, user_id=user_id)
    except (ValueError, DomainError) as exc:
        raise _handle_service_error(exc) from exc
    if report is None:
        raise HTTPException(status_code=404, detail="报告不存在")
    return report


@router.post("/reports", response_model=IncidentReportDetail)
async def create_new_report(
    payload: IncidentReportCreateRequest,
    user_id: str = Depends(get_current_user_id),
    service: ReportApplicationService = Depends(get_report_application_service),
) -> IncidentReportDetail:
    try:
        return await service.create(
            CreateReportCommand(
                title=payload.title,
                reporter_id=user_id,
                severity=payload.severity,
                system=payload.system,
                site_id=payload.site_id,
                fault_date=payload.fault_date,
                form_data=payload.form_data,
            )
        )
    except (ValueError, DomainError) as exc:
        raise _handle_service_error(exc) from exc


@router.put("/reports/{report_id}", response_model=IncidentReportDetail)
async def update_existing_report(
    report_id: str,
    payload: IncidentReportUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    service: ReportApplicationService = Depends(get_report_application_service),
) -> IncidentReportDetail:
    fields = {k: v for k, v in payload.model_dump().items() if v is not None}
    try:
        result = await service.update(UpdateReportCommand(report_id=report_id, actor_id=user_id, fields=fields))
    except (ValueError, DomainError) as exc:
        raise _handle_service_error(exc) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="报告不存在")
    return result


@router.delete("/reports/{report_id}")
async def delete_report_by_id(
    report_id: str,
    user_id: str = Depends(get_current_user_id),
    service: ReportApplicationService = Depends(get_report_application_service),
) -> dict[str, bool]:
    try:
        deleted = await service.delete(DeleteReportCommand(report_id=report_id, actor_id=user_id))
    except (ValueError, DomainError) as exc:
        raise _handle_service_error(exc) from exc
    return {"deleted": deleted}


@router.post("/reports/{report_id}/submit", response_model=IncidentReportDetail)
async def submit_report_for_review(
    report_id: str,
    payload: IncidentReportSubmitRequest | None = None,
    user_id: str = Depends(get_current_user_id),
    service: ReportApplicationService = Depends(get_report_application_service),
) -> IncidentReportDetail:
    comment = payload.comment if payload else None
    try:
        result = await service.submit(SubmitReportCommand(report_id=report_id, actor_id=user_id, comment=comment))
    except (ValueError, DomainError) as exc:
        raise _handle_service_error(exc) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="报告不存在")
    return result


@router.post("/reports/{report_id}/approve", response_model=IncidentReportDetail)
async def approve_report_review(
    report_id: str,
    payload: IncidentReportApproveRequest,
    user_id: str = Depends(get_current_user_id),
    service: ReportApplicationService = Depends(get_report_application_service),
) -> IncidentReportDetail:
    try:
        result = await service.approve(
            ApproveReportCommand(report_id=report_id, actor_id=user_id, comment=payload.comment)
        )
    except (ValueError, DomainError) as exc:
        raise _handle_service_error(exc) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="报告不存在")
    return result


@router.post("/reports/{report_id}/reject", response_model=IncidentReportDetail)
async def reject_report_review(
    report_id: str,
    payload: IncidentReportRejectRequest,
    user_id: str = Depends(get_current_user_id),
    service: ReportApplicationService = Depends(get_report_application_service),
) -> IncidentReportDetail:
    try:
        result = await service.reject(
            RejectReportCommand(report_id=report_id, actor_id=user_id, comment=payload.comment)
        )
    except (ValueError, DomainError) as exc:
        raise _handle_service_error(exc) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="报告不存在")
    return result


@router.post("/reports/{report_id}/assign", response_model=IncidentReportDetail)
async def assign_report_handler(
    report_id: str,
    payload: IncidentReportAssignRequest,
    user_id: str = Depends(get_current_user_id),
    service: ReportApplicationService = Depends(get_report_application_service),
) -> IncidentReportDetail:
    try:
        result = await service.assign_handler(
            AssignHandlerCommand(report_id=report_id, actor_id=user_id, assignee_id=payload.assignee_id)
        )
    except (ValueError, DomainError) as exc:
        raise _handle_service_error(exc) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="报告不存在")
    return result


@router.post("/reports/{report_id}/close", response_model=IncidentReportDetail)
async def close_report_by_handler(
    report_id: str,
    payload: IncidentReportCloseRequest | None = None,
    user_id: str = Depends(get_current_user_id),
    service: ReportApplicationService = Depends(get_report_application_service),
) -> IncidentReportDetail:
    comment = payload.comment if payload else None
    try:
        result = await service.close(CloseReportCommand(report_id=report_id, actor_id=user_id, comment=comment))
    except (ValueError, DomainError) as exc:
        raise _handle_service_error(exc) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="报告不存在")
    return result


@router.post("/reports/{report_id}/reopen", response_model=IncidentReportDetail)
async def reopen_closed_report(
    report_id: str,
    payload: IncidentReportReopenRequest | None = None,
    user_id: str = Depends(get_current_user_id),
    service: ReportApplicationService = Depends(get_report_application_service),
) -> IncidentReportDetail:
    comment = payload.comment if payload else None
    try:
        result = await service.reopen(ReopenReportCommand(report_id=report_id, actor_id=user_id, comment=comment))
    except (ValueError, DomainError) as exc:
        raise _handle_service_error(exc) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="报告不存在")
    return result


@router.post(
    "/reports/{report_id}/body/quick-generate",
    response_model=IncidentBodyGenerateResponse,
)
async def quick_generate_report_body(
    report_id: str,
    payload: IncidentBodyQuickGenerateRequest,
    user_id: str = Depends(get_current_user_id),
    service: GenerationService = Depends(get_generation_service),
) -> IncidentBodyGenerateResponse:
    try:
        return await service.quick_generate(
            report_id=report_id,
            user_id=user_id,
            model=payload.model,
            reranker_model=payload.reranker_model,
        )
    except ValueError as exc:
        raise _handle_service_error(exc) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post(
    "/reports/{report_id}/body/section-generate",
    response_model=IncidentBodyGenerateResponse,
)
async def generate_report_body_section(
    report_id: str,
    payload: IncidentBodySectionGenerateRequest,
    user_id: str = Depends(get_current_user_id),
    service: GenerationService = Depends(get_generation_service),
) -> IncidentBodyGenerateResponse:
    try:
        return await service.generate_section(
            report_id=report_id,
            section_id=payload.section_id,
            timeline_index=payload.timeline_index,
            user_id=user_id,
            model=payload.model,
            reranker_model=payload.reranker_model,
        )
    except ValueError as exc:
        raise _handle_service_error(exc) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post(
    "/reports/{report_id}/preview",
    response_model=IncidentReportPreviewResponse,
)
async def preview_report_attachment(
    report_id: str,
    payload: IncidentReportPreviewRequest,
    user_id: str = Depends(get_current_user_id),
    service: PreviewService = Depends(get_preview_service),
) -> IncidentReportPreviewResponse:
    try:
        return await service.preview_report(
            report_id=report_id,
            user_id=user_id,
            version=payload.version,
            model=payload.model,
            reranker_model=payload.reranker_model,
        )
    except ValueError as exc:
        raise _handle_service_error(exc) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/reports/{report_id}/audit-logs", response_model=list[IncidentAuditLogEntry])
async def get_report_audit_logs(
    report_id: str,
    user_id: str = Depends(get_current_user_id),
    service: AuditQueryService = Depends(get_audit_query_service),
) -> list[IncidentAuditLogEntry]:
    try:
        return await service.list_audit_logs(report_id, user_id=user_id)
    except (ValueError, DomainError) as exc:
        raise _handle_service_error(exc) from exc


@router.get("/reports/{report_id}/comments", response_model=list[IncidentCommentEntry])
async def get_report_comments(
    report_id: str,
    user_id: str = Depends(get_current_user_id),
    service: CommentService = Depends(get_comment_service),
) -> list[IncidentCommentEntry]:
    try:
        return await service.list_comments(report_id, user_id=user_id)
    except (ValueError, DomainError) as exc:
        raise _handle_service_error(exc) from exc


@router.post("/reports/{report_id}/comments", response_model=IncidentCommentEntry)
async def add_report_comment(
    report_id: str,
    payload: IncidentCommentCreateRequest,
    user_id: str = Depends(get_current_user_id),
    service: CommentService = Depends(get_comment_service),
) -> IncidentCommentEntry:
    try:
        return await service.add_comment(
            report_id=report_id,
            author_id=user_id,
            content=payload.content,
            parent_id=payload.parent_id,
        )
    except (ValueError, DomainError) as exc:
        raise _handle_service_error(exc) from exc
