from fastapi import Depends, HTTPException

from ...core.security import get_current_user_id
from ..service.role import has_permission, has_any_permission


async def require_admin(user_id: str = Depends(get_current_user_id)) -> str:
    if not await has_permission(user_id, "role:manage"):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user_id


async def require_verifier_or_admin(user_id: str = Depends(get_current_user_id)) -> str:
    if not await has_any_permission(user_id, {"report:audit", "role:manage"}):
        raise HTTPException(status_code=403, detail="需要审核人或管理员权限")
    return user_id


async def require_report_writer(
    report_id: str,
    user_id: str = Depends(get_current_user_id),
) -> str:
    from ..service.report_store import load_report_orm
    record = await load_report_orm(report_id)
    if record is None:
        raise HTTPException(status_code=404, detail="报告不存在")
    if record.reporter_id != user_id:
        if not await has_permission(user_id, "report:delete"):
            raise HTTPException(status_code=403, detail="只有报告人或管理员可以执行此操作")
    return user_id
