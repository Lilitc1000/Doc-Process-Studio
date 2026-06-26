"""角色管理应用服务。

提供角色查询、分配、撤销及权限查询用例。
"""

from ..dtos import (
    IncidentPermissionListResponse,
    IncidentRoleDefinitionListResponse,
    IncidentRoleEntry,
    IncidentRoleListResponse,
    IncidentUserPermissionsResponse,
    IncidentUserWithRolesEntry,
    IncidentUserWithRolesListResponse,
)
from ..ports import PermissionChecker, UserDirectory
from ..ports.role_ports import RoleRepository


class RoleService:
    """角色管理用例：查询/分配/撤销角色 + 权限查询。"""

    def __init__(
        self,
        role_repo: RoleRepository,
        checker: PermissionChecker,
        user_dir: UserDirectory,
    ) -> None:
        self._role_repo = role_repo
        self._checker = checker
        self._user_dir = user_dir

    async def get_my_permissions(self, *, user_id: str) -> IncidentUserPermissionsResponse:
        roles = await self._role_repo.get_user_roles(user_id)
        permissions = await self._checker.permissions_of(user_id)
        return IncidentUserPermissionsResponse(
            user_id=user_id,
            roles=sorted(roles),
            permissions=sorted(p.value for p in permissions),
        )

    async def list_role_assignments(self) -> IncidentRoleListResponse:
        assignments = await self._role_repo.list_assignments()
        assigned_by_ids = {a.assigned_by for a in assignments if a.assigned_by}
        usernames = await self._user_dir.resolve_usernames(assigned_by_ids)
        items = [
            a.model_copy(update={"assigned_by_name": usernames.get(a.assigned_by) if a.assigned_by else None})
            for a in assignments
        ]
        return IncidentRoleListResponse(items=items)

    async def list_users_with_roles(self) -> IncidentUserWithRolesListResponse:
        users = await self._role_repo.list_users_with_roles()
        items = [
            IncidentUserWithRolesEntry(
                user_id=u["user_id"],
                username=u["username"],
                roles=u["roles"],
            )
            for u in users
        ]
        return IncidentUserWithRolesListResponse(items=items)

    async def assign_role(self, *, user_id: str, role: str, assigned_by: str) -> IncidentRoleEntry:
        await self._role_repo.assign_role(user_id=user_id, role=role, assigned_by=assigned_by)
        admin_names = await self._user_dir.resolve_usernames({assigned_by})
        return IncidentRoleEntry(
            user_id=user_id,
            role=role,
            assigned_by=assigned_by,
            assigned_by_name=admin_names.get(assigned_by),
        )

    async def revoke_role(self, *, user_id: str, role: str) -> None:
        await self._role_repo.revoke_role(user_id=user_id, role=role)

    async def list_role_definitions(self) -> IncidentRoleDefinitionListResponse:
        definitions = await self._role_repo.list_role_definitions()
        role_perms_map = await self._role_repo.get_role_permissions_map()
        items = [d.model_copy(update={"permissions": role_perms_map.get(d.role_key, [])}) for d in definitions]
        return IncidentRoleDefinitionListResponse(items=items)

    async def list_permissions(self) -> IncidentPermissionListResponse:
        perms = await self._role_repo.list_permissions()
        return IncidentPermissionListResponse(items=perms)
