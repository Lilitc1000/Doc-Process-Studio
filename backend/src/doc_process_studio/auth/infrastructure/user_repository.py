"""SQLAlchemy 用户仓储实现。

实现 UserRepository 端口，封装所有用户数据访问。
"""

from datetime import UTC, datetime
from typing import cast

from sqlalchemy import delete, select
from sqlalchemy.engine import CursorResult

from ...common.infrastructure.database import async_session_factory
from ...common.security.security import generate_user_id
from ..application.ports import UserRepository
from .persistence.user import User


class SqlUserRepository(UserRepository):
    """基于 SQLAlchemy 的用户仓储。"""

    async def get_by_username(self, username: str) -> tuple[str, str, str, str, datetime] | None:
        async with async_session_factory() as session:
            result = await session.execute(select(User).where(User.username == username))
            user = result.scalar_one_or_none()
            if user is None:
                return None
            return (
                user.user_id,
                user.username,
                user.hashed_password,
                user.avatar_color,
                user.created_at,
            )

    async def get_by_user_id(self, user_id: str) -> tuple[str, str, str, str, datetime] | None:
        async with async_session_factory() as session:
            result = await session.execute(select(User).where(User.user_id == user_id))
            user = result.scalar_one_or_none()
            if user is None:
                return None
            return (
                user.user_id,
                user.username,
                user.hashed_password,
                user.avatar_color,
                user.created_at,
            )

    async def username_exists(self, username: str) -> bool:
        async with async_session_factory() as session:
            result = await session.execute(select(User).where(User.username == username))
            return result.scalar_one_or_none() is not None

    async def create(
        self,
        *,
        user_id: str,
        username: str,
        hashed_password: str,
        avatar_color: str,
    ) -> datetime:
        async with async_session_factory() as session:
            user = User(
                user_id=user_id,
                username=username,
                hashed_password=hashed_password,
                avatar_color=avatar_color,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user.created_at

    async def update_profile(
        self,
        user_id: str,
        *,
        username: str | None = None,
        avatar_color: str | None = None,
    ) -> tuple[str, str, str, datetime] | None:
        async with async_session_factory() as session:
            result = await session.execute(select(User).where(User.user_id == user_id))
            user = result.scalar_one_or_none()
            if user is None:
                return None

            if username is not None and username != user.username:
                existing = await session.execute(select(User).where(User.username == username))
                if existing.scalar_one_or_none() is not None:
                    raise ValueError("Username already exists")
                user.username = username

            if avatar_color is not None:
                user.avatar_color = avatar_color

            user.updated_at = datetime.now(UTC)
            await session.commit()
            await session.refresh(user)
            return (user.user_id, user.username, user.avatar_color, user.created_at)

    async def update_password(self, user_id: str, hashed_password: str) -> None:
        async with async_session_factory() as session:
            result = await session.execute(select(User).where(User.user_id == user_id))
            user = result.scalar_one_or_none()
            if user is None:
                return
            user.hashed_password = hashed_password
            user.updated_at = datetime.now(UTC)
            await session.commit()

    async def delete_by_user_id(self, user_id: str) -> bool:
        async with async_session_factory() as session:
            result = await session.execute(select(User).where(User.user_id == user_id))
            user = result.scalar_one_or_none()
            if user is None:
                return False
            await session.execute(delete(User).where(User.user_id == user_id))
            await session.commit()
            return True

    async def delete_by_username_prefix(self, prefix: str) -> int:
        from ...incident_report.infrastructure.persistence.audit_log import IncidentAuditLog
        from ...incident_report.infrastructure.persistence.incident_report_orm import (
            IncidentComment,
            IncidentReport,
        )
        from ...incident_report.infrastructure.persistence.incident_report_role import IncidentReportUserRole

        async with async_session_factory() as session:
            user_ids_result = await session.execute(select(User.user_id).where(User.username.like(f"{prefix}%")))
            user_ids = [row[0] for row in user_ids_result.all()]

            if not user_ids:
                return 0

            report_ids_result = await session.execute(
                select(IncidentReport.id).where(IncidentReport.reporter_id.in_(user_ids))
            )
            report_ids = [row[0] for row in report_ids_result.all()]

            if report_ids:
                await session.execute(delete(IncidentComment).where(IncidentComment.report_id.in_(report_ids)))
                await session.execute(delete(IncidentAuditLog).where(IncidentAuditLog.report_id.in_(report_ids)))
                await session.execute(delete(IncidentReport).where(IncidentReport.id.in_(report_ids)))

            await session.execute(delete(IncidentComment).where(IncidentComment.author_id.in_(user_ids)))
            await session.execute(delete(IncidentAuditLog).where(IncidentAuditLog.actor_id.in_(user_ids)))
            await session.execute(delete(IncidentReportUserRole).where(IncidentReportUserRole.user_id.in_(user_ids)))
            await session.execute(delete(IncidentReport).where(IncidentReport.reporter_id.in_(user_ids)))

            result = await session.execute(delete(User).where(User.username.like(f"{prefix}%")))
            await session.commit()
            count: int = cast(CursorResult, result).rowcount
            return count

    async def count_users(self) -> int:
        async with async_session_factory() as session:
            result = await session.execute(select(User).limit(1))
            return 0 if result.scalar_one_or_none() is None else 1

    async def resolve_usernames(self, user_ids: set[str]) -> dict[str, str]:
        if not user_ids:
            return {}
        async with async_session_factory() as session:
            result = await session.execute(select(User.user_id, User.username).where(User.user_id.in_(user_ids)))
            return {row[0]: row[1] for row in result.all()}

    async def assign_all_roles_to_admin(self, user_id: str) -> None:
        from ...incident_report.domain.values.permission import VALID_ROLES
        from ...incident_report.infrastructure.persistence.incident_report_role import IncidentReportUserRole

        async with async_session_factory() as session:
            for role_key in VALID_ROLES:
                session.add(
                    IncidentReportUserRole(
                        id=generate_user_id(),
                        user_id=user_id,
                        role_key=role_key,
                        assigned_by=user_id,
                    )
                )
            await session.commit()
