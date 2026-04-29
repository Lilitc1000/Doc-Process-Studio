from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select

from ...core.database import async_session_factory
from ...shared.dtutils import to_utc8
from ..models.audit_log import IncidentAuditLog
from ..schemas.response import IncidentAuditLogEntry


async def create_audit_log(
    *,
    report_id: str,
    action: str,
    actor_id: str,
    from_status: str | None = None,
    to_status: str | None = None,
    comment: str | None = None,
    metadata: dict | None = None,
) -> IncidentAuditLog:
    now = datetime.now(UTC)
    log_id = uuid4().hex[:32]
    record = IncidentAuditLog(
        id=log_id,
        report_id=report_id,
        action=action,
        actor_id=actor_id,
        from_status=from_status,
        to_status=to_status,
        comment=comment,
        metadata_=metadata,
        created_at=now,
    )
    async with async_session_factory() as session:
        session.add(record)
        await session.commit()
        await session.refresh(record)
    return record


async def list_audit_logs(report_id: str) -> list[IncidentAuditLog]:
    async with async_session_factory() as session:
        result = await session.execute(
            select(IncidentAuditLog).where(
                IncidentAuditLog.report_id == report_id,
            ).order_by(IncidentAuditLog.created_at.asc()),
        )
        return list(result.scalars().all())


def orm_to_entry(record: IncidentAuditLog) -> IncidentAuditLogEntry:
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
