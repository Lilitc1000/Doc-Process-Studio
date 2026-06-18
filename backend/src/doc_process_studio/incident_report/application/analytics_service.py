"""统计分析应用服务。

提供报告统计、趋势、分布等分析用例。
"""

from ..application.analytics_ports import AnalyticsRepository
from ..application.ports import PermissionChecker
from ..domain.permission import Permission
from ..schemas.response import IncidentAnalyticsOverview, IncidentAnalyticsTrend


class AnalyticsService:
    """统计分析用例：概览 + 趋势。"""

    def __init__(
        self,
        repo: AnalyticsRepository,
        checker: PermissionChecker,
    ) -> None:
        self._repo = repo
        self._checker = checker

    async def get_overview(self, *, user_id: str) -> IncidentAnalyticsOverview:
        await self._checker.require(user_id, Permission.ANALYTICS_VIEW)
        return await self._repo.get_overview()

    async def get_trend(self, *, user_id: str, days: int = 30) -> list[IncidentAnalyticsTrend]:
        await self._checker.require(user_id, Permission.ANALYTICS_VIEW)
        return await self._repo.get_trend(days=days)
