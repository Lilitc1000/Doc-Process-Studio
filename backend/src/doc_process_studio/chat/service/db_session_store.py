from datetime import UTC, datetime

from sqlalchemy import delete, select

from ...core.database import async_session_factory
from ..models.chat_session_orm import ChatSession as ChatSessionORM
from ..models.session import ChatSessionSnapshot, ChatSessionSummary


async def list_chat_session_ids_by_user(user_id: str) -> list[str]:
    async with async_session_factory() as session:
        result = await session.execute(
            select(ChatSessionORM.id)
            .where(ChatSessionORM.user_id == user_id)
            .order_by(ChatSessionORM.updated_at.desc()),
        )
        return [row[0] for row in result.all()]


async def load_chat_session_summary(session_id: str) -> ChatSessionSummary | None:
    async with async_session_factory() as session:
        result = await session.execute(
            select(ChatSessionORM).where(ChatSessionORM.id == session_id),
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return ChatSessionSummary(
            id=row.id,
            title=row.title,
            created_at=row.created_at,
            updated_at=row.updated_at,
            selected_model=row.selected_model,
            selected_reranker_model=row.selected_reranker_model,
        )


async def load_chat_session_snapshot(session_id: str) -> ChatSessionSnapshot | None:
    async with async_session_factory() as session:
        result = await session.execute(
            select(ChatSessionORM.snapshot).where(ChatSessionORM.id == session_id),
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return ChatSessionSnapshot.model_validate(row)


async def save_chat_session_summary_with_user_id(
    summary: ChatSessionSummary,
    user_id: str,
) -> None:
    summary_id = getattr(summary, "id", None)
    if not isinstance(summary_id, str):
        raise ValueError("Summary model must have an 'id' field")
    async with async_session_factory() as session:
        result = await session.execute(
            select(ChatSessionORM).where(ChatSessionORM.id == summary_id),
        )
        existing = result.scalar_one_or_none()
        if existing is None:
            cs = ChatSessionORM(
                id=summary_id,
                user_id=user_id,
                title=summary.title,
                selected_model=summary.selected_model,
                selected_reranker_model=summary.selected_reranker_model,
                created_at=summary.created_at,
                updated_at=summary.updated_at,
            )
            session.add(cs)
        else:
            existing.title = summary.title
            existing.selected_model = summary.selected_model
            existing.selected_reranker_model = summary.selected_reranker_model
            existing.updated_at = summary.updated_at or datetime.now(UTC)
        await session.commit()


async def save_chat_session_snapshot(session_id: str, snapshot: ChatSessionSnapshot) -> None:
    async with async_session_factory() as session:
        result = await session.execute(
            select(ChatSessionORM).where(ChatSessionORM.id == session_id),
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            existing.snapshot = snapshot.model_dump(mode="json")
            existing.updated_at = datetime.now(UTC)
            await session.commit()


async def touch_chat_session_updated_at(session_id: str) -> None:
    async with async_session_factory() as session:
        result = await session.execute(
            select(ChatSessionORM).where(ChatSessionORM.id == session_id),
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            existing.updated_at = datetime.now(UTC)
            await session.commit()


async def delete_chat_session_records(session_id: str) -> bool:
    async with async_session_factory() as session:
        result = await session.execute(
            delete(ChatSessionORM).where(ChatSessionORM.id == session_id),
        )
        await session.commit()
        return result.rowcount > 0


async def get_chat_session_user_id(session_id: str) -> str | None:
    async with async_session_factory() as session:
        result = await session.execute(
            select(ChatSessionORM.user_id).where(ChatSessionORM.id == session_id),
        )
        row = result.scalar_one_or_none()
        return row


async def delete_chat_sessions_by_title_prefix(
    user_id: str, title_prefix: str
) -> int:
    async with async_session_factory() as session:
        result = await session.execute(
            delete(ChatSessionORM).where(
                ChatSessionORM.user_id == user_id,
                ChatSessionORM.title.like(f"{title_prefix}%"),
            )
        )
        await session.commit()
        return result.rowcount
