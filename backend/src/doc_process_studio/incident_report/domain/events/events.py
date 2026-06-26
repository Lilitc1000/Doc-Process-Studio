"""事故报告领域事件。

每个状态变更动作产生对应的独立事件类，由聚合根在转换时追加，
应用层统一通过 consume_events() 取出并 flush 到 AuditEventSink。
事件类用 ClassVar 声明 action，对应审计日志表的 action 字段值。
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import ClassVar


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class ReportEvent:
    """领域事件基类。子类通过 ClassVar action 声明动作类型。"""

    action: ClassVar[str] = ""
    report_id: str
    actor_id: str | None
    from_status: str | None
    to_status: str | None
    comment: str | None = None
    occurred_at: datetime = field(default_factory=_utcnow)


@dataclass(frozen=True)
class ReportCreated(ReportEvent):
    action: ClassVar[str] = "create"


@dataclass(frozen=True)
class ReportSubmitted(ReportEvent):
    action: ClassVar[str] = "submit"


@dataclass(frozen=True)
class ReportApproved(ReportEvent):
    action: ClassVar[str] = "approve"


@dataclass(frozen=True)
class ReportRejected(ReportEvent):
    action: ClassVar[str] = "reject"


@dataclass(frozen=True)
class HandlerAssigned(ReportEvent):
    action: ClassVar[str] = "assign"


@dataclass(frozen=True)
class ReportClosed(ReportEvent):
    action: ClassVar[str] = "close"


@dataclass(frozen=True)
class ReportReopened(ReportEvent):
    action: ClassVar[str] = "reopen"
