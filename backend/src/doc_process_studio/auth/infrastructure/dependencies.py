"""认证基础设施依赖装配。

提供 FastAPI 依赖注入工厂，装配应用服务单例；并提供全局管理员门禁。
"""

from functools import lru_cache

from fastapi import Depends, HTTPException

from ...common.infrastructure.config import settings
from ...common.security.security import get_current_user_id
from ..application.auth_service import AuthService
from ..application.ports import TokenBlacklist, UserRepository
from ..domain.roles import is_admin_role
from .token_blacklist import RedisTokenBlacklist
from .user_repository import SqlUserRepository


@lru_cache(maxsize=1)
def get_user_repository() -> UserRepository:
    return SqlUserRepository()


@lru_cache(maxsize=1)
def get_token_blacklist() -> TokenBlacklist:
    return RedisTokenBlacklist()


@lru_cache(maxsize=1)
def get_auth_service() -> AuthService:
    return AuthService(
        user_repo=get_user_repository(),
        token_blacklist=get_token_blacklist(),
        refresh_token_expire_days=settings.refresh_token_expire_days,
    )


async def require_admin(
    user_id: str = Depends(get_current_user_id),
    user_repo: UserRepository = Depends(get_user_repository),
) -> str:
    """全局管理员门禁（FastAPI 依赖）。

    "管理员"的定义是 ``users.role == 'admin'``（全局角色）。

    **不要**拿事故报告模块的 RBAC 来判断这里的权限：``incident_report_user_roles``
    是模块级角色，与"能否修改全系统共享设置"无关。曾经考虑过复用它，
    但那会让"给某人分配事故报告审核人"顺带获得改全局密钥的权限，语义是错的。

    未知 / 空角色一律 fail closed（视为非管理员）。
    """
    role = await user_repo.get_role(user_id)
    if not is_admin_role(role):
        raise HTTPException(status_code=403, detail="该操作需要管理员权限")
    return user_id


async def is_admin(
    user_id: str = Depends(get_current_user_id),
    user_repo: UserRepository = Depends(get_user_repository),
) -> bool:
    """「当前用户是不是全局管理员」的**软门禁**（不抛异常，返回布尔）。

    与 :func:`require_admin` 的分工：

    - 需要**放行/拦截**整个接口 → 用 ``require_admin``（越权返回 403）。
    - 需要**按身份调整响应内容** → 用本函数。典型场景：``GET /api/settings``
      对所有人都要返回 200，但只有管理员才该看到系统级共享配置段。

    判定口径与 ``require_admin`` 完全一致（``users.role == 'admin'``，
    未知/空角色一律视为非管理员），保证「能看的」和「能改的」不会出现两套标准。
    """
    return is_admin_role(await user_repo.get_role(user_id))
