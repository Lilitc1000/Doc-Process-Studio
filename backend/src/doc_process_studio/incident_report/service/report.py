import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import delete

from ...core.database import async_session_factory
from ...shared.dtutils import to_utc8, utcnow
from ..models.audit_log import IncidentAuditLog
from ..models.incident_report_orm import IncidentComment, IncidentReport as IncidentReportORM
from ..schemas.common import PermissionDenied
from ..schemas.response import IncidentAuditLogEntry, IncidentCommentEntry, IncidentReportDetail, IncidentReportListResponse
from ..service.audit_log import create_audit_log
from ..service.report_store import (
    _CLEAR_SENTINEL,
    _resolve_usernames_safe,
    create_comment_record,
    create_report_record,
    list_comment_records,
    list_reports,
    load_report_orm,
    orm_to_detail,
    orm_to_summary,
    update_report_record,
)
from .audit_log import list_audit_logs, orm_to_entry as audit_orm_to_entry
from .form_validation import validate_form_data_for_submit
from .role import has_permission

logger = logging.getLogger(__name__)


async def create_report(
    *,
    title: str,
    reporter_id: str,
    severity: str | None = None,
    system: str | None = None,
    site_id: str | None = None,
    fault_date: datetime | None = None,
    form_data: dict | None = None,
    ref_no: str | None = None,
) -> IncidentReportDetail:
    if not await has_permission(reporter_id, "report:create"):
        raise PermissionDenied("需要报告人权限才能创建报告")

    manual_ref_no = None
    if form_data and isinstance(form_data, dict):
        manual_ref_no = form_data.get("manual_reference_no") or None
    effective_ref_no = ref_no or manual_ref_no or None

    record = await create_report_record(
        report_id=uuid4().hex[:32],
        ref_no=effective_ref_no,
        title=title,
        reporter_id=reporter_id,
        severity=severity,
        system=system,
        site_id=site_id,
        fault_date=fault_date,
        form_data=form_data,
    )
    if record is None:
        raise RuntimeError("Failed to create report after retries")
    await create_audit_log(
        report_id=record.id,
        action="create",
        actor_id=reporter_id,
        to_status="draft",
    )
    return await orm_to_detail(record)


async def get_report(report_id: str, user_id: str | None = None) -> IncidentReportDetail | None:
    record = await load_report_orm(report_id)
    if record is None:
        return None
    if user_id and not await has_permission(user_id, "report:view_all"):
        if record.reporter_id != user_id and record.assignee_id != user_id and record.verifier_id != user_id:
            raise PermissionDenied("无权查看此报告")
    return await orm_to_detail(record)


async def update_report(
    *,
    report_id: str,
    user_id: str,
    **fields: Any,
) -> IncidentReportDetail | None:
    record = await load_report_orm(report_id)
    if record is None:
        return None
    if record.status not in ("draft", "rejected"):
        raise ValueError(f"当前状态 {record.status} 不允许编辑")
    can_edit = (
        (record.reporter_id == user_id and await has_permission(user_id, "report:edit_own"))
        or (record.assignee_id == user_id and await has_permission(user_id, "report:edit_assigned"))
        or await has_permission(user_id, "report:edit_all")
    )
    if not can_edit:
        raise PermissionDenied("无权编辑此报告")
    updated = await update_report_record(report_id, **fields)
    if updated is None:
        return None
    return await orm_to_detail(updated)


