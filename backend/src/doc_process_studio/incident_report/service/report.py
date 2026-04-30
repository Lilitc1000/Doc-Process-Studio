import logging
from datetime import datetime
from uuid import uuid4

from sqlalchemy import delete

logger = logging.getLogger(__name__)

from ...core.database import async_session_factory
from ...shared.dtutils import utcnow
from ..models.audit_log import IncidentAuditLog
from ..models.incident_report_orm import IncidentReport as IncidentReportORM
from ..schemas.common import STATUS_TRANSITIONS, VALID_STATUSES
from ..schemas.response import IncidentReportDetail, IncidentReportListResponse, IncidentReportSummary
from ..service.audit_log import create_audit_log
from ..service.report_store import (
    _CLEAR_SENTINEL,
    _REF_NO_RETRY_MAX,
    _resolve_usernames_safe,
    generate_ref_no,
    list_reports,
    load_report_orm,
    orm_to_detail,
    orm_to_summary,
    update_report_record,
)


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
    from sqlalchemy.exc import IntegrityError as SAIntegrityError

    report_id = uuid4().hex[:32]
    manual_ref_no = None
    if form_data and isinstance(form_data, dict):
        manual_ref_no = form_data.get("manual_reference_no") or None
    effective_ref_no = ref_no or manual_ref_no or None

    now = utcnow()
    for attempt in range(_REF_NO_RETRY_MAX + 1):
        if effective_ref_no is None:
            effective_ref_no = await generate_ref_no()
            if attempt > 0:
                import random
                effective_ref_no = f"DAS-{random.randint(1, 99999):05d}"
        record = IncidentReportORM(
            id=report_id,
            ref_no=effective_ref_no,
            title=title,
            status="draft",
            severity=severity,
            reporter_id=reporter_id,
            system=system,
            site_id=site_id,
            fault_date=fault_date,
            form_data=form_data or {},
            created_at=now,
            updated_at=now,
        )
        audit_record = IncidentAuditLog(
            id=uuid4().hex[:32],
            report_id=report_id,
            action="create",
            actor_id=reporter_id,
            to_status="draft",
            created_at=now,
        )
        async with async_session_factory() as session:
            session.add(record)
            try:
                await session.flush()
            except SAIntegrityError:
                await session.rollback()
                if ref_no is not None:
                    raise
                effective_ref_no = None
                continue
            session.add(audit_record)
            try:
                await session.commit()
                await session.refresh(record)
                return await orm_to_detail(record)
            except SAIntegrityError as e:
                await session.rollback()
                logger.warning("IntegrityError in audit log (attempt %d): %s", attempt, e)
                if ref_no is not None:
                    raise
                effective_ref_no = None
    raise RuntimeError(f"Failed to create report after {_REF_NO_RETRY_MAX + 1} attempts")


async def get_report(report_id: str) -> IncidentReportDetail | None:
    record = await load_report_orm(report_id)
    if record is None:
        return None
    return await orm_to_detail(record)


async def update_report(
    *,
    report_id: str,
    user_id: str,
    **fields,
) -> IncidentReportDetail | None:
    record = await load_report_orm(report_id)
    if record is None:
        return None
    if record.status not in ("draft", "rejected"):
        raise ValueError(f"当前状态 {record.status} 不允许编辑")
    if record.reporter_id != user_id:
        from .role import has_permission
        if not await has_permission(user_id, "report:edit_assigned") and not await has_permission(user_id, "report:delete"):
            raise ValueError("只有报告人、被指派处理人或管理员可以编辑报告")
    updated = await update_report_record(report_id, **fields)
    if updated is None:
        return None
    return await orm_to_detail(updated)


async def list_incident_reports(
    *,
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    severity: str | None = None,
    search: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> IncidentReportListResponse:
    records, total = await list_reports(
        page=page,
        page_size=page_size,
        status=status,
        severity=severity,
        search=search,
        start_date=start_date,
        end_date=end_date,
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
    record = await load_report_orm(report_id)
    if record is None:
        return None
    if record.status not in ("draft", "rejected"):
        raise ValueError(f"当前状态 {record.status} 不允许提交审核")
    if record.reporter_id != actor_id:
        from .role import has_permission
        if not await has_permission(actor_id, "report:delete"):
            raise ValueError("只有报告人或管理员可以提交审核")
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
    record = await load_report_orm(report_id)
    if record is None:
        return None
    if record.status != "in_progress":
        raise ValueError(f"当前状态 {record.status} 不允许关闭")
    if record.assignee_id != actor_id:
        from .role import has_permission
        if not await has_permission(actor_id, "report:delete"):
            raise ValueError("只有处理人或管理员可以关闭报告")
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
    from ..models.audit_log import IncidentAuditLog
    from ..models.incident_report_orm import IncidentComment

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
