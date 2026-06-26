"""报告应用服务。

用例编排：load → 权限校验 → 调聚合根方法 → 持久化 → 发事件 → 转 DTO。
"""

from datetime import datetime
from typing import Any
from uuid import uuid4

from ....common.utils.dtutils import to_utc8
from ...domain.entities.report import Report
from ...domain.values.errors import (
    PermissionDeniedError,
    ReportNotFoundError,
)
from ...domain.values.permission import Permission
from ..commands import (
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
from ..dtos import (
    IncidentReportDetail,
    IncidentReportListResponse,
)
from ..ports import (
    AuditEventSink,
    PermissionChecker,
    RefNoGenerator,
    ReportRepository,
    UserDirectory,
)


class ReportApplicationService:
    """报告应用服务，编排报告全生命周期用例。"""

    def __init__(
        self,
        repo: ReportRepository,
        checker: PermissionChecker,
        audit_sink: AuditEventSink,
        user_dir: UserDirectory,
        ref_no_gen: RefNoGenerator,
    ) -> None:
        self._repo = repo
        self._checker = checker
        self._audit = audit_sink
        self._users = user_dir
        self._ref_no_gen = ref_no_gen

    # ---- 表单 Schema ----
    @staticmethod
    def get_form_schema() -> dict[str, Any]:
        """返回事故报告表单 Schema（4 步骤结构）。"""
        from ...domain.values.form_schema import INCIDENT_REPORT_FORM_SCHEMA

        return INCIDENT_REPORT_FORM_SCHEMA.model_dump()

    # ---- 创建 ----
    async def create(self, cmd: CreateReportCommand) -> IncidentReportDetail:
        await self._checker.require(cmd.reporter_id, Permission.REPORT_CREATE)

        # ref_no 选取优先级：传入参数 > form_data.manual_reference_no > 自动生成
        effective_ref_no = cmd.ref_no
        if effective_ref_no is None and cmd.form_data and isinstance(cmd.form_data, dict):
            effective_ref_no = cmd.form_data.get("manual_reference_no") or None
        if effective_ref_no is None:
            effective_ref_no = await self._ref_no_gen.next()

        report = Report.create(
            report_id=uuid4().hex[:32],
            ref_no=effective_ref_no,
            title=cmd.title,
            reporter_id=cmd.reporter_id,
            severity=cmd.severity,
            system=cmd.system,
            site_id=cmd.site_id,
            fault_date=cmd.fault_date,
            form_data=cmd.form_data,
        )
        saved = await self._repo.add(report)
        await self._audit.flush(report.consume_events())
        return await self._to_detail(saved)

    # ---- 查询 ----
    async def get(self, report_id: str, user_id: str | None = None) -> IncidentReportDetail | None:
        report = await self._repo.get(report_id)
        if report is None:
            return None
        if user_id:
            perms = await self._checker.permissions_of(user_id)
            if not report.is_visible_to(user_id, perms):
                raise PermissionDeniedError("无权查看此报告")
        return await self._to_detail(report)

    async def list(
        self,
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
        # 无 report:view_all 权限时只返回自己参与的报告
        reporter_id_filter = None
        if user_id:
            perms = await self._checker.permissions_of(user_id)
            if Permission.REPORT_VIEW_ALL not in perms:
                reporter_id_filter = user_id
        items, total = await self._repo.list(
            page=page,
            page_size=page_size,
            status=status,
            severity=severity,
            search=search,
            start_date=start_date,
            end_date=end_date,
            reporter_id_filter=reporter_id_filter,
        )
        return IncidentReportListResponse(total=total, items=items)

    # ---- 更新 ----
    async def update(self, cmd: UpdateReportCommand) -> IncidentReportDetail | None:
        report = await self._repo.get(cmd.report_id)
        if report is None:
            return None
        perms = await self._checker.permissions_of(cmd.actor_id)
        if not report.can_be_edited_by(cmd.actor_id, perms):
            raise PermissionDeniedError("无权编辑此报告")
        report.update_fields(**cmd.fields)
        updated = await self._repo.update(report)
        if updated is None:
            return None
        return await self._to_detail(updated)

    # ---- 删除 ----
    async def delete(self, cmd: DeleteReportCommand) -> bool:
        if cmd.actor_id:
            await self._checker.require(cmd.actor_id, Permission.REPORT_DELETE)
        return await self._repo.delete(cmd.report_id)

    # ---- 状态流转 ----
    async def submit(self, cmd: SubmitReportCommand) -> IncidentReportDetail | None:
        report = await self._load_or_none(cmd.report_id)
        if report is None:
            return None
        await self._checker.require(cmd.actor_id, Permission.REPORT_SUBMIT)
        report.submit(actor_id=cmd.actor_id, comment=cmd.comment)
        return await self._persist_and_return(report)

    async def approve(self, cmd: ApproveReportCommand) -> IncidentReportDetail | None:
        report = await self._load_or_none(cmd.report_id)
        if report is None:
            return None
        await self._checker.require(cmd.actor_id, Permission.REPORT_AUDIT)
        report.approve(actor_id=cmd.actor_id, comment=cmd.comment)
        return await self._persist_and_return(report)

    async def reject(self, cmd: RejectReportCommand) -> IncidentReportDetail | None:
        report = await self._load_or_none(cmd.report_id)
        if report is None:
            return None
        await self._checker.require(cmd.actor_id, Permission.REPORT_AUDIT)
        report.reject(actor_id=cmd.actor_id, comment=cmd.comment)
        return await self._persist_and_return(report)

    async def assign_handler(self, cmd: AssignHandlerCommand) -> IncidentReportDetail | None:
        report = await self._load_or_none(cmd.report_id)
        if report is None:
            return None
        await self._checker.require(cmd.actor_id, Permission.REPORT_ASSIGN)
        report.assign_handler(
            actor_id=cmd.actor_id,
            assignee_id=cmd.assignee_id,
        )
        return await self._persist_and_return(report)

    async def close(self, cmd: CloseReportCommand) -> IncidentReportDetail | None:
        report = await self._load_or_none(cmd.report_id)
        if report is None:
            return None
        await self._checker.require(cmd.actor_id, Permission.REPORT_CLOSE_ASSIGNED)
        report.close(actor_id=cmd.actor_id, comment=cmd.comment)
        return await self._persist_and_return(report)

    async def reopen(self, cmd: ReopenReportCommand) -> IncidentReportDetail | None:
        report = await self._load_or_none(cmd.report_id)
        if report is None:
            return None
        await self._checker.require(cmd.actor_id, Permission.REPORT_REOPEN)
        report.reopen(actor_id=cmd.actor_id, comment=cmd.comment)
        return await self._persist_and_return(report)

    # ---- 私有 ----
    async def _load_or_none(self, report_id: str) -> Report | None:
        return await self._repo.get(report_id)

    async def _persist_and_return(self, report: Report) -> IncidentReportDetail:
        saved = await self._repo.update(report)
        if saved is None:
            raise ReportNotFoundError(report.id)
        await self._audit.flush(report.consume_events())
        return await self._to_detail(saved)

    async def _to_detail(self, report: Report) -> IncidentReportDetail:
        """聚合根 → IncidentReportDetail DTO。"""
        user_ids = {uid for uid in (report.reporter_id, report.assignee_id, report.verifier_id) if uid}
        usernames = await self._users.resolve_usernames(user_ids)
        return IncidentReportDetail(
            id=report.id,
            ref_no=report.ref_no,
            title=report.title,
            status=report.status.value,
            severity=report.severity,
            reporter_id=report.reporter_id,
            reporter_name=usernames.get(report.reporter_id),
            assignee_id=report.assignee_id,
            assignee_name=usernames.get(report.assignee_id) if report.assignee_id else None,
            verifier_id=report.verifier_id,
            verifier_name=usernames.get(report.verifier_id) if report.verifier_id else None,
            fault_date=to_utc8(report.fault_date),
            created_at=to_utc8(report.created_at),
            updated_at=to_utc8(report.updated_at),
            system=report.system,
            site_id=report.site_id,
            form_data=report.form_data,
            report_data=report.report_data,
            submitted_at=to_utc8(report.submitted_at),
            approved_at=to_utc8(report.approved_at),
            closed_at=to_utc8(report.closed_at),
            resolution_date=to_utc8(report.resolution_date),
        )