async def list_incident_reports(
    *,
    user_id: str | None = None,
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    severity: str | None = None,
    search: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> IncidentReportListResponse:
    reporter_id_filter = None
    if user_id and not await has_permission(user_id, "report:view_all"):
        reporter_id_filter = user_id
    records, total = await list_reports(
        page=page,
        page_size=page_size,
        status=status,
        severity=severity,
        search=search,
        start_date=start_date,
        end_date=end_date,
        reporter_id=reporter_id_filter,
    )
    items = []
    for r in records:
        items.append(await orm_to_summary(r))
    return IncidentReportListResponse(total=total, items=items)


async def submit_report(
    *,
    report_id: str,
    actor_id: str,
    comment: str | None = None,
) -> IncidentReportDetail | None:
    if not await has_permission(actor_id, "report:submit"):
        raise PermissionDenied("需要报告人权限才能提交审核")
    record = await load_report_orm(report_id)
    if record is None:
        return None
    if record.status not in ("draft", "rejected"):
        raise ValueError(f"当前状态 {record.status} 不允许提交审核")
    form_data = record.form_data or {}
    missing = validate_form_data_for_submit(form_data)
    if missing:
        raise ValueError(f"缺少必填字段: {', '.join(missing)}")
    now = utcnow()
    updated = await update_report_record(
        report_id,
        status="pending",
        submitted_at=now,
        updated_at=now,
    )
    if updated is None:
        return None
    await create_audit_log(
        report_id=report_id,
        action="submit",
        actor_id=actor_id,
        from_status=record.status,
        to_status="pending",
        comment=comment,
    )
    return await orm_to_detail(updated)


async def approve_report(
    *,
    report_id: str,
    actor_id: str,
    comment: str | None = None,
) -> IncidentReportDetail | None:
    if not await has_permission(actor_id, "report:audit"):
        raise PermissionDenied("需要审核人权限才能批准报告")
    record = await load_report_orm(report_id)
    if record is None:
        return None
    if record.status != "pending":
        raise ValueError(f"当前状态 {record.status} 不允许审核通过")
    now = utcnow()
    updated = await update_report_record(
        report_id,
        status="approved",
        verifier_id=actor_id,
        approved_at=now,
        updated_at=now,
    )
    if updated is None:
        return None
    await create_audit_log(
        report_id=report_id,
        action="approve",
        actor_id=actor_id,
        from_status="pending",
        to_status="approved",
        comment=comment,
    )
    return await orm_to_detail(updated)


async def reject_report(
    *,
    report_id: str,
    actor_id: str,
    comment: str,
) -> IncidentReportDetail | None:
    if not await has_permission(actor_id, "report:audit"):
        raise PermissionDenied("需要审核人权限才能驳回报告")
    record = await load_report_orm(report_id)
    if record is None:
        return None
    if record.status != "pending":
        raise ValueError(f"当前状态 {record.status} 不允许驳回")
    now = utcnow()
    updated = await update_report_record(
        report_id,
        status="rejected",
        verifier_id=actor_id,
        updated_at=now,
    )
    if updated is None:
        return None
    await create_audit_log(
        report_id=report_id,
        action="reject",
        actor_id=actor_id,
        from_status="pending",
        to_status="rejected",
        comment=comment,
    )
    return await orm_to_detail(updated)


async def assign_handler(
    *,
    report_id: str,
    actor_id: str,
    assignee_id: str,
) -> IncidentReportDetail | None:
    if not await has_permission(actor_id, "report:assign"):
        raise PermissionDenied("需要审核人权限才能分配处理人")
    record = await load_report_orm(report_id)
    if record is None:
        return None
    if record.status not in ("approved", "in_progress"):
        raise ValueError(f"当前状态 {record.status} 不允许分配处理人")
    now = utcnow()
    new_status = "in_progress" if record.status == "approved" else record.status
    updated = await update_report_record(
        report_id,
        status=new_status,
        assignee_id=assignee_id,
        updated_at=now,
    )
    if updated is None:
        return None
    assignee_names = await _resolve_usernames_safe({assignee_id})
    assignee_display = assignee_names.get(assignee_id, assignee_id)
    await create_audit_log(
        report_id=report_id,
        action="assign",
        actor_id=actor_id,
        from_status=record.status,
        to_status=new_status,
        comment=f"分配处理人: {assignee_display}",
    )
    return await orm_to_detail(updated)


async def close_report(
    *,
    report_id: str,
    actor_id: str,
    comment: str | None = None,
) -> IncidentReportDetail | None:
    if not await has_permission(actor_id, "report:close_assigned"):
        raise PermissionDenied("需要处理人权限才能关闭报告")
    record = await load_report_orm(report_id)
    if record is None:
        return None
    if record.status != "in_progress":
        raise ValueError(f"当前状态 {record.status} 不允许关闭")
    now = utcnow()
    updated = await update_report_record(
        report_id,
        status="closed",
        closed_at=now,
        resolution_date=now,
        updated_at=now,
    )
    if updated is None:
        return None
    await create_audit_log(
        report_id=report_id,
        action="close",
        actor_id=actor_id,
        from_status="in_progress",
        to_status="closed",
        comment=comment,
    )
    return await orm_to_detail(updated)


async def reopen_report(
    *,
    report_id: str,
    actor_id: str,
    comment: str | None = None,
) -> IncidentReportDetail | None:
    if not await has_permission(actor_id, "report:reopen"):
        raise PermissionDenied("需要管理员权限才能重新打开报告")
    record = await load_report_orm(report_id)
    if record is None:
        return None
    if record.status != "closed":
        raise ValueError(f"当前状态 {record.status} 不允许重新打开")
    now = utcnow()
    updated = await update_report_record(
        report_id,
        status="draft",
        closed_at=_CLEAR_SENTINEL,
        updated_at=now,
    )
    if updated is None:
        return None
    await create_audit_log(
        report_id=report_id,
        action="reopen",
        actor_id=actor_id,
        from_status="closed",
        to_status="draft",
        comment=comment,
    )
    return await orm_to_detail(updated)


async def delete_report(
    *,
    report_id: str,
    actor_id: str | None = None,
) -> bool:
    if actor_id and not await has_permission(actor_id, "report:delete"):
        raise PermissionDenied("需要管理员权限才能删除报告")
    async with async_session_factory() as session:
        record = await session.get(IncidentReportORM, report_id)
        if record is None:
            return False

        await session.execute(
            delete(IncidentComment).where(
                IncidentComment.report_id == report_id
            )
        )
        await session.execute(
            delete(IncidentAuditLog).where(
                IncidentAuditLog.report_id == report_id
            )
        )
        await session.delete(record)
        await session.commit()
    return True


async def list_audit_log_entries(report_id: str, user_id: str | None = None) -> list[IncidentAuditLogEntry]:
    record = await load_report_orm(report_id)
    if record is None:
        return []
    if user_id and not await has_permission(user_id, "report:view_all"):
        if record.reporter_id != user_id and record.assignee_id != user_id and record.verifier_id != user_id:
            raise PermissionDenied("无权查看此报告的审计日志")
    records = await list_audit_logs(report_id)
    actor_ids = {r.actor_id for r in records if r.actor_id}
    usernames = await _resolve_usernames_safe(actor_ids)
    return [audit_orm_to_entry(r, actor_name=usernames.get(r.actor_id)) for r in records]


async def list_comment_entries(report_id: str, user_id: str | None = None) -> list[IncidentCommentEntry]:
    record = await load_report_orm(report_id)
    if record is None:
        return []
    if user_id and not await has_permission(user_id, "report:view_all"):
        if record.reporter_id != user_id and record.assignee_id != user_id and record.verifier_id != user_id:
            raise PermissionDenied("无权查看此报告的评论")
    records = await list_comment_records(report_id)
    author_ids = {r.author_id for r in records if r.author_id}
    usernames = await _resolve_usernames_safe(author_ids)
    return [
        IncidentCommentEntry(
            id=r.id,
            report_id=r.report_id,
            author_id=r.author_id,
            author_name=usernames.get(r.author_id),
            content=r.content,
            parent_id=r.parent_id,
            created_at=to_utc8(r.created_at),
        )
        for r in records
    ]


async def add_comment_entry(
    *,
    report_id: str,
    author_id: str,
    content: str,
    parent_id: str | None = None,
) -> IncidentCommentEntry:
    report_record = await load_report_orm(report_id)
    if report_record is None:
        raise ValueError(f"报告 {report_id} 不存在")
    if not await has_permission(author_id, "report:view"):
        raise PermissionDenied("无权对此报告添加评论")

    comment_id = uuid4().hex[:32]
    record = await create_comment_record(
        comment_id=comment_id,
        report_id=report_id,
        author_id=author_id,
        content=content,
        parent_id=parent_id,
    )
    return IncidentCommentEntry(
        id=record.id,
        report_id=record.report_id,
        author_id=record.author_id,
        author_name=(await _resolve_usernames_safe({record.author_id})).get(record.author_id),
        content=record.content,
        parent_id=record.parent_id,
        created_at=to_utc8(record.created_at),
    )
