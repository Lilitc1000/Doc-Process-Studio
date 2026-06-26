"""事故报告状态与严重级别的类型定义。

这些 Literal 类型和校验集合用于 HTTP DTO 和 ORM 映射层的类型标注。
领域逻辑层使用 domain/entities/status.py 中的 ReportStatus 枚举。
"""

from typing import Literal

IncidentReportStatus = Literal["draft", "pending", "approved", "rejected", "in_progress", "closed"]
IncidentSeverity = Literal["P0", "P1", "P2", "P3"]

VALID_STATUSES: set[str] = {"draft", "pending", "approved", "rejected", "in_progress", "closed"}
VALID_SEVERITIES: set[str] = {"P0", "P1", "P2", "P3"}
