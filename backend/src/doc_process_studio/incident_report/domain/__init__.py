"""领域层包。

通过子包组织领域模型：entities（聚合根/实体）、events（领域事件）、values（值对象/常量/规则）。
本包 re-export 核心领域名称，常量等请直接从子包导入（如 from domain.values.constants import xxx）。
"""

from .entities import Report, ReportStatus
from .events import (
    HandlerAssigned,
    ReportApproved,
    ReportClosed,
    ReportCreated,
    ReportEvent,
    ReportRejected,
    ReportReopened,
    ReportSubmitted,
)
from .values import (
    INCIDENT_REPORT_FORM_SCHEMA,
    INCIDENT_VALID_ROLES,
    ROLE_DEFINITIONS,
    ROLE_PERMISSIONS_MAP,
    VALID_PERMISSIONS,
    VALID_ROLES,
    VALID_SEVERITIES,
    VALID_STATUSES,
    DomainError,
    IncidentReportStatus,
    IncidentSeverity,
    Permission,
    PermissionDeniedError,
    ReportNotFoundError,
    Role,
    find_missing_submit_fields,
)

__all__ = [
    "Report",
    "ReportStatus",
    "ReportEvent",
    "ReportCreated",
    "ReportSubmitted",
    "ReportApproved",
    "ReportRejected",
    "ReportClosed",
    "ReportReopened",
    "HandlerAssigned",
    "DomainError",
    "PermissionDeniedError",
    "ReportNotFoundError",
    "INCIDENT_REPORT_FORM_SCHEMA",
    "INCIDENT_VALID_ROLES",
    "ROLE_DEFINITIONS",
    "ROLE_PERMISSIONS_MAP",
    "VALID_PERMISSIONS",
    "VALID_ROLES",
    "find_missing_submit_fields",
    "Permission",
    "Role",
    "IncidentReportStatus",
    "IncidentSeverity",
    "VALID_SEVERITIES",
    "VALID_STATUSES",
]
