"""评论仓储实现。

实现 CommentRepository 端口，提供评论的列表查询与新增。
"""

from datetime import UTC, datetime

from sqlalchemy import select

from ...core.database import async_session_factory
from ...shared.dtutils import to_utc8
from ..application.ports import CommentRepository
from ..models.incident_report_orm import IncidentComment
from ..schemas.response import IncidentCommentEntry


class SqlCommentRepository(CommentRepository):
    """评论仓储 SQLAlchemy 实现。"""

    async def add(
        self,
        *,
        comment_id: str,
        report_id: str,
        author_id: str,
        content: str,
        parent_id: str | None = None,
    ) -> IncidentCommentEntry:
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
        return _orm_to_entry(record)

    async def list_by_report(self, report_id: str) -> list[IncidentCommentEntry]:
        async with async_session_factory() as session:
            result = await session.execute(
                select(IncidentComment)
                .where(
                    IncidentComment.report_id == report_id,
                )
                .order_by(IncidentComment.created_at.asc()),
            )
            records = list(result.scalars().all())
            return [_orm_to_entry(r) for r in records]


def _orm_to_entry(record: IncidentComment) -> IncidentCommentEntry:
    """评论 ORM → DTO。"""
    return IncidentCommentEntry(
        id=record.id,
        report_id=record.report_id,
        author_id=record.author_id,
        author_name=None,
        content=record.content,
        parent_id=record.parent_id,
        created_at=to_utc8(record.created_at),
    )
