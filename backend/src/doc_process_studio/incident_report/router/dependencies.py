from fastapi import Depends, HTTPException

from ...core.security import get_current_user_id
from ..application.ports import PermissionChecker
from ..domain.errors import PermissionDeniedError
from ..domain.permission import Permission
from ..infrastructure.dependencies import get_permission_checker


async def require_admin(
    user_id: str = Depends(get_current_user_id),
    checker: PermissionChecker = Depends(get_permission_checker),
) -> str:
    try:
        await checker.require(user_id, Permission.ROLE_MANAGE)
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=403, detail="需要管理员权限") from exc
    return user_id


async def require_verifier_or_admin(
    user_id: str = Depends(get_current_user_id),
    checker: PermissionChecker = Depends(get_permission_checker),
) -> str:
    permissions = await checker.permissions_of(user_id)
    if Permission.REPORT_AUDIT not in permissions and Permission.ROLE_MANAGE not in permissions:
        raise HTTPException(status_code=403, detail="需要审核人或管理员权限")
    return user_id
