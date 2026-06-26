"""角色管理仓储端口。"""

from abc import ABC, abstractmethod

from ..dtos import (
    IncidentPermissionEntry,
    IncidentRoleDefinitionEntry,
    IncidentRoleEntry,
)


class RoleRepository(ABC):
    """角色管理仓储端口。"""

    @abstractmethod
    async def get_user_roles(self, user_id: str) -> set[str]:
        """查询用户拥有的角色集合。"""

    @abstractmethod
    async def list_assignments(self) -> list[IncidentRoleEntry]:
        """查询全部角色分配记录，返回 DTO。"""

    @abstractmethod
    async def list_users_with_roles(self) -> list[dict]:
        """查询全部用户及其角色（含用户名）。"""

    @abstractmethod
    async def assign_role(self, *, user_id: str, role: str, assigned_by: str) -> bool:
        """分配角色（已存在则跳过），返回是否新增。"""

    @abstractmethod
    async def revoke_role(self, *, user_id: str, role: str) -> None:
        """撤销角色。"""

    @abstractmethod
    async def list_role_definitions(self) -> list[IncidentRoleDefinitionEntry]:
        """查询角色定义列表，返回 DTO。"""

    @abstractmethod
    async def list_permissions(self) -> list[IncidentPermissionEntry]:
        """查询权限定义列表，返回 DTO。"""

    @abstractmethod
    async def get_role_permissions_map(self) -> dict[str, list[str]]:
        """查询角色-权限映射。"""

    @abstractmethod
    async def seed_rbac_data(self) -> None:
        """初始化 RBAC 种子数据。"""

    @abstractmethod
    async def ensure_admin_role(self) -> None:
        """确保 admin 用户拥有 admin 角色。"""
