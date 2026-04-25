from datetime import UTC, datetime

from sqlalchemy import delete, select

from ...core.database import async_session_factory
from ..models.incident_report import (
    IncidentReportSessionSnapshot,
    IncidentReportSessionSummary,
)
from ..models.incident_report_session_orm import IncidentReportSession as IncidentReportSessionORM


async def list_incident_session_ids() -> list[str]:
    async with async_session_factory() as session:
        result = await session.execute(
            select(IncidentReportSessionORM.id).order_by(
                IncidentReportSessionORM.updated_at.desc(),
            ),
        )
        return [row[0] for row in result.all()]


async def load_incident_session_summary(session_id: str) -> IncidentReportSessionSummary | None:
    async with async_session_factory() as session:
        result = await session.execute(
            select(IncidentReportSessionORM).where(
                IncidentReportSessionORM.id == session_id,
            ),
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return IncidentReportSessionSummary(
            id=row.id,
            title=row.title,
            status=row.status,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


async def load_incident_session_snapshot(session_id: str) -> IncidentReportSessionSnapshot | None:
    async with async_session_factory() as session:
        result = await session.execute(
            select(IncidentReportSessionORM.snapshot).where(
                IncidentReportSessionORM.id == session_id,
            ),
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return IncidentReportSessionSnapshot.model_validate(row)


async def save_incident_session_summary(summary: IncidentReportSessionSummary) -> None:
    session_id = getattr(summary, "id", None)
    if not isinstance(session_id, str):
        raise ValueError("Summary model must have an 'id' field")
    async with async_session_factory() as session:
        result = await session.execute(
            select(IncidentReportSessionORM).where(
                IncidentReportSessionORM.id == session_id,
            ),
        )
        existing = result.scalar_one_or_none()
        if existing is None:
            irs = IncidentReportSessionORM(
                id=session_id,
                title=summary.title,
                status=summary.status,
                created_at=summary.created_at,
                updated_at=summary.updated_at,
            )
            session.add(irs)
        else:
            existing.title = summary.title
            existing.status = summary.status
            existing.updated_at = summary.updated_at or datetime.now(UTC)
        await session.commit()


async def save_incident_session_snapshot(session_id: str, snapshot: IncidentReportSessionSnapshot) -> None:
    async with async_session_factory() as session:
        result = await session.execute(
            select(IncidentReportSessionORM).where(
                IncidentReportSessionORM.id == session_id,
            ),
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            existing.snapshot = snapshot.model_dump(mode="json")
            existing.updated_at = datetime.now(UTC)
            await session.commit()


async def touch_incident_session_updated_at(session_id: str) -> None:
    async with async_session_factory() as session:
        result = await session.execute(
            select(IncidentReportSessionORM).where(
                IncidentReportSessionORM.id == session_id,
            ),
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            existing.updated_at = datetime.now(UTC)
            await session.commit()


async def delete_incident_session_records(session_id: str) -> bool:
    async with async_session_factory() as session:
        result = await session.execute(
            delete(IncidentReportSessionORM).where(
                IncidentReportSessionORM.id == session_id,
            ),
        )
        await session.commit()
        return result.rowcount > 0
