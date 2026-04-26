from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import delete, func, select

from ...core.database import async_session_factory
from ..models.incident_report_orm import IncidentComment, IncidentReport as IncidentReportORM
from ..schemas.common import VALID_STATUSES
from ..schemas.response import IncidentReportDetail, IncidentReportSummary


async def generate_ref_no() -> str:
    async with async_session_factory() as session:
        result = await session.execute(
            select(func.count(IncidentReportORM.id)),
        )
        count = result.scalar_one() + 1
        return f"DAS-{count:04d}"


async def create_report_record(
    *,
    report_id: str,
    ref_no: str,
    title: str,
    reporter_id: str,
    severity: str | None = None,
    system: str | None = None,
    site_id: str | None = None,
    fault_date: datetime | None = None,
    form_data: dict | None = None,
) -> IncidentReportORM:
    now = datetime.now(UTC)
    record = IncidentReportORM(
        id=report_id,
        ref_no=ref_no,
        title=title,
        status="draft",
        severity=severity,
        reporter_id=reporter_id,
        system=system,
        site_id=site_id,
        fault_date=fault_date,
        form_data=form_data or {},
        created_at=now,
        updated_at=now,
    )
    async with async_session_factory() as session:
        session.add(record)
        await session.commit()
        await session.refresh(record)
    return record


async def load_report_orm(report_id: str) -> IncidentReportORM | None:
    async with async_session_factory() as session:
        result = await session.execute(
            select(IncidentReportORM).where(
                IncidentReportORM.id == report_id,
            ),
        )
        return result.scalar_one_or_none()


_CLEAR_SENTINEL = object()


async def update_report_record(
    report_id: str,
    **fields,
) -> IncidentReportORM | None:
    async with async_session_factory() as session:
        result = await session.execute(
            select(IncidentReportORM).where(
                IncidentReportORM.id == report_id,
            ),
        )
        record = result.scalar_one_or_none()
        if record is None:
            return None
        for key, value in fields.items():
            if not hasattr(record, key):
                continue
            if value is _CLEAR_SENTINEL:
                setattr(record, key, None)
            elif value is not None:
                setattr(record, key, value)
        # Safety: ensure no _CLEAR_SENTINEL values remain on the record before commit
        for key in fields:
            if hasattr(record, key) and getattr(record, key, None) is _CLEAR_SENTINEL:
                setattr(record, key, None)
        record.updated_at = datetime.now(UTC)
        await session.commit()
        await session.refresh(record)
    return record


async def delete_report_record(report_id: str) -> bool:
    async with async_session_factory() as session:
        result = await session.execute(
            delete(IncidentReportORM).where(
                IncidentReportORM.id == report_id,
            ),
        )
        await session.commit()
        return result.rowcount > 0


async def list_reports(
    *,
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    severity: str | None = None,
    search: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> tuple[list[IncidentReportORM], int]:
    async with async_session_factory() as session:
        query = select(IncidentReportORM)
        count_query = select(func.count(IncidentReportORM.id))

        if status is not None:
            query = query.where(IncidentReportORM.status == status)
            count_query = count_query.where(IncidentReportORM.status == status)
        if severity is not None:
            query = query.where(IncidentReportORM.severity == severity)
            count_query = count_query.where(IncidentReportORM.severity == severity)
        if search is not None:
            search_filter = IncidentReportORM.title.ilike(f"%{search}%")
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)
        if start_date is not None:
            query = query.where(IncidentReportORM.created_at >= start_date)
            count_query = count_query.where(IncidentReportORM.created_at >= start_date)
        if end_date is not None:
            query = query.where(IncidentReportORM.created_at <= end_date)
            count_query = count_query.where(IncidentReportORM.created_at <= end_date)

        total_result = await session.execute(count_query)
        total = total_result.scalar_one()

        offset = (page - 1) * page_size
        query = query.order_by(IncidentReportORM.updated_at.desc()).offset(offset).limit(page_size)
        result = await session.execute(query)
        records = list(result.scalars().all())

    return records, total


async def create_comment_record(
    *,
    comment_id: str,
    report_id: str,
    author_id: str,
    content: str,
    parent_id: str | None = None,
) -> IncidentComment:
    now = datetime.now(UTC)
    record = IncidentComment(
        id=comment_id,
        report_id=report_id,
        author_id=author_id,
        content=content,
        parent_id=parent_id,
        created_at=now,
    )
    async with async_session_factory() as session:
        session.add(record)
        await session.commit()
        await session.refresh(record)
    return record


async def list_comment_records(report_id: str) -> list[IncidentComment]:
    async with async_session_factory() as session:
        result = await session.execute(
            select(IncidentComment).where(
                IncidentComment.report_id == report_id,
            ).order_by(IncidentComment.created_at.asc()),
        )
        return list(result.scalars().all())


def orm_to_summary(record: IncidentReportORM) -> IncidentReportSummary:
    return IncidentReportSummary(
        id=record.id,
        ref_no=record.ref_no,
        title=record.title,
        status=record.status,
        severity=record.severity,
        reporter_id=record.reporter_id,
        reporter_name=None,
        assignee_id=record.assignee_id,
        assignee_name=None,
        verifier_id=record.verifier_id,
        verifier_name=None,
        fault_date=record.fault_date,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def orm_to_detail(record: IncidentReportORM) -> IncidentReportDetail:
    return IncidentReportDetail(
        id=record.id,
        ref_no=record.ref_no,
        title=record.title,
        status=record.status,
        severity=record.severity,
        reporter_id=record.reporter_id,
        reporter_name=None,
        assignee_id=record.assignee_id,
        assignee_name=None,
        verifier_id=record.verifier_id,
        verifier_name=None,
        fault_date=record.fault_date,
        created_at=record.created_at,
        updated_at=record.updated_at,
        system=record.system,
        site_id=record.site_id,
        form_data=record.form_data or {},
        report_data=record.report_data,
        submitted_at=record.submitted_at,
        approved_at=record.approved_at,
        closed_at=record.closed_at,
        resolution_date=record.resolution_date,
    )
