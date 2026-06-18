"""权限检查辅助函数。

提供基于字符串的权限检查入口，内部委托给 RbacPermissionChecker。
供 service 层（generation/preview）使用。
"""

from ..domain.permission import Permission
from .permission_checker import RbacPermissionChecker

_checker: RbacPermissionChecker | None = None


def _get_checker() -> RbacPermissionChecker:
    global _checker
    if _checker is None:
        _checker = RbacPermissionChecker()
    return _checker


async def has_permission(user_id: str, permission: str) -> bool:
    """检查用户是否拥有指定权限（字符串形式）。"""
    checker = _get_checker()
    try:
        perm = Permission(permission)
    except ValueError:
        return False
    return perm in await checker.permissions_of(user_id)


async def has_any_permission(user_id: str, permissions: set[str]) -> bool:
    """检查用户是否拥有给定权限中的任意一个。"""
    checker = _get_checker()
    user_perms = await checker.permissions_of(user_id)
    for p in permissions:
        try:
            perm = Permission(p)
        except ValueError:
            continue
        if perm in user_perms:
            return True
    return False
