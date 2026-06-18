"""审计事件落库实现。

实现 AuditEventSink 端口，将领域事件写入 incident_audit_logs 表。
"""

import logging
from datetime import UTC, datetime
from uuid import uuid4

from ...core.database import async_session_factory
from ..application.ports import AuditEventSink
from ..domain.events import ReportEvent
from ..models.audit_log import IncidentAuditLog

logger = logging.getLogger(__name__)


class SqlAuditEventSink(AuditEventSink):
    """审计事件落库：将领域事件转为审计日志记录。"""

    async def flush(self, events: list[ReportEvent]) -> None:
        for event in events:
            await self._write_one(event)

    async def _write_one(self, event: ReportEvent) -> IncidentAuditLog:
        now = datetime.now(UTC)
        log_id = uuid4().hex[:32]
        record = IncidentAuditLog(
            id=log_id,
            report_id=event.report_id,
            action=event.action,
            actor_id=event.actor_id or "",
            from_status=event.from_status,
            to_status=event.to_status,
            comment=event.comment,
            metadata_=None,
            created_at=now,
        )
        async with async_session_factory() as session:
            session.add(record)
            await session.commit()
            await session.refresh(record)
        logger.info(
            "创建审计日志: report_id=%s, action=%s, actor_id=%s",
            event.report_id,
            event.action,
            event.actor_id,
        )
        return record
