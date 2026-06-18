"""认证应用层端口。

定义数据访问和外部服务抽象，由 infrastructure 层实现。
"""

from abc import ABC, abstractmethod
from datetime import datetime


class UserRepository(ABC):
    """用户仓储端口。

    元组返回顺序：(user_id, username, hashed_password, avatar_color, created_at)
    """

    @abstractmethod
    async def get_by_username(self, username: str) -> tuple[str, str, str, str, datetime] | None:
        """按用户名查询用户记录。"""

    @abstractmethod
    async def get_by_user_id(self, user_id: str) -> tuple[str, str, str, str, datetime] | None:
        """按 user_id 查询用户记录。"""

    @abstractmethod
    async def username_exists(self, username: str) -> bool:
        """判断用户名是否已存在。"""

    @abstractmethod
    async def create(self, *, user_id: str, username: str, hashed_password: str, avatar_color: str) -> datetime:
        """创建用户，返回 created_at。"""

    @abstractmethod
    async def update_profile(
        self,
        user_id: str,
        *,
        username: str | None = None,
        avatar_color: str | None = None,
    ) -> tuple[str, str, str, datetime] | None:
        """更新用户资料，返回 (user_id, username, avatar_color, created_at) 或 None。"""

    @abstractmethod
    async def update_password(self, user_id: str, hashed_password: str) -> None:
        """更新用户密码哈希。"""

    @abstractmethod
    async def delete_by_user_id(self, user_id: str) -> bool:
        """按 user_id 删除用户，返回是否删除成功。"""

    @abstractmethod
    async def delete_by_username_prefix(self, prefix: str) -> int:
        """按用户名前缀批量删除用户及其关联数据，返回删除数量。"""

    @abstractmethod
    async def count_users(self) -> int:
        """统计用户总数。"""

    @abstractmethod
    async def resolve_usernames(self, user_ids: set[str]) -> dict[str, str]:
        """解析用户 ID → 用户名映射。"""

    @abstractmethod
    async def assign_all_roles_to_admin(self, user_id: str) -> None:
        """为管理员用户分配事故报告全部角色（跨域初始化）。"""


class TokenBlacklist(ABC):
    """令牌黑名单端口。"""

    @abstractmethod
    async def is_blacklisted(self, jti: str) -> bool:
        """判断 jti 是否在黑名单中。"""

    @abstractmethod
    async def add(self, jti: str, expire_seconds: int) -> None:
        """将 jti 加入黑名单，expire_seconds 后过期。"""
