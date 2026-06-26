"""用户接口层响应 DTO。

从 application/dtos/ re-export 端口返回类型，供 router 层作为 FastAPI response_model 使用。
所有数据结构定义在 application/dtos/ 中，本文件不新增类型。
"""

from ...application.dtos import (
    IncidentAnalyticsOverview,
    IncidentAnalyticsTrend,
    IncidentAuditLogEntry,
    IncidentBodyGenerateResponse,
    IncidentCommentEntry,
    IncidentPermissionEntry,
    IncidentPermissionListResponse,
    IncidentReportDetail,
    IncidentReportListResponse,
    IncidentReportPreviewResponse,
    IncidentReportSummary,
    IncidentRoleDefinitionEntry,
    IncidentRoleDefinitionListResponse,
    IncidentRoleEntry,
    IncidentRoleListResponse,
    IncidentUserPermissionsResponse,
    IncidentUserRolesResponse,
    IncidentUserWithRolesEntry,
    IncidentUserWithRolesListResponse,
)

__all__ = [
    "IncidentAnalyticsOverview",
    "IncidentAnalyticsTrend",
    "IncidentAuditLogEntry",
    "IncidentBodyGenerateResponse",
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
