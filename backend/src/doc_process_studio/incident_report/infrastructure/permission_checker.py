"""RBAC 权限检查器实现。

实现 PermissionChecker 端口：查询用户角色并映射到权限集合。
"""

import logging

from sqlalchemy import select

from ...common.infrastructure.database import async_session_factory
from ..application.ports.ports import PermissionChecker
from ..domain.values.permission import ROLE_PERMISSIONS, Permission, Role
from .persistence.incident_report_role import IncidentReportUserRole

logger = logging.getLogger(__name__)


class RbacPermissionChecker(PermissionChecker):
    """RBAC 权限检查器：查询用户角色 → 映射到权限集合。"""

    async def _get_user_roles(self, user_id: str) -> set[str]:
        async with async_session_factory() as session:
            result = await session.execute(
                select(IncidentReportUserRole.role_key).where(
                    IncidentReportUserRole.user_id == user_id,
                ),
            )
            return {row[0] for row in result.all()}

    async def permissions_of(self, user_id: str) -> set[Permission]:
        user_roles = await self._get_user_roles(user_id)
        if not user_roles:
            return set()
        permissions: set[Permission] = set()
        for role_key in user_roles:
            try:
                role = Role(role_key)
            except ValueError:
                continue
            role_perms = ROLE_PERMISSIONS.get(role, set())
            permissions.update(role_perms)
        return permissions
