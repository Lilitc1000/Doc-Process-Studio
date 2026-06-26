"""统计分析仓储 SQLAlchemy 实现。

提供报告统计、趋势、分布等聚合查询。
"""

from datetime import timedelta
from typing import cast

from sqlalchemy import func, select

from ....common.infrastructure.database import async_session_factory
from ....common.utils.dtutils import utcnow
from ...application.dtos import IncidentAnalyticsOverview, IncidentAnalyticsTrend
from ...application.ports.analytics_ports import AnalyticsRepository
from ..persistence.incident_report_orm import IncidentReport as IncidentReportORM


class SqlAnalyticsRepository(AnalyticsRepository):
    """统计分析查询 SQLAlchemy 实现。"""

    async def get_overview(self) -> IncidentAnalyticsOverview:
        async with async_session_factory() as session:
            total_count_result = await session.execute(
                select(func.count(IncidentReportORM.id)),
            )
            total_count = total_count_result.scalar_one()

            draft_result = await session.execute(
                select(func.count(IncidentReportORM.id)).where(
                    IncidentReportORM.status == "draft",
                ),
            )
            draft_count = draft_result.scalar_one()

            pending_result = await session.execute(
                select(func.count(IncidentReportORM.id)).where(
                    IncidentReportORM.status == "pending",
                ),
            )
            pending_count = pending_result.scalar_one()

            rejected_result = await session.execute(
                select(func.count(IncidentReportORM.id)).where(
                    IncidentReportORM.status == "rejected",
                ),
            )
            rejected_count = rejected_result.scalar_one()

            approved_result = await session.execute(
                select(func.count(IncidentReportORM.id)).where(
                    IncidentReportORM.status == "approved",
                ),
            )
            approved_count = approved_result.scalar_one()

            in_progress_result = await session.execute(
                select(func.count(IncidentReportORM.id)).where(
                    IncidentReportORM.status == "in_progress",
                ),
            )
            in_progress_count = in_progress_result.scalar_one()

            closed_count_result = await session.execute(
                select(func.count(IncidentReportORM.id)).where(
                    IncidentReportORM.status == "closed",
                ),
            )
            closed_count = closed_count_result.scalar_one()

            avg_resolution_result = await session.execute(
                select(
                    func.avg(func.extract("epoch", IncidentReportORM.closed_at - IncidentReportORM.created_at) / 3600)
                ).where(
                    IncidentReportORM.status == "closed",
                    IncidentReportORM.created_at.isnot(None),
                    IncidentReportORM.closed_at.isnot(None),
                ),
            )
            avg_resolution_hours = avg_resolution_result.scalar_one_or_none()

        return IncidentAnalyticsOverview(
            total_count=total_count,
            draft_count=draft_count,
            pending_count=pending_count,
            rejected_count=rejected_count,
            approved_count=approved_count,
            in_progress_count=in_progress_count,
            closed_count=closed_count,
            avg_resolution_hours=round(avg_resolution_hours, 1) if avg_resolution_hours else None,
        )

    async def get_trend(self, days: int = 30) -> list[IncidentAnalyticsTrend]:
        now = utcnow()
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if days and days < 365:
            start_date = start_date - timedelta(days=days - 1)

        async with async_session_factory() as session:
            result = await session.execute(
                select(
                    func.date_trunc("day", IncidentReportORM.created_at).label("day"),
                    func.count(IncidentReportORM.id).label("count"),
                )
                .where(
                    IncidentReportORM.created_at >= start_date,
                )
                .group_by("day")
                .order_by("day"),
            )
            rows = result.all()

        return [
            IncidentAnalyticsTrend(
                date=row.day.strftime("%Y-%m-%d") if row.day else "",
                count=int(cast(int, row.count)),
            )
            for row in rows
        ]
