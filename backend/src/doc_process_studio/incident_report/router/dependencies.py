from fastapi import Depends, HTTPException

from ...common.security.security import get_current_user_id
from ..application.ports.ports import PermissionChecker
from ..domain.values.errors import PermissionDeniedError
from ..domain.values.permission import Permission
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
