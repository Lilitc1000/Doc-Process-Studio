"""认证应用服务契约。

定义应用服务对外暴露的调用接口，测试桩类继承此契约以确保签名同步。
运行时实例化桩类会自动检测未实现的抽象方法。
"""

from abc import ABC, abstractmethod

from .dtos import (
    RegisterResponse,
    TokenResponse,
    UpdateProfileResponse,
    UserInfoResponse,
)


class AuthServiceContract(ABC):
    """认证用例服务契约。"""

    @abstractmethod
    async def register(self, *, username: str, password: str) -> RegisterResponse: ...

    @abstractmethod
    async def authenticate(self, *, username: str, password: str) -> TokenResponse: ...

    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> TokenResponse: ...

    @abstractmethod
    async def get_current_user_info(self, user_id: str) -> UserInfoResponse: ...

    @abstractmethod
    async def update_profile(
        self,
        user_id: str,
        *,
        username: str | None = None,
        avatar_color: str | None = None,
    ) -> UpdateProfileResponse: ...

    @abstractmethod
    async def change_password(
        self,
        user_id: str,
        *,
        current_password: str,
        new_password: str,
    ) -> None: ...

    @abstractmethod
    async def logout(self, *, refresh_token: str) -> None: ...

    @abstractmethod
    async def delete_user(self, user_id: str) -> bool: ...

    @abstractmethod
    async def delete_users_by_prefix(self, prefix: str) -> int: ...

    @abstractmethod
    async def ensure_admin_user(self, *, admin_username: str, admin_password: str) -> None: ...
