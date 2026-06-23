"""审计日志查询仓储实现。

实现 AuditLogRepository 端口，提供审计日志的列表查询。
"""

from sqlalchemy import select

from ...core.database import async_session_factory
from ...shared.dtutils import to_utc8
from ..application.ports import AuditLogRepository
from ..models.audit_log import IncidentAuditLog
from ..schemas.response import IncidentAuditLogEntry


class SqlAuditLogRepository(AuditLogRepository):
    """审计日志查询 SQLAlchemy 实现。"""

    async def list_by_report(self, report_id: str) -> list[IncidentAuditLogEntry]:
        async with async_session_factory() as session:
            result = await session.execute(
                select(IncidentAuditLog)
                .where(
                    IncidentAuditLog.report_id == report_id,
                )
                .order_by(IncidentAuditLog.created_at.asc()),
            )
            records = list(result.scalars().all())
            return [_orm_to_entry(r) for r in records]


def _orm_to_entry(record: IncidentAuditLog) -> IncidentAuditLogEntry:
    """审计日志 ORM → DTO。"""
    return IncidentAuditLogEntry(
        id=record.id,
        action=record.action,
        actor_id=record.actor_id,
        actor_name=None,
        from_status=record.from_status,
        to_status=record.to_status,
        comment=record.comment,
        created_at=to_utc8(record.created_at),
    )
