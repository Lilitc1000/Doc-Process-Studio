"""认证基础设施依赖装配。

提供 FastAPI 依赖注入工厂，装配应用服务单例。
"""

from functools import lru_cache

from ...core.config import settings
from ..application.auth_service import AuthService
from ..application.ports import TokenBlacklist, UserRepository
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
