"""统计分析仓储端口。"""

from abc import ABC, abstractmethod

from ..schemas.response import IncidentAnalyticsOverview, IncidentAnalyticsTrend


class AnalyticsRepository(ABC):
    """统计分析查询端口。"""

    @abstractmethod
    async def get_overview(self) -> IncidentAnalyticsOverview:
        """查询统计概览（各状态数量 + 平均解决时长）。"""

    @abstractmethod
    async def get_trend(self, days: int = 30) -> list[IncidentAnalyticsTrend]:
        """查询创建趋势（按天分组）。"""
