import logging
from datetime import timedelta

from sqlalchemy import func, select

from ...core.database import async_session_factory
from ...shared.dtutils import utcnow
from ..models.incident_report_orm import IncidentReport as IncidentReportORM
from ..schemas.common import PermissionDenied
from ..schemas.response import IncidentAnalyticsOverview, IncidentAnalyticsTrend

logger = logging.getLogger(__name__)


async def _check_analytics_permission(user_id: str) -> None:
    from .role import has_permission

    if not await has_permission(user_id, "analytics:view"):
        raise PermissionDenied("需要查看统计分析权限")


async def get_analytics_overview(user_id: str) -> IncidentAnalyticsOverview:
    await _check_analytics_permission(user_id)
    now = utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    async with async_session_factory() as session:
        total_this_month_result = await session.execute(
            select(func.count(IncidentReportORM.id)).where(
                IncidentReportORM.created_at >= month_start,
            ),
        )
        total_this_month = total_this_month_result.scalar_one()

        pending_result = await session.execute(
            select(func.count(IncidentReportORM.id)).where(
                IncidentReportORM.status == "pending",
            ),
        )
        pending_count = pending_result.scalar_one()

        in_progress_result = await session.execute(
            select(func.count(IncidentReportORM.id)).where(
                IncidentReportORM.status == "in_progress",
            ),
        )
        in_progress_count = in_progress_result.scalar_one()

        closed_this_month_result = await session.execute(
            select(func.count(IncidentReportORM.id)).where(
                IncidentReportORM.status == "closed",
                IncidentReportORM.closed_at >= month_start,
            ),
        )
        closed_this_month = closed_this_month_result.scalar_one()

        avg_resolution_result = await session.execute(
            select(
                func.avg(
                    func.extract("epoch", IncidentReportORM.closed_at - IncidentReportORM.created_at) / 3600
                )
            ).where(
                IncidentReportORM.status == "closed",
                IncidentReportORM.closed_at >= month_start,
                IncidentReportORM.created_at.isnot(None),
                IncidentReportORM.closed_at.isnot(None),
            ),
        )
        avg_resolution_hours = avg_resolution_result.scalar_one_or_none()

    return IncidentAnalyticsOverview(
        total_this_month=total_this_month,
        pending_count=pending_count,
        in_progress_count=in_progress_count,
        closed_this_month=closed_this_month,
        avg_resolution_hours=round(avg_resolution_hours, 1) if avg_resolution_hours else None,
    )


async def get_analytics_trend(user_id: str, days: int = 30) -> list[IncidentAnalyticsTrend]:
    await _check_analytics_permission(user_id)
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
            count=int(getattr(row, "count", 0)),
        )
        for row in rows
    ]
