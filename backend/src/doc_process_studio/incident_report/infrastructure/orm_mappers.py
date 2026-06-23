"""ORM ↔ 聚合根映射器。

负责 IncidentReportORM 与 Report 聚合根之间的双向转换。
严格保持字段一一对应，不改变任何业务语义。
"""

from typing import cast

from ...shared.dtutils import to_utc8
from ..domain.report import Report
from ..domain.status import ReportStatus
from ..models.incident_report_orm import IncidentReport as IncidentReportORM
from ..schemas.common import IncidentReportStatus, IncidentSeverity
from ..schemas.response import (
    IncidentReportDetail,
    IncidentReportSummary,
)


def orm_to_report(orm: IncidentReportORM) -> Report:
    """ORM → 聚合根。"""
    return Report(
        id=orm.id,
        ref_no=orm.ref_no,
        title=orm.title,
        status=ReportStatus(orm.status),
        reporter_id=orm.reporter_id,
        assignee_id=orm.assignee_id,
        verifier_id=orm.verifier_id,
        severity=orm.severity,
        system=orm.system,
        site_id=orm.site_id,
        fault_date=orm.fault_date,
        resolution_date=orm.resolution_date,
        form_data=orm.form_data or {},
        report_data=orm.report_data,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
        submitted_at=orm.submitted_at,
        approved_at=orm.approved_at,
        closed_at=orm.closed_at,
    )


def apply_report_to_orm(report: Report, orm: IncidentReportORM) -> None:
    """将聚合根状态同步到已存在的 ORM 对象（用于 update）。"""
    orm.title = report.title
    orm.status = report.status.value
    orm.severity = report.severity
    orm.assignee_id = report.assignee_id
    orm.verifier_id = report.verifier_id
    orm.system = report.system
    orm.site_id = report.site_id
    orm.fault_date = report.fault_date
    orm.resolution_date = report.resolution_date
    orm.form_data = report.form_data
    orm.report_data = report.report_data
    orm.submitted_at = report.submitted_at
    orm.approved_at = report.approved_at
    orm.closed_at = report.closed_at
    orm.updated_at = report.updated_at


def build_orm_from_report(report: Report) -> IncidentReportORM:
    """从聚合根构建新的 ORM 对象（用于 add）。"""
    return IncidentReportORM(
        id=report.id,
        ref_no=report.ref_no,
        title=report.title,
        status=report.status.value,
        severity=report.severity,
        reporter_id=report.reporter_id,
        assignee_id=report.assignee_id,
        verifier_id=report.verifier_id,
        system=report.system,
        site_id=report.site_id,
        fault_date=report.fault_date,
        resolution_date=report.resolution_date,
        form_data=report.form_data,
        report_data=report.report_data,
        created_at=report.created_at,
        updated_at=report.updated_at,
        submitted_at=report.submitted_at,
        approved_at=report.approved_at,
        closed_at=report.closed_at,
    )


async def orm_to_summary(
    orm: IncidentReportORM,
    usernames: dict[str, str],
) -> IncidentReportSummary:
    """ORM → 摘要 DTO（需外部传入已解析的用户名映射）。"""
    return IncidentReportSummary(
        id=orm.id,
        ref_no=orm.ref_no,
        title=orm.title,
        status=cast(IncidentReportStatus, orm.status),
        severity=cast(IncidentSeverity | None, orm.severity),
        reporter_id=orm.reporter_id,
        reporter_name=usernames.get(orm.reporter_id),
        assignee_id=orm.assignee_id,
        assignee_name=usernames.get(orm.assignee_id) if orm.assignee_id else None,
        verifier_id=orm.verifier_id,
        verifier_name=usernames.get(orm.verifier_id) if orm.verifier_id else None,
        fault_date=to_utc8(orm.fault_date),
        created_at=to_utc8(orm.created_at),
        updated_at=to_utc8(orm.updated_at),
    )


async def orm_to_detail(
    orm: IncidentReportORM,
    usernames: dict[str, str],
) -> IncidentReportDetail:
    """ORM → 详情 DTO（需外部传入已解析的用户名映射）。"""
    summary = await orm_to_summary(orm, usernames)
    return IncidentReportDetail(
        **summary.model_dump(),
        system=orm.system,
        site_id=orm.site_id,
        form_data=orm.form_data or {},
        report_data=orm.report_data,
        submitted_at=to_utc8(orm.submitted_at),
        approved_at=to_utc8(orm.approved_at),
        closed_at=to_utc8(orm.closed_at),
        resolution_date=to_utc8(orm.resolution_date),
    )
