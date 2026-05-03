from datetime import datetime as dt
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from ...core.security import get_current_user_id
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
    IncidentReportReopenRequest,
    IncidentReportRejectRequest,
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
from ..service.form_schema import INCIDENT_REPORT_FORM_SCHEMA
from ..service.report import (
    add_comment_entry,
    approve_report,
    assign_handler,
    close_report,
    create_report,
    delete_report,
    get_report,
    list_audit_log_entries,
    list_comment_entries,
    list_incident_reports,
    reject_report,
    reopen_report,
    submit_report,
    update_report,
)

router = APIRouter(prefix="/api/incident-report", tags=["incident-report"])


def _handle_service_error(exc: ValueError) -> HTTPException:
    if isinstance(exc, PermissionDenied):
        return HTTPException(status_code=403, detail=str(exc))
    return HTTPException(status_code=400, detail=str(exc))


@router.get("/reports/schema")
async def get_report_form_schema() -> dict[str, Any]:
    return INCIDENT_REPORT_FORM_SCHEMA.model_dump()


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
) -> IncidentReportListResponse:
    sd = dt.fromisoformat(start_date) if start_date else None
    ed = dt.fromisoformat(end_date) if end_date else None
    return await list_incident_reports(
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
) -> IncidentReportDetail:
    try:
        report = await get_report(report_id, user_id=user_id)
    except ValueError as exc:
        raise _handle_service_error(exc) from exc
    if report is None:
        raise HTTPException(status_code=404, detail="报告不存在")
    return report


@router.post("/reports", response_model=IncidentReportDetail)
async def create_new_report(
    payload: IncidentReportCreateRequest,
    user_id: str = Depends(get_current_user_id),
) -> IncidentReportDetail:
    try:
        return await create_report(
            title=payload.title,
            reporter_id=user_id,
            severity=payload.severity,
            system=payload.system,
            site_id=payload.site_id,
            fault_date=payload.fault_date,
            form_data=payload.form_data,
        )
    except ValueError as exc:
        raise _handle_service_error(exc) from exc


@router.put("/reports/{report_id}", response_model=IncidentReportDetail)
async def update_existing_report(
    report_id: str,
    payload: IncidentReportUpdateRequest,
    user_id: str = Depends(get_current_user_id),
) -> IncidentReportDetail:
    fields = {k: v for k, v in payload.model_dump().items() if v is not None}
    try:
        result = await update_report(report_id=report_id, user_id=user_id, **fields)
    except ValueError as exc:
        raise _handle_service_error(exc) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="报告不存在")
    return result


@router.delete("/reports/{report_id}")
async def delete_report_by_id(
    report_id: str,
    user_id: str = Depends(get_current_user_id),
) -> dict[str, bool]:
    try:
        deleted = await delete_report(report_id=report_id, actor_id=user_id)
    except ValueError as exc:
        raise _handle_service_error(exc) from exc
    return {"deleted": deleted}


@router.post("/reports/{report_id}/submit", response_model=IncidentReportDetail)
async def submit_report_for_review(
    report_id: str,
    payload: IncidentReportSubmitRequest | None = None,
    user_id: str = Depends(get_current_user_id),
) -> IncidentReportDetail:
    comment = payload.comment if payload else None
    try:
        result = await submit_report(report_id=report_id, actor_id=user_id, comment=comment)
    except ValueError as exc:
        raise _handle_service_error(exc) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="报告不存在")
    return result


@router.post("/reports/{report_id}/approve", response_model=IncidentReportDetail)
async def approve_report_review(
    report_id: str,
    payload: IncidentReportApproveRequest,
    user_id: str = Depends(get_current_user_id),
) -> IncidentReportDetail:
    try:
        result = await approve_report(report_id=report_id, actor_id=user_id, comment=payload.comment)
    except ValueError as exc:
        raise _handle_service_error(exc) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="报告不存在")
    return result


@router.post("/reports/{report_id}/reject", response_model=IncidentReportDetail)
async def reject_report_review(
    report_id: str,
    payload: IncidentReportRejectRequest,
    user_id: str = Depends(get_current_user_id),
) -> IncidentReportDetail:
    try:
        result = await reject_report(report_id=report_id, actor_id=user_id, comment=payload.comment)
    except ValueError as exc:
        raise _handle_service_error(exc) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="报告不存在")
    return result


@router.post("/reports/{report_id}/assign", response_model=IncidentReportDetail)
async def assign_report_handler(
    report_id: str,
    payload: IncidentReportAssignRequest,
    user_id: str = Depends(get_current_user_id),
) -> IncidentReportDetail:
    try:
        result = await assign_handler(report_id=report_id, actor_id=user_id, assignee_id=payload.assignee_id)
    except ValueError as exc:
        raise _handle_service_error(exc) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="报告不存在")
    return result


@router.post("/reports/{report_id}/close", response_model=IncidentReportDetail)
async def close_report_by_handler(
    report_id: str,
    payload: IncidentReportCloseRequest | None = None,
    user_id: str = Depends(get_current_user_id),
) -> IncidentReportDetail:
    comment = payload.comment if payload else None
    try:
        result = await close_report(report_id=report_id, actor_id=user_id, comment=comment)
    except ValueError as exc:
        raise _handle_service_error(exc) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="报告不存在")
    return result


@router.post("/reports/{report_id}/reopen", response_model=IncidentReportDetail)
async def reopen_closed_report(
    report_id: str,
    payload: IncidentReportReopenRequest | None = None,
    user_id: str = Depends(get_current_user_id),
) -> IncidentReportDetail:
    comment = payload.comment if payload else None
    try:
        result = await reopen_report(report_id=report_id, actor_id=user_id, comment=comment)
    except ValueError as exc:
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
) -> IncidentBodyGenerateResponse:
    from ..service.generation import quick_generate_report_body as _quick_generate
    try:
        return await _quick_generate(
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
) -> IncidentBodyGenerateResponse:
    from ..service.generation import generate_report_body_section as _section_generate
    try:
        return await _section_generate(
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
) -> IncidentReportPreviewResponse:
    from ..service.preview import preview_report_attachment as _preview
    try:
        return await _preview(
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
) -> list[IncidentAuditLogEntry]:
    try:
        return await list_audit_log_entries(report_id, user_id=user_id)
    except ValueError as exc:
        raise _handle_service_error(exc) from exc


@router.get("/reports/{report_id}/comments", response_model=list[IncidentCommentEntry])
async def get_report_comments(
    report_id: str,
    user_id: str = Depends(get_current_user_id),
) -> list[IncidentCommentEntry]:
    try:
        return await list_comment_entries(report_id, user_id=user_id)
    except ValueError as exc:
        raise _handle_service_error(exc) from exc


@router.post("/reports/{report_id}/comments", response_model=IncidentCommentEntry)
async def add_report_comment(
    report_id: str,
    payload: IncidentCommentCreateRequest,
    user_id: str = Depends(get_current_user_id),
) -> IncidentCommentEntry:
    try:
        return await add_comment_entry(
            report_id=report_id,
            author_id=user_id,
            content=payload.content,
            parent_id=payload.parent_id,
        )
    except ValueError as exc:
        raise _handle_service_error(exc) from exc
