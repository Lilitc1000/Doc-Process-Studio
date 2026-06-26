"""应用层统计 DTO。"""

from pydantic import BaseModel, Field


class IncidentAnalyticsOverview(BaseModel):
    total_count: int = Field(...)
    draft_count: int = Field(default=0)
    pending_count: int = Field(...)
    rejected_count: int = Field(default=0)
    approved_count: int = Field(default=0)
    in_progress_count: int = Field(...)
    closed_count: int = Field(...)
    avg_resolution_hours: float | None = Field(default=None)


class IncidentAnalyticsTrend(BaseModel):
    date: str = Field(...)
    count: int = Field(...)
