"""评论应用服务。

提供报告评论的列表查询与新增用例。
"""

from uuid import uuid4

from ..application.ports import (
    CommentRepository,
    PermissionChecker,
    ReportRepository,
    UserDirectory,
)
from ..domain.permission import Permission
from ..domain.report import Report
from ..schemas.response import IncidentCommentEntry


class CommentService:
    """评论用例：查询列表 + 新增评论。"""

    def __init__(
        self,
        report_repo: ReportRepository,
        comment_repo: CommentRepository,
        checker: PermissionChecker,
        user_dir: UserDirectory,
    ) -> None:
        self._report_repo = report_repo
        self._comment_repo = comment_repo
        self._checker = checker
        self._user_dir = user_dir

    async def list_comments(
        self,
        report_id: str,
        *,
        user_id: str | None = None,
    ) -> list[IncidentCommentEntry]:
        report = await self._report_repo.get(report_id)
        if report is None:
            return []

        if (
            user_id
            and Permission.REPORT_VIEW_ALL not in await self._checker.permissions_of(user_id)
            and not _is_participant(report, user_id)
        ):
            from ..domain.errors import PermissionDeniedError

            raise PermissionDeniedError("无权查看此报告的评论")

        entries = await self._comment_repo.list_by_report(report_id)
        author_ids = {e.author_id for e in entries if e.author_id}
        usernames = await self._user_dir.resolve_usernames(author_ids)
        return [e.model_copy(update={"author_name": usernames.get(e.author_id)}) for e in entries]

    async def add_comment(
        self,
        *,
        report_id: str,
        author_id: str,
        content: str,
        parent_id: str | None = None,
    ) -> IncidentCommentEntry:
        report = await self._report_repo.get(report_id)
        if report is None:
            raise ValueError(f"报告 {report_id} 不存在")

        await self._checker.require(author_id, Permission.REPORT_VIEW)

        comment_id = uuid4().hex[:32]
        entry = await self._comment_repo.add(
            comment_id=comment_id,
            report_id=report_id,
            author_id=author_id,
            content=content,
            parent_id=parent_id,
        )
        usernames = await self._user_dir.resolve_usernames({entry.author_id})
        return entry.model_copy(update={"author_name": usernames.get(entry.author_id)})


def _is_participant(report: Report, user_id: str) -> bool:
    """检查用户是否为报告参与人（报告人/处理人/审核人）。"""
    return user_id in (report.reporter_id, report.assignee_id, report.verifier_id)
