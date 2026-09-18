"""settings 模块的 SQLAlchemy 仓储实现。"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy import delete, select
from sqlalchemy.engine import CursorResult

from ....common.infrastructure.database import async_session_factory
from ...application.ports import (
    StoredSecret,
    SystemSecretRepository,
    SystemSettingRepository,
    UserSettingsRepository,
)
from ..persistence.models import SystemSecret, SystemSetting, UserSettings


def _deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    """把 patch 合并进 base 的副本：两层深度，同名字段为 dict 时递归合并，否则整体替换。

    只做两层是因为偏好结构本身只有两层（如 ``models.selected``）。再加深度属于过度设计，
    真要更深的结构应该换一张表而不是把 JSON 当数据库用。
    """
    merged: dict[str, Any] = dict(base)
    for key, value in patch.items():
        current = merged.get(key)
        if isinstance(value, dict) and isinstance(current, dict):
            merged[key] = {**current, **value}
        else:
            merged[key] = value
    return merged


class SqlSystemSecretRepository(SystemSecretRepository):
    """系统级密文凭据仓储。"""

    async def get(self, secret_key: str) -> StoredSecret | None:
        async with async_session_factory() as session:
            result = await session.execute(select(SystemSecret).where(SystemSecret.secret_key == secret_key))
            row = result.scalar_one_or_none()
            if row is None:
                return None
            return StoredSecret(
                secret_key=row.secret_key,
                ciphertext=row.ciphertext,
                key_id=row.key_id,
                hint=row.hint,
                updated_at=row.updated_at,
            )

    async def upsert(
        self,
        *,
        secret_key: str,
        ciphertext: str,
        key_id: str,
        hint: str | None,
    ) -> StoredSecret:
        now = datetime.now(UTC)
        async with async_session_factory() as session:
            result = await session.execute(select(SystemSecret).where(SystemSecret.secret_key == secret_key))
            row = result.scalar_one_or_none()
            if row is None:
                row = SystemSecret(
                    secret_key=secret_key,
                    ciphertext=ciphertext,
                    key_id=key_id,
                    hint=hint,
                    created_at=now,
                    updated_at=now,
                )
                session.add(row)
            else:
                row.ciphertext = ciphertext
                row.key_id = key_id
                row.hint = hint
                row.updated_at = now
            await session.commit()
            await session.refresh(row)
            return StoredSecret(
                secret_key=row.secret_key,
                ciphertext=row.ciphertext,
                key_id=row.key_id,
                hint=row.hint,
                updated_at=row.updated_at,
            )

    async def delete(self, secret_key: str) -> bool:
        async with async_session_factory() as session:
            result = await session.execute(delete(SystemSecret).where(SystemSecret.secret_key == secret_key))
            await session.commit()
            return bool(cast(CursorResult, result).rowcount)


class SqlSystemSettingRepository(SystemSettingRepository):
    """系统级非敏感配置仓储。"""

    async def get(self, setting_key: str) -> Any | None:
        async with async_session_factory() as session:
            result = await session.execute(select(SystemSetting).where(SystemSetting.setting_key == setting_key))
            row = result.scalar_one_or_none()
            return None if row is None else row.value_json

    async def set(self, setting_key: str, value: Any) -> None:
        now = datetime.now(UTC)
        async with async_session_factory() as session:
            result = await session.execute(select(SystemSetting).where(SystemSetting.setting_key == setting_key))
            row = result.scalar_one_or_none()
            if row is None:
                session.add(SystemSetting(setting_key=setting_key, value_json=value, updated_at=now))
            else:
                row.value_json = value
                row.updated_at = now
            await session.commit()

    async def delete(self, setting_key: str) -> bool:
        async with async_session_factory() as session:
            result = await session.execute(delete(SystemSetting).where(SystemSetting.setting_key == setting_key))
            await session.commit()
            return bool(cast(CursorResult, result).rowcount)


class SqlUserSettingsRepository(UserSettingsRepository):
    """用户级偏好仓储。"""

    async def get_preferences(self, user_id: str) -> dict[str, Any]:
        async with async_session_factory() as session:
            result = await session.execute(select(UserSettings).where(UserSettings.user_id == user_id))
            row = result.scalar_one_or_none()
            if row is None or not isinstance(row.preferences, dict):
                return {}
            return dict(row.preferences)

    async def merge_preferences(self, user_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(UTC)
        async with async_session_factory() as session:
            result = await session.execute(select(UserSettings).where(UserSettings.user_id == user_id))
            row = result.scalar_one_or_none()
            if row is None:
                merged = _deep_merge({}, patch)
                session.add(
                    UserSettings(
                        user_id=user_id,
                        preferences=merged,
                        version=1,
                        created_at=now,
                        updated_at=now,
                    )
                )
            else:
                current = dict(row.preferences) if isinstance(row.preferences, dict) else {}
                merged = _deep_merge(current, patch)
                row.preferences = merged
                row.version = int(row.version or 1) + 1
                row.updated_at = now
            await session.commit()
            return merged
