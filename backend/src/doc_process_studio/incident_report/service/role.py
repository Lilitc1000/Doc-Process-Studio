from typing import Iterable

from sqlalchemy import delete, func, select

from ...core.database import async_session_factory
from ...core.security import generate_user_id
from ...auth.models.user import User
from ..models.incident_report_role import (
    IncidentReportPermission,
    IncidentReportRoleDefinition,
    IncidentReportRolePermission,
    IncidentReportUserRole,
)
from ..schemas.common import (
    PERMISSION_DEFINITIONS,
    ROLE_DEFINITIONS,
    ROLE_PERMISSIONS_MAP,
    VALID_ROLES,
)


async def get_user_incident_roles(user_id: str) -> set[str]:
    async with async_session_factory() as session:
        result = await session.execute(
            select(IncidentReportUserRole.role_key).where(
                IncidentReportUserRole.user_id == user_id,
            ),
        )
        return {row[0] for row in result.all()}


async def has_incident_role(user_id: str, role: str) -> bool:
    async with async_session_factory() as session:
        result = await session.execute(
            select(IncidentReportUserRole.role_key).where(
                IncidentReportUserRole.user_id == user_id,
                IncidentReportUserRole.role_key == role,
            ),
        )
        return result.scalar_one_or_none() is not None


async def require_incident_role(user_id: str, roles: Iterable[str]) -> bool:
    user_roles = await get_user_incident_roles(user_id)
    return bool(user_roles.intersection(set(roles)))


async def get_user_permissions(user_id: str) -> set[str]:
    user_roles = await get_user_incident_roles(user_id)
    if not user_roles:
        return set()
    permissions: set[str] = set()
    for role_key in user_roles:
        role_perms = ROLE_PERMISSIONS_MAP.get(role_key, set())
        permissions.update(role_perms)
    return permissions


async def has_permission(user_id: str, permission: str) -> bool:
    permissions = await get_user_permissions(user_id)
    return permission in permissions


async def has_any_permission(user_id: str, permissions: Iterable[str]) -> bool:
    user_permissions = await get_user_permissions(user_id)
    return bool(user_permissions.intersection(set(permissions)))


async def assign_incident_role(
    user_id: str,
    role: str,
    assigned_by: str,
) -> None:
    if role not in VALID_ROLES:
        raise ValueError(f"无效的角色标识: {role}")
    async with async_session_factory() as session:
        user_exists = await session.execute(
            select(User.user_id).where(User.user_id == user_id)
        )
        if user_exists.scalar_one_or_none() is None:
            raise ValueError(f"用户 {user_id} 不存在")

        result = await session.execute(
            select(IncidentReportUserRole).where(
                IncidentReportUserRole.user_id == user_id,
                IncidentReportUserRole.role_key == role,
            ),
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            return
        entry = IncidentReportUserRole(
            id=generate_user_id(),
            user_id=user_id,
            role_key=role,
            assigned_by=assigned_by,
        )
        session.add(entry)
        await session.commit()


async def revoke_incident_role(user_id: str, role: str) -> None:
    if role not in VALID_ROLES:
        raise ValueError(f"无效的角色标识: {role}")
    async with async_session_factory() as session:
        await session.execute(
            delete(IncidentReportUserRole).where(
                IncidentReportUserRole.user_id == user_id,
                IncidentReportUserRole.role_key == role,
            ),
        )
        await session.commit()


async def list_all_role_assignments() -> list[IncidentReportUserRole]:
    async with async_session_factory() as session:
        result = await session.execute(
            select(IncidentReportUserRole).order_by(
                IncidentReportUserRole.user_id,
                IncidentReportUserRole.role_key,
            ),
        )
        return list(result.scalars().all())


async def list_non_admin_users_with_roles() -> list[dict]:
    async with async_session_factory() as session:
        result = await session.execute(
            select(User).where(User.username != "admin").order_by(User.username)
        )
        users = list(result.scalars().all())
        if not users:
            return []

        user_ids = [u.user_id for u in users]
        roles_result = await session.execute(
            select(IncidentReportUserRole).where(
                IncidentReportUserRole.user_id.in_(user_ids)
            ).order_by(
                IncidentReportUserRole.user_id,
                IncidentReportUserRole.role_key,
            )
        )
        role_map: dict[str, list[str]] = {}
        for row in roles_result.scalars().all():
            role_map.setdefault(row.user_id, []).append(row.role_key)

        return [
            {
                "user_id": u.user_id,
                "username": u.username,
                "roles": role_map.get(u.user_id, []),
            }
            for u in users
        ]


async def list_role_definitions() -> list[IncidentReportRoleDefinition]:
    async with async_session_factory() as session:
        result = await session.execute(
            select(IncidentReportRoleDefinition).order_by(
                IncidentReportRoleDefinition.role_key,
            ),
        )
        return list(result.scalars().all())


async def list_permissions() -> list[IncidentReportPermission]:
    async with async_session_factory() as session:
        result = await session.execute(
            select(IncidentReportPermission).order_by(
                IncidentReportPermission.category,
                IncidentReportPermission.permission_key,
            ),
        )
        return list(result.scalars().all())


async def list_role_permissions(role_key: str) -> list[str]:
    async with async_session_factory() as session:
        result = await session.execute(
            select(IncidentReportRolePermission.permission_key).where(
                IncidentReportRolePermission.role_key == role_key,
            ),
        )
        return [row[0] for row in result.all()]


async def get_role_permissions_map() -> dict[str, list[str]]:
    async with async_session_factory() as session:
        result = await session.execute(
            select(IncidentReportRolePermission).order_by(
                IncidentReportRolePermission.role_key,
                IncidentReportRolePermission.permission_key,
            ),
        )
        mapping: dict[str, list[str]] = {}
        for row in result.scalars().all():
            mapping.setdefault(row.role_key, []).append(row.permission_key)
        return mapping


async def seed_rbac_data() -> None:
    async with async_session_factory() as session:
        existing_roles = await session.execute(
            select(func.count(IncidentReportRoleDefinition.role_key))
        )
        if existing_roles.scalar() > 0:
            return

        for role_def in ROLE_DEFINITIONS:
            session.add(IncidentReportRoleDefinition(**role_def))

        for perm_def in PERMISSION_DEFINITIONS:
            session.add(IncidentReportPermission(**perm_def))

        await session.flush()

        for role_key, permissions in ROLE_PERMISSIONS_MAP.items():
            for perm_key in permissions:
                session.add(
                    IncidentReportRolePermission(
                        role_key=role_key,
                        permission_key=perm_key,
                    )
                )

        await session.commit()


async def ensure_incident_report_admin() -> None:
    from ...auth.models.user import User

    async with async_session_factory() as session:
        result = await session.execute(
            select(User).where(User.username == "admin").limit(1)
        )
        admin_user = result.scalar_one_or_none()
        if admin_user is None:
            return

        existing = await session.execute(
            select(IncidentReportUserRole).where(
                IncidentReportUserRole.user_id == admin_user.user_id,
                IncidentReportUserRole.role_key == "admin",
            ),
        )
        if existing.scalar_one_or_none() is not None:
            return

        entry = IncidentReportUserRole(
            id=generate_user_id(),
            user_id=admin_user.user_id,
            role_key="admin",
            assigned_by=None,
        )
        session.add(entry)
        await session.commit()
