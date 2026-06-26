"""SQLAlchemy 报告仓储实现。

实现 ReportRepository 端口。
add() 包含 ref_no 冲突重试。
update() 直接按聚合根状态写回，closed_at=None 就写 None。
"""

import logging
from datetime import UTC, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from ....auth.infrastructure.user_repository import SqlUserRepository
from ....common.infrastructure.database import async_session_factory
from ...application.dtos import IncidentReportSummary
from ...application.ports import RefNoGenerator, ReportRepository, UserDirectory
from ...domain.entities.report import Report
from ..persistence.audit_log import IncidentAuditLog
from ..persistence.incident_report_orm import IncidentComment
from ..persistence.incident_report_orm import IncidentReport as IncidentReportORM
from .orm_mappers import apply_report_to_orm, build_orm_from_report, orm_to_report, orm_to_summary

logger = logging.getLogger(__name__)

_REF_NO_RETRY_MAX = 8


class SqlUserDirectory(UserDirectory):
    """用户目录实现：调用 auth 仓储解析用户名。"""

    _repo = SqlUserRepository()

    async def resolve_usernames(self, user_ids: set[str]) -> dict[str, str]:
        if not user_ids:
            return {}
        try:
            return await self._repo.resolve_usernames(user_ids)
        except Exception:
            logger.warning("Failed to resolve usernames for ids: %s", user_ids, exc_info=True)
            return {}


class SequentialRefNoGenerator(RefNoGenerator):
    """报告编号生成器：DAS-XXXX 递增格式。"""

    async def next(self) -> str:
        async with async_session_factory() as session:
            result = await session.execute(
                select(func.max(IncidentReportORM.ref_no)),
            )
            max_ref = result.scalar_one_or_none()
            if max_ref is None:
                next_num = 1
            else:
                try:
                    next_num = int(max_ref.split("-")[1]) + 1
                except (IndexError, ValueError):
                    next_num = 1
            return f"DAS-{next_num:04d}"


class SqlAlchemyReportRepository(ReportRepository):
    """报告仓储 SQLAlchemy 实现。"""

    def __init__(
        self,
        user_dir: UserDirectory,
        ref_no_gen: RefNoGenerator,
    ) -> None:
        self._user_dir = user_dir
        self._ref_no_gen = ref_no_gen

    async def add(self, report: Report) -> Report:
        """新建报告，包含 ref_no 冲突重试。"""
        effective_ref_no = report.ref_no
        for attempt in range(_REF_NO_RETRY_MAX + 1):
            orm = build_orm_from_report(report)
            orm.ref_no = effective_ref_no
            async with async_session_factory() as session:
                session.add(orm)
                try:
                    await session.commit()
                    await session.refresh(orm)
                    logger.info(
                        "Report created successfully: id=%s, ref_no=%s",
                        orm.id,
                        orm.ref_no,
                    )
                    return orm_to_report(orm)
                except IntegrityError:
                    await session.rollback()
                    logger.warning(
                        "IntegrityError creating report: id=%s, ref_no=%s, attempt=%d",
                        report.id,
                        effective_ref_no,
                        attempt,
                    )
                    # 仅当 ref_no 是自动生成时才重试；显式指定的 ref_no 冲突直接抛错
                    effective_ref_no = await self._ref_no_gen.next()
        raise RuntimeError(f"Failed to create report after {_REF_NO_RETRY_MAX} retries: id={report.id}")

    async def get(self, report_id: str) -> Report | None:
        async with async_session_factory() as session:
            result = await session.execute(
                select(IncidentReportORM).where(IncidentReportORM.id == report_id),
            )
            orm = result.scalar_one_or_none()
            return orm_to_report(orm) if orm else None

    async def update(self, report: Report) -> Report | None:
        async with async_session_factory() as session:
            result = await session.execute(
                select(IncidentReportORM).where(IncidentReportORM.id == report.id),
            )
            orm = result.scalar_one_or_none()
            if orm is None:
                return None
            apply_report_to_orm(report, orm)
            await session.commit()
            await session.refresh(orm)
        return orm_to_report(orm)

    async def list(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        severity: str | None = None,
        search: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        reporter_id_filter: str | None = None,
    ) -> tuple[list[IncidentReportSummary], int]:
        async with async_session_factory() as session:
            query = select(IncidentReportORM)
            count_query = select(func.count(IncidentReportORM.id))

            if reporter_id_filter is not None:
                query = query.where(IncidentReportORM.reporter_id == reporter_id_filter)
                count_query = count_query.where(IncidentReportORM.reporter_id == reporter_id_filter)
            if status is not None:
                query = query.where(IncidentReportORM.status == status)
                count_query = count_query.where(IncidentReportORM.status == status)
            if severity is not None:
                query = query.where(IncidentReportORM.severity == severity)
                count_query = count_query.where(IncidentReportORM.severity == severity)
            if search is not None:
                search_filter = IncidentReportORM.title.ilike(f"%{search}%")
                query = query.where(search_filter)
                count_query = count_query.where(search_filter)
            if start_date is not None:
                query = query.where(IncidentReportORM.created_at >= start_date)
                count_query = count_query.where(IncidentReportORM.created_at >= start_date)
            if end_date is not None:
                query = query.where(IncidentReportORM.created_at <= end_date)
                count_query = count_query.where(IncidentReportORM.created_at <= end_date)

            total_result = await session.execute(count_query)
            total = total_result.scalar_one()

            offset = (page - 1) * page_size
            query = query.order_by(IncidentReportORM.updated_at.desc()).offset(offset).limit(page_size)
            result = await session.execute(query)
            records = list(result.scalars().all())

        # 批量解析用户名
        user_ids: set[str] = set()
        for r in records:
            for uid in (r.reporter_id, r.assignee_id, r.verifier_id):
                if uid:
                    user_ids.add(uid)
        usernames = await self._user_dir.resolve_usernames(user_ids)

        items = [await orm_to_summary(r, usernames) for r in records]
        return items, total

    async def delete(self, report_id: str) -> bool:
        """删除报告，级联删除评论和审计日志（与原 delete_report 一致）。"""
        async with async_session_factory() as session:
            record = await session.get(IncidentReportORM, report_id)
            if record is None:
                return False
            await session.execute(delete(IncidentComment).where(IncidentComment.report_id == report_id))
            await session.execute(delete(IncidentAuditLog).where(IncidentAuditLog.report_id == report_id))
            await session.delete(record)
            await session.commit()
        return True

    async def update_form_data(
        self,
        report_id: str,
        form_data: dict,
        report_data: dict | None = None,
    ) -> Report | None:
        """更新报告的 form_data 和 report_data，返回更新后的聚合根。"""
        async with async_session_factory() as session:
            result = await session.execute(
                select(IncidentReportORM).where(IncidentReportORM.id == report_id),
            )
            orm = result.scalar_one_or_none()
            if orm is None:
                return None
            orm.form_data = form_data
            if report_data is not None:
                orm.report_data = report_data
            orm.updated_at = datetime.now(UTC)
            await session.commit()
            await session.refresh(orm)
        return orm_to_report(orm)
