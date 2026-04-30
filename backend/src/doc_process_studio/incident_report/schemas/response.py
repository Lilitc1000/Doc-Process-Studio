from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from .common import IncidentFormAnswer, IncidentReportStatus, IncidentSeverity


class IncidentBodyGenerateResponse(BaseModel):
    report_id: str = Field(..., description="报告ID")
    form_answers: dict[str, IncidentFormAnswer] = Field(
        default_factory=dict,
        description="更新后的表单答案。",
    )
    trace_id: str = Field(..., description="本次正文生成 trace_id。")
    section_id: str = Field(..., description="本次生成的分段标识。")
    timeline_index: int | None = Field(
        default=None,
        description="若为时间线条目生成，返回条目索引。",
    )


class IncidentReportPreviewResponse(BaseModel):
    source: Literal["draft", "version"] = Field(..., description="预览来源。")
    version: int | None = Field(default=None, description="历史版本号。")
    label: str = Field(..., description="预览标签。")
    html: str = Field(default="", description="HTML 预览内容（已弃用，保留兼容）。")
    docx_base64: str | None = Field(
        default=None,
        description="可选 DOCX 文档内容（base64 编码，草稿预览下载使用）。",
    )
    docx_file_name: str | None = Field(
        default=None,
        description="草稿预览下载文件名。",
    )
    pdf_base64: str | None = Field(
        default=None,
        description="可选 PDF 预览内容（base64 编码）。",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="预览生成提示信息。",
    )


class IncidentReportSummary(BaseModel):
    id: str = Field(..., description="报告ID")
    ref_no: str = Field(..., description="参考编号")
    title: str = Field(..., description="标题")
    status: IncidentReportStatus = Field(..., description="状态")
    severity: IncidentSeverity | None = Field(default=None, description="严重级别")
    reporter_id: str = Field(..., description="报告人ID")
    reporter_name: str | None = Field(default=None, description="报告人姓名")
    assignee_id: str | None = Field(default=None, description="处理人ID")
    assignee_name: str | None = Field(default=None, description="处理人姓名")
    verifier_id: str | None = Field(default=None, description="审核人ID")
    verifier_name: str | None = Field(default=None, description="审核人姓名")
    fault_date: datetime | None = Field(default=None, description="故障日期")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class IncidentReportDetail(IncidentReportSummary):
    system: str | None = Field(default=None, description="所属系统")
    site_id: str | None = Field(default=None, description="站点编号")
    form_data: dict[str, Any] = Field(default_factory=dict, description="表单数据")
    report_data: dict[str, Any] | None = Field(default=None, description="报告数据")
    submitted_at: datetime | None = Field(default=None, description="提交时间")
    approved_at: datetime | None = Field(default=None, description="审批时间")
    closed_at: datetime | None = Field(default=None, description="关闭时间")
    resolution_date: datetime | None = Field(default=None, description="解决日期")


class IncidentReportListResponse(BaseModel):
    total: int = Field(..., description="总数")
    items: list[IncidentReportSummary] = Field(default_factory=list)


class IncidentAuditLogEntry(BaseModel):
    id: str = Field(...)
    action: str = Field(...)
    actor_id: str = Field(...)
    actor_name: str | None = Field(default=None)
    from_status: str | None = Field(default=None)
    to_status: str | None = Field(default=None)
    comment: str | None = Field(default=None)
    created_at: datetime = Field(...)


class IncidentCommentEntry(BaseModel):
    id: str = Field(...)
    report_id: str = Field(...)
    author_id: str = Field(...)
    author_name: str | None = Field(default=None)
    content: str = Field(...)
    parent_id: str | None = Field(default=None)
    created_at: datetime = Field(...)


class IncidentAnalyticsOverview(BaseModel):
    total_this_month: int = Field(...)
    pending_count: int = Field(...)
    in_progress_count: int = Field(...)
    closed_this_month: int = Field(...)
    avg_resolution_hours: float | None = Field(default=None)


class IncidentAnalyticsTrend(BaseModel):
    date: str = Field(...)
    count: int = Field(...)


class IncidentRoleEntry(BaseModel):
    user_id: str = Field(...)
    role: str = Field(...)
    assigned_by: str | None = Field(default=None)
    assigned_by_name: str | None = Field(default=None)
    assigned_at: datetime | None = Field(default=None)


class IncidentUserRolesResponse(BaseModel):
    user_id: str = Field(...)
    roles: list[str] = Field(default_factory=list)


class IncidentRoleListResponse(BaseModel):
    items: list[IncidentRoleEntry] = Field(default_factory=list)


class IncidentRoleDefinitionEntry(BaseModel):
    role_key: str = Field(...)
    role_name: str = Field(...)
    description: str | None = Field(default=None)
    permissions: list[str] = Field(default_factory=list)


class IncidentRoleDefinitionListResponse(BaseModel):
    items: list[IncidentRoleDefinitionEntry] = Field(default_factory=list)


class IncidentPermissionEntry(BaseModel):
    permission_key: str = Field(...)
    permission_name: str = Field(...)
    description: str | None = Field(default=None)
    category: str = Field(...)


class IncidentPermissionListResponse(BaseModel):
    items: list[IncidentPermissionEntry] = Field(default_factory=list)


class IncidentUserPermissionsResponse(BaseModel):
    user_id: str = Field(...)
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)


class IncidentUserWithRolesEntry(BaseModel):
    user_id: str = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    roles: list[str] = Field(default_factory=list, description="已分配的角色列表")


class IncidentUserWithRolesListResponse(BaseModel):
    items: list[IncidentUserWithRolesEntry] = Field(default_factory=list)


__all__ = [
    "IncidentAnalyticsOverview",
    "IncidentAnalyticsTrend",
    "IncidentAuditLogEntry",
    "IncidentCommentEntry",
    "IncidentPermissionEntry",
    "IncidentPermissionListResponse",
    "IncidentReportDetail",
    "IncidentReportListResponse",
    "IncidentReportPreviewResponse",
    "IncidentReportSummary",
    "IncidentRoleDefinitionEntry",
    "IncidentRoleDefinitionListResponse",
    "IncidentRoleEntry",
    "IncidentRoleListResponse",
    "IncidentUserPermissionsResponse",
    "IncidentUserRolesResponse",
    "IncidentUserWithRolesEntry",
    "IncidentUserWithRolesListResponse",
]
