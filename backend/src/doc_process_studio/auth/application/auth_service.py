"""认证应用服务。

用例编排：注册、登录、令牌刷新、用户信息、资料更新、密码修改、登出、删除、管理员初始化。
"""

import logging

from ...common.security.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_user_id,
    hash_password,
    verify_password,
)
from ...common.utils.dtutils import to_utc8
from ..domain.errors import (
    IncorrectPasswordError,
    InvalidCredentialsError,
    InvalidTokenError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from ..domain.roles import ROLE_ADMIN, is_admin_role
from .dtos import (
    RegisterResponse,
    TokenResponse,
    UpdateProfileResponse,
    UserInfoResponse,
)
from .ports import TokenBlacklist, UserRepository

_DEFAULT_AVATAR_COLOR = "#4f46e5"

_logger = logging.getLogger(__name__)


class AuthService:
    """认证用例服务。"""

    def __init__(
        self,
        *,
        user_repo: UserRepository,
        token_blacklist: TokenBlacklist,
        refresh_token_expire_days: int,
    ) -> None:
        self._users = user_repo
        self._blacklist = token_blacklist
        self._refresh_expire_days = refresh_token_expire_days

    async def register(self, *, username: str, password: str) -> RegisterResponse:
        if await self._users.username_exists(username):
            raise UserAlreadyExistsError("Username already exists")

        user_id = generate_user_id()
        created_at = await self._users.create(
            user_id=user_id,
            username=username,
            hashed_password=hash_password(password),
            avatar_color=_DEFAULT_AVATAR_COLOR,
        )
        return RegisterResponse(
            user_id=user_id,
            username=username,
            created_at=to_utc8(created_at),
        )

    async def authenticate(self, *, username: str, password: str) -> TokenResponse:
        record = await self._users.get_by_username(username)
        if record is None or not verify_password(password, record[2]):
            raise InvalidCredentialsError("Incorrect username or password")

        user_id, resolved_username = record[0], record[1]
        access_token = create_access_token(user_id, resolved_username)
        refresh_token = create_refresh_token(user_id)
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    async def refresh_token(self, refresh_token: str) -> TokenResponse:
        payload = decode_token(refresh_token)
        if payload is None or payload.get("type") != "refresh":
            raise InvalidTokenError("Invalid or expired refresh token")

        jti = payload.get("jti", "")
        if jti and await self._blacklist.is_blacklisted(jti):
            raise InvalidTokenError("Invalid or expired refresh token")

        user_id = payload.get("sub", "")
        record = await self._users.get_by_user_id(user_id)
        if record is None:
            raise InvalidTokenError("Invalid or expired refresh token")

        uid, username = record[0], record[1]
        new_access_token = create_access_token(uid, username)
        new_refresh_token = create_refresh_token(uid)

        if jti:
            await self._blacklist.add(jti, self._refresh_expire_days * 86400)

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
        )

    async def get_current_user_info(self, user_id: str) -> UserInfoResponse:
        record = await self._users.get_by_user_id(user_id)
        if record is None:
            raise UserNotFoundError("User not found")
        uid = record[0]
        username = record[1]
        avatar_color = record[3]
        created_at = record[4]
        role = record[5]
        return UserInfoResponse(
            user_id=uid,
            username=username,
            avatar_color=avatar_color,
            role=role,
            created_at=to_utc8(created_at),
        )

    async def update_profile(
        self,
        user_id: str,
        *,
        username: str | None = None,
        avatar_color: str | None = None,
    ) -> UpdateProfileResponse:
        current = await self._users.get_by_user_id(user_id)
        if current is None:
            raise UserNotFoundError("User not found")

        if username is not None and username != current[1] and await self._users.username_exists(username):
            raise UserAlreadyExistsError("Username already exists")

        record = await self._users.update_profile(
            user_id,
            username=username,
            avatar_color=avatar_color,
        )
        if record is None:
            raise UserNotFoundError("User not found")
        uid, resolved_username, resolved_color, created_at = record
        return UpdateProfileResponse(
            user_id=uid,
            username=resolved_username,
            avatar_color=resolved_color,
            created_at=to_utc8(created_at),
        )

    async def change_password(
        self,
        user_id: str,
        *,
        current_password: str,
        new_password: str,
    ) -> None:
        record = await self._users.get_by_user_id(user_id)
        if record is None:
            raise UserNotFoundError("User not found")
        _, _, hashed_password, _, _, _ = record
        if not verify_password(current_password, hashed_password):
            raise IncorrectPasswordError("Current password is incorrect")
        await self._users.update_password(user_id, hash_password(new_password))

    async def logout(self, *, refresh_token: str) -> None:
        payload = decode_token(refresh_token)
        if payload and payload.get("type") == "refresh":
            jti = payload.get("jti", "")
            if jti:
                await self._blacklist.add(jti, self._refresh_expire_days * 86400)

    async def delete_user(self, user_id: str) -> bool:
        return await self._users.delete_by_user_id(user_id)

    async def delete_users_by_prefix(self, prefix: str) -> int:
        return await self._users.delete_by_username_prefix(prefix)

    async def ensure_admin_user(self, *, admin_username: str, admin_password: str) -> None:
        """保证存在一个全局管理员（幂等）。

        1. **账号已存在** → 只确保它的全局 ``role='admin'``，**不动密码**。
           这是幂等兜底：即使有人手工把 role 改回 member，启动也会纠回来。
        2. **账号不存在且库为空** → 保持原有「空库初始化」语义，按
           ``ADMIN_USERNAME`` / ``ADMIN_PASSWORD`` 创建，并授予事故报告全部角色。
        3. **账号不存在但库中已有用户** → **不擅自创建**（避免 env 写错就凭空多出
           一个高权限账号），只打 ERROR 并给出可执行的修复 SQL。

        为什么不再沿用 ``count_users() > 0 就直接 return``：那个早退意味着
        「已有数据的库在启动时完全不保证存在管理员」。而系统级共享设置只能由
        管理员修改（见 ``auth.infrastructure.dependencies.require_admin``），
        一旦没有管理员就彻底没人能配密钥 —— 这是个会把人卡死的隐形状态。
        """
        existing = await self._users.get_by_username(admin_username)
        if existing is not None:
            user_id = existing[0]
            role = existing[5]
            if not is_admin_role(role):
                await self._users.set_role(user_id, ROLE_ADMIN)
                _logger.warning(
                    "已将账号 %s(user_id=%s) 的全局角色修正为 admin（原值=%r）",
                    admin_username,
                    user_id,
                    role,
                )
            return

        if await self._users.count_users() > 0:
            _logger.error(
                "未找到管理员账号 %r，但库中已有用户，因此不自动创建。"
                "请手工提权：UPDATE users SET role='admin' WHERE username='<管理员账号>';",
                admin_username,
            )
            return

        user_id = generate_user_id()
        await self._users.create(
            user_id=user_id,
            username=admin_username,
            hashed_password=hash_password(admin_password),
            avatar_color=_DEFAULT_AVATAR_COLOR,
            role=ROLE_ADMIN,
        )
        await self._users.assign_all_roles_to_admin(user_id)
        _logger.info("已创建初始管理员账号 %s(user_id=%s)", admin_username, user_id)
