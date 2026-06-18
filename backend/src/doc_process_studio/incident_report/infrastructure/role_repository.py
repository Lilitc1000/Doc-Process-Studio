"""角色管理仓储 SQLAlchemy 实现。

提供用户角色分配的查询、新增、撤销及角色/权限定义查询。
"""

import logging

from sqlalchemy import delete, func, select

from ...auth.models.user import User
from ...core.database import async_session_factory
from ...core.security import generate_user_id
from ...shared.dtutils import to_utc8
from ..application.role_ports import RoleRepository
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
from ..schemas.response import (
    IncidentPermissionEntry,
    IncidentRoleDefinitionEntry,
    IncidentRoleEntry,
)

logger = logging.getLogger(__name__)


class SqlRoleRepository(RoleRepository):
    """角色管理 SQLAlchemy 实现。"""

    async def get_user_roles(self, user_id: str) -> set[str]:
        async with async_session_factory() as session:
            result = await session.execute(
                select(IncidentReportUserRole.role_key).where(
                    IncidentReportUserRole.user_id == user_id,
                ),
            )
            return {row[0] for row in result.all()}

    async def list_assignments(self) -> list[IncidentRoleEntry]:
        async with async_session_factory() as session:
            result = await session.execute(
                select(IncidentReportUserRole).order_by(
                    IncidentReportUserRole.user_id,
                    IncidentReportUserRole.role_key,
                ),
            )
            return [
                IncidentRoleEntry(
                    user_id=row.user_id,
                    role=row.role_key,
                    assigned_by=row.assigned_by,
                    assigned_by_name=None,
                    assigned_at=to_utc8(row.assigned_at),
                )
                for row in result.scalars().all()
            ]

    async def list_users_with_roles(self) -> list[dict]:
        async with async_session_factory() as session:
            result = await session.execute(select(User).order_by(User.username))
            users = list(result.scalars().all())
            if not users:
                return []

            user_ids = [u.user_id for u in users]
            roles_result = await session.execute(
                select(IncidentReportUserRole)
                .where(IncidentReportUserRole.user_id.in_(user_ids))
                .order_by(
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

    async def assign_role(self, *, user_id: str, role: str, assigned_by: str) -> bool:
        if role not in VALID_ROLES:
            raise ValueError(f"无效的角色标识: {role}")
        async with async_session_factory() as session:
            user_exists = await session.execute(select(User.user_id).where(User.user_id == user_id))
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
                return False
            entry = IncidentReportUserRole(
                id=generate_user_id(),
                user_id=user_id,
                role_key=role,
                assigned_by=assigned_by,
            )
            session.add(entry)
            await session.commit()
            logger.info("分配角色: user_id=%s, role=%s, assigned_by=%s", user_id, role, assigned_by)
            return True

    async def revoke_role(self, *, user_id: str, role: str) -> None:
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
            logger.info("撤销角色: user_id=%s, role=%s", user_id, role)

    async def list_role_definitions(self) -> list[IncidentRoleDefinitionEntry]:
        async with async_session_factory() as session:
            result = await session.execute(
                select(IncidentReportRoleDefinition).order_by(
                    IncidentReportRoleDefinition.role_key,
                ),
            )
            return [
                IncidentRoleDefinitionEntry(
                    role_key=row.role_key,
                    role_name=row.role_name,
                    description=row.description,
                    permissions=[],
                )
                for row in result.scalars().all()
            ]

    async def list_permissions(self) -> list[IncidentPermissionEntry]:
        async with async_session_factory() as session:
            result = await session.execute(
                select(IncidentReportPermission).order_by(
                    IncidentReportPermission.category,
                    IncidentReportPermission.permission_key,
                ),
            )
            return [
                IncidentPermissionEntry(
                    permission_key=row.permission_key,
                    permission_name=row.permission_name,
                    description=row.description,
                    category=row.category,
                )
                for row in result.scalars().all()
            ]

    async def get_role_permissions_map(self) -> dict[str, list[str]]:
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

    async def seed_rbac_data(self) -> None:
        async with async_session_factory() as session:
            existing_roles = await session.execute(select(func.count(IncidentReportRoleDefinition.role_key)))
            if (existing_roles.scalar() or 0) > 0:
                for perm_def in PERMISSION_DEFINITIONS:
                    existing_perm = await session.execute(
                        select(IncidentReportPermission).where(
                            IncidentReportPermission.permission_key == perm_def["permission_key"]
                        )
                    )
                    if existing_perm.scalar_one_or_none() is None:
                        session.add(IncidentReportPermission(**perm_def))

                for role_key, permissions in ROLE_PERMISSIONS_MAP.items():
                    for perm_key in permissions:
                        existing_mapping = await session.execute(
                            select(IncidentReportRolePermission).where(
                                IncidentReportRolePermission.role_key == role_key,
                                IncidentReportRolePermission.permission_key == perm_key,
                            )
                        )
                        if existing_mapping.scalar_one_or_none() is None:
                            session.add(
                                IncidentReportRolePermission(
                                    role_key=role_key,
                                    permission_key=perm_key,
                                )
                            )

                await session.commit()
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
            logger.info("RBAC 种子数据初始化完成")

    async def ensure_admin_role(self) -> None:
        async with async_session_factory() as session:
            result = await session.execute(select(User).where(User.username == "admin").limit(1))
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
            logger.info("确保管理员角色: user_id=%s", admin_user.user_id)
