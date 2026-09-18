"""settings 模块 ORM 映射。

三张表的分工（这个划分是刻意的，不要合并）：

- ``system_settings`` —— 系统级**非敏感**配置，值直接是 JSON 标量（如 ``"http://..."``、``true``）
- ``system_secrets``  —— 系统级**密文**凭据，明文永不落库
- ``user_settings``   —— 用户级**非敏感**偏好

把密文单独放一张表，是为了让"敏感值不可能被误序列化进 API 响应"成为**结构保证**，
而不是靠"记得在 DTO 里排除那个字段"这种代码纪律。
"""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ....common.infrastructure.database import Base


class SystemSetting(Base):
    """系统级非敏感配置（key → JSON 标量/对象）。"""

    __tablename__ = "system_settings"

    setting_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    #: ``value_json`` 直接存 JSON 标量，例如 ``"http://s.example:10108"``、``true``
    value_json: Mapped[Any] = mapped_column(JSONB, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SystemSecret(Base):
    """系统级密文凭据。"""

    __tablename__ = "system_secrets"

    secret_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    #: 格式 ``v1:<key_id>:<nonce_b64url>:<ciphertext_b64url>``
    ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    key_id: Mapped[str] = mapped_column(String(16), nullable=False)
    #: 掩码展示用的尾串（仅当明文 >= 24 字符时写入）
    hint: Mapped[str | None] = mapped_column(String(8), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        """显式覆盖 repr，避免密文被顺手打进日志或异常回溯。"""
        return f"<SystemSecret secret_key={self.secret_key!r} key_id={self.key_id!r}>"


class UserSettings(Base):
    """用户级非敏感偏好。"""

    __tablename__ = "user_settings"

    user_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    preferences: Mapped[Any] = mapped_column(JSONB, nullable=False)
    #: 每次写入 +1，作为"配置已变更"的信号
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
