from fastapi import APIRouter, Depends, Query

from ...core.security import get_current_user_id
from ..schemas.response import IncidentAnalyticsOverview, IncidentAnalyticsTrend
from ..service.analytics import get_analytics_overview as _get_overview
from ..service.analytics import get_analytics_trend as _get_trend

router = APIRouter(prefix="/api/incident-report/analytics", tags=["incident-report-analytics"])


@router.get("/overview", response_model=IncidentAnalyticsOverview)
async def get_analytics_overview(
    user_id: str = Depends(get_current_user_id),
) -> IncidentAnalyticsOverview:
    return await _get_overview(user_id=user_id)


@router.get("/trend", response_model=list[IncidentAnalyticsTrend])
async def get_analytics_trend(
    days: int = Query(default=30, ge=1, le=365),
    user_id: str = Depends(get_current_user_id),
) -> list[IncidentAnalyticsTrend]:
    return await _get_trend(user_id=user_id, days=days)
