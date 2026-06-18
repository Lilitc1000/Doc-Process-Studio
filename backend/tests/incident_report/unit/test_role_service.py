"""RoleService 单元测试。

覆盖角色查询、分配、撤销、权限查询等用例的编排逻辑，
使用桩端口隔离基础设施。
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

from doc_process_studio.incident_report.application.role_service import RoleService
from doc_process_studio.incident_report.domain.permission import Permission
from doc_process_studio.incident_report.schemas.response import (
    IncidentPermissionEntry,
    IncidentRoleDefinitionEntry,
    IncidentRoleEntry,
)


def _make_service(
    *,
    roles: set[str] | None = None,
    permissions: set[Permission] | None = None,
    assignments: list[IncidentRoleEntry] | None = None,
    users_with_roles: list[dict] | None = None,
    usernames: dict[str, str] | None = None,
    role_defs: list[IncidentRoleDefinitionEntry] | None = None,
    perms_defs: list[IncidentPermissionEntry] | None = None,
    role_perms_map: dict[str, list[str]] | None = None,
) -> RoleService:
    role_repo = AsyncMock()
    role_repo.get_user_roles = AsyncMock(return_value=roles or set())
    role_repo.list_assignments = AsyncMock(return_value=assignments or [])
    role_repo.list_users_with_roles = AsyncMock(return_value=users_with_roles or [])
    role_repo.list_role_definitions = AsyncMock(return_value=role_defs or [])
    role_repo.list_permissions = AsyncMock(return_value=perms_defs or [])
    role_repo.get_role_permissions_map = AsyncMock(return_value=role_perms_map or {})

    checker = AsyncMock()
    checker.permissions_of = AsyncMock(return_value=permissions or set())

    user_dir = AsyncMock()
    user_dir.resolve_usernames = AsyncMock(return_value=usernames or {})

    return RoleService(role_repo, checker, user_dir)


# ---- get_my_permissions ----
async def test_get_my_permissions_returns_sorted_roles_and_permissions():
    service = _make_service(
        roles={"reporter", "viewer"},
        permissions={Permission.REPORT_VIEW, Permission.REPORT_CREATE},
    )
    result = await service.get_my_permissions(user_id="usr_1")
    assert result.user_id == "usr_1"
    assert result.roles == ["reporter", "viewer"]
    assert result.permissions == ["report:create", "report:view"]


async def test_get_my_permissions_empty():
    service = _make_service()
    result = await service.get_my_permissions(user_id="usr_1")
    assert result.roles == []
    assert result.permissions == []


# ---- list_role_assignments ----
async def test_list_assignments_resolves_assigned_by_name():
    now = datetime.now(UTC)
    assignment = IncidentRoleEntry(
        user_id="usr_1",
        role="reporter",
        assigned_by="usr_admin",
        assigned_by_name=None,
        assigned_at=now,
    )
    service = _make_service(assignments=[assignment], usernames={"usr_admin": "管理员"})
    result = await service.list_role_assignments()
    assert len(result.items) == 1
    entry = result.items[0]
    assert entry.user_id == "usr_1"
    assert entry.role == "reporter"
    assert entry.assigned_by == "usr_admin"
    assert entry.assigned_by_name == "管理员"


async def test_list_assignments_assigned_by_none_keeps_name_none():
    assignment = IncidentRoleEntry(
        user_id="usr_1",
        role="reporter",
        assigned_by=None,
        assigned_by_name=None,
        assigned_at=datetime.now(UTC),
    )
    service = _make_service(assignments=[assignment])
    result = await service.list_role_assignments()
    assert result.items[0].assigned_by_name is None


async def test_list_assignments_empty():
    service = _make_service()
    result = await service.list_role_assignments()
    assert result.items == []


# ---- list_users_with_roles ----
async def test_list_users_with_roles_maps_users():
    service = _make_service(
        users_with_roles=[
            {"user_id": "usr_1", "username": "张三", "roles": ["reporter"]},
            {"user_id": "usr_2", "username": "李四", "roles": ["viewer", "handler"]},
        ]
    )
    result = await service.list_users_with_roles()
    assert len(result.items) == 2
    assert result.items[0].user_id == "usr_1"
    assert result.items[1].roles == ["viewer", "handler"]


async def test_list_users_with_roles_empty():
    service = _make_service()
    result = await service.list_users_with_roles()
    assert result.items == []


# ---- assign_role / revoke_role ----
async def test_assign_role_delegates_to_repo_and_resolves_name():
    service = _make_service(usernames={"usr_admin": "管理员"})
    result = await service.assign_role(user_id="usr_1", role="reporter", assigned_by="usr_admin")
    service._role_repo.assign_role.assert_awaited_once_with(
        user_id="usr_1", role="reporter", assigned_by="usr_admin"
    )
    assert result.user_id == "usr_1"
    assert result.role == "reporter"
    assert result.assigned_by == "usr_admin"
    assert result.assigned_by_name == "管理员"


async def test_revoke_role_delegates_to_repo():
    service = _make_service()
    await service.revoke_role(user_id="usr_1", role="reporter")
    service._role_repo.revoke_role.assert_awaited_once_with(
        user_id="usr_1", role="reporter"
    )


# ---- list_role_definitions / list_permissions ----
async def test_list_role_definitions_with_permissions_map():
    defs = [
        IncidentRoleDefinitionEntry(
            role_key="reporter", role_name="报告人", description="创建报告", permissions=[]
        ),
        IncidentRoleDefinitionEntry(
            role_key="viewer", role_name="观察者", description="仅查看", permissions=[]
        ),
    ]
    service = _make_service(
        role_defs=defs,
        role_perms_map={"reporter": ["report:create", "report:view"], "viewer": []},
    )
    result = await service.list_role_definitions()
    assert len(result.items) == 2
    assert result.items[0].role_key == "reporter"
    assert result.items[0].permissions == ["report:create", "report:view"]
    assert result.items[1].permissions == []


async def test_list_permissions_maps_entries():
    perms = [
        IncidentPermissionEntry(
            permission_key="report:create",
            permission_name="创建报告",
            description="创建新报告",
            category="report",
        )
    ]
    service = _make_service(perms_defs=perms)
    result = await service.list_permissions()
    assert len(result.items) == 1
    assert result.items[0].permission_key == "report:create"
    assert result.items[0].category == "report"
