import logging
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)

from ...core.database import async_session_factory
from ...shared.dtutils import to_utc8
from ...auth.service.auth import resolve_usernames
from ..models.incident_report_orm import IncidentComment, IncidentReport as IncidentReportORM
from ..schemas.common import VALID_STATUSES
from ..schemas.response import IncidentReportDetail, IncidentReportSummary


async def generate_ref_no() -> str:
    async with async_session_factory() as session:
        result = await session.execute(
            select(func.max(IncidentReportORM.ref_no)),
        )
        max_ref = result.scalar_one_or_none()
        if max_ref is None:
            next_num = 1
        else:
            try:
                next_num = int(max_ref.split("-")[1]) + 1
            except (IndexError, ValueError):
                next_num = 1
        return f"DAS-{next_num:04d}"


_REF_NO_RETRY_MAX = 8


async def create_report_record(
    *,
    report_id: str,
    ref_no: str | None = None,
    title: str,
    reporter_id: str,
    severity: str | None = None,
    system: str | None = None,
    site_id: str | None = None,
    fault_date: datetime | None = None,
    form_data: dict | None = None,
) -> IncidentReportORM:
    now = datetime.now(UTC)
    effective_ref_no = ref_no
    for attempt in range(_REF_NO_RETRY_MAX + 1):
        if effective_ref_no is None:
            effective_ref_no = await generate_ref_no()
        record = IncidentReportORM(
            id=report_id,
            ref_no=effective_ref_no,
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
            try:
                await session.commit()
                await session.refresh(record)
                logger.info("Report created successfully: id=%s, ref_no=%s", record.id, record.ref_no)
                return record
            except IntegrityError:
                await session.rollback()
                logger.warning("IntegrityError creating report: id=%s, ref_no=%s, attempt=%d", report_id, effective_ref_no, attempt)
                if ref_no is not None:
                    raise
                effective_ref_no = None


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


async def _resolve_usernames_safe(user_ids: set[str]) -> dict[str, str]:
    if not user_ids:
        return {}
    try:
        return await resolve_usernames(user_ids)
    except Exception:
        logger.warning("Failed to resolve usernames for ids: %s", user_ids, exc_info=True)
        return {}


async def orm_to_summary(record: IncidentReportORM) -> IncidentReportSummary:
    user_ids = {uid for uid in (record.reporter_id, record.assignee_id, record.verifier_id) if uid}
    usernames = await _resolve_usernames_safe(user_ids)
    return IncidentReportSummary(
        id=record.id,
        ref_no=record.ref_no,
        title=record.title,
        status=record.status,
        severity=record.severity,
        reporter_id=record.reporter_id,
        reporter_name=usernames.get(record.reporter_id),
        assignee_id=record.assignee_id,
        assignee_name=usernames.get(record.assignee_id) if record.assignee_id else None,
        verifier_id=record.verifier_id,
        verifier_name=usernames.get(record.verifier_id) if record.verifier_id else None,
        fault_date=to_utc8(record.fault_date),
        created_at=to_utc8(record.created_at),
        updated_at=to_utc8(record.updated_at),
    )


async def orm_to_detail(record: IncidentReportORM) -> IncidentReportDetail:
    user_ids = {uid for uid in (record.reporter_id, record.assignee_id, record.verifier_id) if uid}
    usernames = await _resolve_usernames_safe(user_ids)
    return IncidentReportDetail(
        id=record.id,
        ref_no=record.ref_no,
        title=record.title,
        status=record.status,
        severity=record.severity,
        reporter_id=record.reporter_id,
        reporter_name=usernames.get(record.reporter_id),
        assignee_id=record.assignee_id,
        assignee_name=usernames.get(record.assignee_id) if record.assignee_id else None,
        verifier_id=record.verifier_id,
        verifier_name=usernames.get(record.verifier_id) if record.verifier_id else None,
        fault_date=to_utc8(record.fault_date),
        created_at=to_utc8(record.created_at),
        updated_at=to_utc8(record.updated_at),
        system=record.system,
        site_id=record.site_id,
        form_data=record.form_data or {},
        report_data=record.report_data,
        submitted_at=to_utc8(record.submitted_at),
        approved_at=to_utc8(record.approved_at),
        closed_at=to_utc8(record.closed_at),
        resolution_date=to_utc8(record.resolution_date),
    )
