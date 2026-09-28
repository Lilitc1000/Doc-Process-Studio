"""认证应用服务。

用例编排：注册、登录、令牌刷新、用户信息、资料更新、密码修改、登出、删除、管理员初始化。
"""

import logging

from sqlalchemy.exc import IntegrityError

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
    AdminAlreadyExistsError,
    IncorrectPasswordError,
    InvalidCredentialsError,
    InvalidTokenError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from ..domain.roles import ROLE_ADMIN
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

    async def needs_setup(self) -> bool:
        """系统是否还没有任何全局管理员（前端据此引导到 setup 页还是登录页）。"""
        return not await self._users.has_admin()

    async def setup_admin(self, *, username: str, password: str) -> RegisterResponse:
        """创建第一个管理员（仅当系统中不存在任何全局管理员时可用）。

        管理员不再来自 ``ADMIN_USERNAME`` / ``ADMIN_PASSWORD`` 配置：部署者首次
        访问时在前端 setup 页自行设定用户名与密码。创建成功即授予事故报告全部
        角色（接管原启动期 ``ensure_admin_role`` 的职责），无需重启。
        """
        if await self._users.has_admin():
            raise AdminAlreadyExistsError("系统已完成初始化，管理员已存在")
        if await self._users.username_exists(username):
            raise UserAlreadyExistsError("Username already exists")

        user_id = generate_user_id()
        try:
            created_at = await self._users.create(
                user_id=user_id,
                username=username,
                hashed_password=hash_password(password),
                avatar_color=_DEFAULT_AVATAR_COLOR,
                role=ROLE_ADMIN,
            )
        except IntegrityError as exc:
            # 并发初始化兜底：另一个请求可能已抢先建号。此时若已有管理员则视为
            # setup 已完成，否则按用户名冲突处理。（两个请求用不同用户名同时穿过
            # has_admin 检查的窗口理论上存在，但只出现在"全新空库 + 首次并发注册"
            # 的极端场景，结果也只是多一个管理员，不构成权限提升。）
            if await self._users.has_admin():
                raise AdminAlreadyExistsError("系统已完成初始化，管理员已存在") from exc
            raise UserAlreadyExistsError("Username already exists") from exc

        _logger.info("已创建初始管理员账号 %s(user_id=%s)", username, user_id)
        # assign_all_roles_to_admin 已幂等（ON CONFLICT DO NOTHING）；
        # 事故报告全部角色在这里一并授予（原启动期 ensure_admin_role 的职责）。
        await self._users.assign_all_roles_to_admin(user_id)
        return RegisterResponse(user_id=user_id, username=username, created_at=to_utc8(created_at))
