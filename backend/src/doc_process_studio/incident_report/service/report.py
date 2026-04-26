from datetime import datetime
from uuid import uuid4

from ...shared.dtutils import utcnow
from ..models.incident_report_orm import IncidentReport as IncidentReportORM
from ..schemas.common import STATUS_TRANSITIONS, VALID_STATUSES
from ..schemas.response import IncidentReportDetail, IncidentReportListResponse, IncidentReportSummary
from ..service.audit_log import create_audit_log
from ..service.report_store import (
    _CLEAR_SENTINEL,
    create_report_record,
    delete_report_record,
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
) -> IncidentReportDetail:
    report_id = uuid4().hex[:32]
    ref_no = await generate_ref_no()
    record = await create_report_record(
        report_id=report_id,
        ref_no=ref_no,
        title=title,
        reporter_id=reporter_id,
        severity=severity,
        system=system,
        site_id=site_id,
        fault_date=fault_date,
        form_data=form_data,
    )
    await create_audit_log(
        report_id=report_id,
        action="create",
        actor_id=reporter_id,
        to_status="draft",
    )
    return orm_to_detail(record)


async def get_report(report_id: str) -> IncidentReportDetail | None:
    record = await load_report_orm(report_id)
    if record is None:
        return None
    return orm_to_detail(record)


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
        from .role import has_incident_role
        if not await has_incident_role(user_id, "admin"):
            raise ValueError("只有报告人或管理员可以编辑报告")
    updated = await update_report_record(report_id, **fields)
    if updated is None:
        return None
    return orm_to_detail(updated)


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
    items = [orm_to_summary(r) for r in records]
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
        from .role import has_incident_role
        if not await has_incident_role(actor_id, "admin"):
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
    return orm_to_detail(updated)


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
    return orm_to_detail(updated)


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
    return orm_to_detail(updated)


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
    await create_audit_log(
        report_id=report_id,
        action="assign",
        actor_id=actor_id,
        from_status=record.status,
        to_status=new_status,
        comment=f"分配处理人: {assignee_id}",
    )
    return orm_to_detail(updated)


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
        from .role import has_incident_role
        if not await has_incident_role(actor_id, "admin"):
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
    return orm_to_detail(updated)


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
    return orm_to_detail(updated)


async def delete_report(
    *,
    report_id: str,
    actor_id: str | None = None,
) -> bool:
    if actor_id:
        await create_audit_log(
            report_id=report_id,
            action="delete",
            actor_id=actor_id,
            from_status=None,
            to_status=None,
            comment="报告已删除",
        )
    return await delete_report_record(report_id)
