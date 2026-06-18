"""审计日志查询应用服务。

提供报告审计日志的列表查询用例。
"""

from ..application.ports import (
    AuditLogRepository,
    PermissionChecker,
    ReportRepository,
    UserDirectory,
)
from ..domain.permission import Permission
from ..domain.report import Report
from ..schemas.response import IncidentAuditLogEntry


class AuditQueryService:
    """审计日志查询用例。"""

    def __init__(
        self,
        report_repo: ReportRepository,
        audit_repo: AuditLogRepository,
        checker: PermissionChecker,
        user_dir: UserDirectory,
    ) -> None:
        self._report_repo = report_repo
        self._audit_repo = audit_repo
        self._checker = checker
        self._user_dir = user_dir

    async def list_audit_logs(
        self,
        report_id: str,
        *,
        user_id: str | None = None,
    ) -> list[IncidentAuditLogEntry]:
        report = await self._report_repo.get(report_id)
        if report is None:
            return []

        if (
            user_id
            and Permission.REPORT_VIEW_ALL not in await self._checker.permissions_of(user_id)
            and not _is_participant(report, user_id)
        ):
            from ..domain.errors import PermissionDeniedError

            raise PermissionDeniedError("无权查看此报告的审计日志")

        entries = await self._audit_repo.list_by_report(report_id)
        actor_ids = {e.actor_id for e in entries if e.actor_id}
        usernames = await self._user_dir.resolve_usernames(actor_ids)
        return [e.model_copy(update={"actor_name": usernames.get(e.actor_id)}) for e in entries]


def _is_participant(report: Report, user_id: str) -> bool:
    """检查用户是否为报告参与人（报告人/处理人/审核人）。"""
    return user_id in (report.reporter_id, report.assignee_id, report.verifier_id)
