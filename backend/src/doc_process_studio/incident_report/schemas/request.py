from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from .common import INCIDENT_VALID_ROLES, IncidentReportStatus, IncidentSeverity


class IncidentReportCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="报告标题")
    severity: IncidentSeverity | None = Field(default=None, description="严重级别")
    system: str | None = Field(default=None, description="所属系统")
    site_id: str | None = Field(default=None, description="站点编号")
    fault_date: datetime | None = Field(default=None, description="故障日期")
    form_data: dict[str, Any] = Field(default_factory=dict, description="表单数据")


class IncidentReportUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200, description="报告标题")
    severity: IncidentSeverity | None = Field(default=None, description="严重级别")
    system: str | None = Field(default=None, description="所属系统")
    site_id: str | None = Field(default=None, description="站点编号")
    fault_date: datetime | None = Field(default=None, description="故障日期")
    form_data: dict[str, Any] | None = Field(default=None, description="表单数据")


class IncidentReportListRequest(BaseModel):
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")
    status: IncidentReportStatus | None = Field(default=None, description="状态筛选")
    severity: IncidentSeverity | None = Field(default=None, description="严重级别筛选")
    search: str | None = Field(default=None, description="搜索关键词")
    start_date: datetime | None = Field(default=None, description="开始日期")
    end_date: datetime | None = Field(default=None, description="结束日期")


class IncidentReportSubmitRequest(BaseModel):
    comment: str | None = Field(default=None, description="提交备注")


class IncidentReportApproveRequest(BaseModel):
    comment: str = Field(..., min_length=1, description="审核意见")


class IncidentReportRejectRequest(BaseModel):
    comment: str = Field(..., min_length=1, description="驳回原因")


class IncidentReportAssignRequest(BaseModel):
    assignee_id: str = Field(..., min_length=1, description="处理人ID")


class IncidentReportCloseRequest(BaseModel):
    comment: str | None = Field(default=None, description="关闭备注")


class IncidentReportReopenRequest(BaseModel):
    comment: str | None = Field(default=None, description="重新打开备注")


class IncidentRoleAssignRequest(BaseModel):
    user_id: str = Field(..., min_length=1, description="目标用户ID")
    role: str = Field(..., description="角色标识")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in INCIDENT_VALID_ROLES:
            raise ValueError(f"无效的角色标识: {v}，有效值: {', '.join(INCIDENT_VALID_ROLES)}")
        return v


class IncidentCommentCreateRequest(BaseModel):
    content: str = Field(..., min_length=1, description="评论内容")
    parent_id: str | None = Field(default=None, description="父评论ID")


__all__ = [
    "IncidentCommentCreateRequest",
    "IncidentReportApproveRequest",
    "IncidentReportAssignRequest",
    "IncidentReportCloseRequest",
    "IncidentReportCreateRequest",
    "IncidentReportListRequest",
    "IncidentReportReopenRequest",
    "IncidentReportRejectRequest",
    "IncidentRoleAssignRequest",
    "IncidentReportSubmitRequest",
    "IncidentReportUpdateRequest",
]
