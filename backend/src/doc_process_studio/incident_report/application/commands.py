"""应用层命令对象。

每个用例对应一个命令，纯 dataclass，不包含业务逻辑。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ..domain.values.status_types import IncidentSeverity


@dataclass
class CreateReportCommand:
    title: str
    reporter_id: str
    severity: IncidentSeverity | None = None
    system: str | None = None
    site_id: str | None = None
    fault_date: datetime | None = None
    form_data: dict[str, Any] | None = None
    ref_no: str | None = None


@dataclass
class UpdateReportCommand:
    report_id: str
    actor_id: str
    fields: dict[str, Any] = field(default_factory=dict)


@dataclass
class DeleteReportCommand:
    report_id: str
    actor_id: str | None = None


@dataclass
class SubmitReportCommand:
    report_id: str
    actor_id: str
    comment: str | None = None


@dataclass
class ApproveReportCommand:
    report_id: str
    actor_id: str
    comment: str | None = None


@dataclass
class RejectReportCommand:
    report_id: str
    actor_id: str
    comment: str


@dataclass
class AssignHandlerCommand:
    report_id: str
    actor_id: str
    assignee_id: str


@dataclass
class CloseReportCommand:
    report_id: str
    actor_id: str
    comment: str | None = None


@dataclass
class ReopenReportCommand:
    report_id: str
    actor_id: str
    comment: str | None = None
