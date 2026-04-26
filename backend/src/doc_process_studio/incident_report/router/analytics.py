from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select

from ...core.database import async_session_factory
from ...core.security import get_current_user_id
from ..models.incident_report_orm import IncidentReport as IncidentReportORM
from ..schemas.response import IncidentAnalyticsOverview, IncidentAnalyticsTrend

router = APIRouter(prefix="/api/incident-report/analytics", tags=["incident-report-analytics"])


@router.get("/overview", response_model=IncidentAnalyticsOverview)
async def get_analytics_overview(
    user_id: str = Depends(get_current_user_id),
) -> IncidentAnalyticsOverview:
    from ...shared.dtutils import utcnow
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


@router.get("/trend", response_model=list[IncidentAnalyticsTrend])
async def get_analytics_trend(
    days: int = Query(default=30, ge=1, le=365),
    user_id: str = Depends(get_current_user_id),
) -> list[IncidentAnalyticsTrend]:
    from ...shared.dtutils import utcnow
    now = utcnow()
    start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if days and days < 365:
        from datetime import timedelta
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
        IncidentAnalyticsTrend(date=row.day.strftime("%Y-%m-%d") if row.day else "", count=row.count)
        for row in rows
    ]
