from typing import Iterable

from sqlalchemy import delete, select

from ...core.database import async_session_factory
from ..models.incident_report_role import IncidentReportRole
from ..schemas.common import VALID_ROLES


async def get_user_incident_roles(user_id: str) -> set[str]:
    async with async_session_factory() as session:
        result = await session.execute(
            select(IncidentReportRole.role).where(
                IncidentReportRole.user_id == user_id,
            ),
        )
        return {row[0] for row in result.all()}


async def has_incident_role(user_id: str, role: str) -> bool:
    async with async_session_factory() as session:
        result = await session.execute(
            select(IncidentReportRole.role).where(
                IncidentReportRole.user_id == user_id,
                IncidentReportRole.role == role,
            ),
        )
        return result.scalar_one_or_none() is not None


async def require_incident_role(user_id: str, roles: Iterable[str]) -> bool:
    user_roles = await get_user_incident_roles(user_id)
    return bool(user_roles.intersection(set(roles)))


async def assign_incident_role(
    user_id: str,
    role: str,
    assigned_by: str,
) -> None:
    if role not in VALID_ROLES:
        raise ValueError(f"无效的角色标识: {role}")
    async with async_session_factory() as session:
        result = await session.execute(
            select(IncidentReportRole).where(
                IncidentReportRole.user_id == user_id,
                IncidentReportRole.role == role,
            ),
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            return
        entry = IncidentReportRole(
            user_id=user_id,
            role=role,
            assigned_by=assigned_by,
        )
        session.add(entry)
        await session.commit()


async def revoke_incident_role(user_id: str, role: str) -> None:
    if role not in VALID_ROLES:
        raise ValueError(f"无效的角色标识: {role}")
    async with async_session_factory() as session:
        await session.execute(
            delete(IncidentReportRole).where(
                IncidentReportRole.user_id == user_id,
                IncidentReportRole.role == role,
            ),
        )
        await session.commit()


async def list_all_role_assignments() -> list[IncidentReportRole]:
    async with async_session_factory() as session:
        result = await session.execute(
            select(IncidentReportRole).order_by(
                IncidentReportRole.user_id,
                IncidentReportRole.role,
            ),
        )
        return list(result.scalars().all())
