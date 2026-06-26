from fastapi import APIRouter, Depends, Query

from ...common.security.security import get_current_user_id
from ..application.services.analytics_service import AnalyticsService
from ..domain.values.errors import DomainError
from ..infrastructure.dependencies import get_analytics_service
from .schemas.response import IncidentAnalyticsOverview, IncidentAnalyticsTrend

router = APIRouter(prefix="/api/incident-report/analytics", tags=["incident-report-analytics"])


@router.get("/overview", response_model=IncidentAnalyticsOverview)
async def get_analytics_overview(
    user_id: str = Depends(get_current_user_id),
    service: AnalyticsService = Depends(get_analytics_service),
) -> IncidentAnalyticsOverview:
    try:
        result: IncidentAnalyticsOverview = await service.get_overview(user_id=user_id)
        return result
    except DomainError as exc:
        from .reports import _handle_domain_error

        raise _handle_domain_error(exc) from exc


@router.get("/trend", response_model=list[IncidentAnalyticsTrend])
async def get_analytics_trend(
    days: int = Query(default=30, ge=1, le=365),
    user_id: str = Depends(get_current_user_id),
    service: AnalyticsService = Depends(get_analytics_service),
) -> list[IncidentAnalyticsTrend]:
    try:
        result: list[IncidentAnalyticsTrend] = await service.get_trend(user_id=user_id, days=days)
        return result
    except DomainError as exc:
        from .reports import _handle_domain_error

        raise _handle_domain_error(exc) from exc
