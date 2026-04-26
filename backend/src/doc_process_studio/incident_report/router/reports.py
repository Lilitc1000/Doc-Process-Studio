from datetime import datetime as dt
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query

from ...core.security import get_current_user_id
from ..schemas.request import (
    IncidentCommentCreateRequest,
    IncidentReportApproveRequest,
    IncidentReportAssignRequest,
    IncidentReportCloseRequest,
    IncidentReportCreateRequest,
    IncidentReportReopenRequest,
    IncidentReportRejectRequest,
    IncidentReportSubmitRequest,
    IncidentReportUpdateRequest,
)
from ..schemas.response import (
    IncidentAuditLogEntry,
    IncidentCommentEntry,
    IncidentReportDetail,
    IncidentReportListResponse,
)
from ..service.audit_log import list_audit_logs, orm_to_entry as audit_orm_to_entry
from ..service.report import (
    approve_report,
    assign_handler,
    close_report,
    create_report,
    delete_report,
    get_report,
    list_incident_reports,
    reject_report,
    reopen_report,
    submit_report,
    update_report,
)
from ..service.report_store import create_comment_record, list_comment_records
from ..service.role import get_user_incident_roles, has_incident_role
from .dependencies import require_admin, require_verifier_or_admin

router = APIRouter(prefix="/api/incident-report", tags=["incident-report"])


@router.get("/reports/schema")
async def get_report_form_schema():
    from ..service.form_schema import INCIDENT_REPORT_FORM_SCHEMA
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
    report = await get_report(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="报告不存在")
    return report


@router.post("/reports", response_model=IncidentReportDetail)
async def create_new_report(
    payload: IncidentReportCreateRequest,
    user_id: str = Depends(get_current_user_id),
) -> IncidentReportDetail:
    can_create = await has_incident_role(user_id, "reporter") or await has_incident_role(user_id, "admin")
    if not can_create:
        roles = await get_user_incident_roles(user_id)
        can_create = bool(roles.intersection({"reporter", "handler", "verifier", "admin"}))
    if not can_create:
        raise HTTPException(status_code=403, detail="需要报告人权限才能创建报告")
    return await create_report(
        title=payload.title,
        reporter_id=user_id,
        severity=payload.severity,
        system=payload.system,
        site_id=payload.site_id,
        fault_date=payload.fault_date,
        form_data=payload.form_data,
    )


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
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="报告不存在")
    return result


@router.delete("/reports/{report_id}")
async def delete_report_by_id(
    report_id: str,
    user_id: str = Depends(require_admin),
) -> dict[str, bool]:
    deleted = await delete_report(report_id=report_id, actor_id=user_id)
    return {"deleted": deleted}


@router.post("/reports/{report_id}/submit", response_model=IncidentReportDetail)
async def submit_report_for_review(
    report_id: str,
    payload: IncidentReportSubmitRequest | None = None,
    user_id: str = Depends(get_current_user_id),
) -> IncidentReportDetail:
    from ..service.form_validation import validate_form_data_for_submit
    from ..service.report_store import load_report_orm
    record = await load_report_orm(report_id)
    if record is None:
        raise HTTPException(status_code=404, detail="报告不存在")
    form_data = record.form_data or {}
    missing = validate_form_data_for_submit(form_data)
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"缺少必填字段: {', '.join(missing)}",
        )
    comment = payload.comment if payload else None
    try:
        result = await submit_report(report_id=report_id, actor_id=user_id, comment=comment)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="报告不存在")
    return result


@router.post("/reports/{report_id}/approve", response_model=IncidentReportDetail)
async def approve_report_review(
    report_id: str,
    payload: IncidentReportApproveRequest,
    user_id: str = Depends(require_verifier_or_admin),
) -> IncidentReportDetail:
    try:
        result = await approve_report(report_id=report_id, actor_id=user_id, comment=payload.comment)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="报告不存在")
    return result


@router.post("/reports/{report_id}/reject", response_model=IncidentReportDetail)
async def reject_report_review(
    report_id: str,
    payload: IncidentReportRejectRequest,
    user_id: str = Depends(require_verifier_or_admin),
) -> IncidentReportDetail:
    try:
        result = await reject_report(report_id=report_id, actor_id=user_id, comment=payload.comment)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="报告不存在")
    return result


@router.post("/reports/{report_id}/assign", response_model=IncidentReportDetail)
async def assign_report_handler(
    report_id: str,
    payload: IncidentReportAssignRequest,
    user_id: str = Depends(require_verifier_or_admin),
) -> IncidentReportDetail:
    try:
        result = await assign_handler(report_id=report_id, actor_id=user_id, assignee_id=payload.assignee_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="报告不存在")
    return result


@router.post("/reports/{report_id}/reopen", response_model=IncidentReportDetail)
async def reopen_closed_report(
    report_id: str,
    payload: IncidentReportReopenRequest | None = None,
    user_id: str = Depends(require_admin),
) -> IncidentReportDetail:
    comment = payload.comment if payload else None
    try:
        result = await reopen_report(report_id=report_id, actor_id=user_id, comment=comment)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="报告不存在")
    return result


@router.get("/reports/{report_id}/audit-logs", response_model=list[IncidentAuditLogEntry])
async def get_report_audit_logs(
    report_id: str,
    user_id: str = Depends(get_current_user_id),
) -> list[IncidentAuditLogEntry]:
    records = await list_audit_logs(report_id)
    return [audit_orm_to_entry(r) for r in records]


@router.get("/reports/{report_id}/comments", response_model=list[IncidentCommentEntry])
async def get_report_comments(
    report_id: str,
    user_id: str = Depends(get_current_user_id),
) -> list[IncidentCommentEntry]:
    records = await list_comment_records(report_id)
    return [
        IncidentCommentEntry(
            id=r.id,
            report_id=r.report_id,
            author_id=r.author_id,
            author_name=None,
            content=r.content,
            parent_id=r.parent_id,
            created_at=r.created_at,
        )
        for r in records
    ]


@router.post("/reports/{report_id}/comments", response_model=IncidentCommentEntry)
async def add_report_comment(
    report_id: str,
    payload: IncidentCommentCreateRequest,
    user_id: str = Depends(get_current_user_id),
) -> IncidentCommentEntry:
    comment_id = uuid4().hex[:32]
    record = await create_comment_record(
        comment_id=comment_id,
        report_id=report_id,
        author_id=user_id,
        content=payload.content,
        parent_id=payload.parent_id,
    )
    return IncidentCommentEntry(
        id=record.id,
        report_id=record.report_id,
        author_id=record.author_id,
        author_name=None,
        content=record.content,
        parent_id=record.parent_id,
        created_at=record.created_at,
    )
