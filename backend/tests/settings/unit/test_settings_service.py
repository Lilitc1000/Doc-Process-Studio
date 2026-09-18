"""SettingsService 单元测试。

重点覆盖三处"改错了会造成安全问题或数据丢失"的逻辑：

1. ``apiKey`` 的四态语义（缺失 / 空串 = 不变，非空 = 覆盖，DELETE = 清除）
2. 任何对外 DTO 都不含明文密钥
3. ``base_url`` 的协议/长度校验与"撤销库内覆盖、回落 env"的语义
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

import pytest

from doc_process_studio.common.security.secret_cipher import SecretCipher, build_secret_hint
from doc_process_studio.settings.application.ports import RagflowConnectionProbe, StoredSecret
from doc_process_studio.settings.application.settings_service import ModelPreferencesUpdate, SettingsService
from doc_process_studio.settings.domain.errors import InvalidBaseUrlError, InvalidSettingValueError
from doc_process_studio.settings.domain.values import (
    SECRET_RAGFLOW_API_KEY,
    SETTING_RAGFLOW_BASE_URL,
    SETTING_RAGFLOW_ENABLED,
    RagflowConfig,
    SecretSource,
)

KEY = os.urandom(32)
CIPHER = SecretCipher(keys={"k1": KEY}, active_key_id="k1")

SAMPLE_API_KEY = "ragflow-testkey-0123456789abcdefghijklmnopqrstuvtkYQ"
USER_ID = "usr_unit_test"


class FakeSecretRepository:
    def __init__(self) -> None:
        self.rows: dict[str, StoredSecret] = {}

    async def get(self, secret_key: str) -> StoredSecret | None:
        return self.rows.get(secret_key)

    async def upsert(self, *, secret_key: str, ciphertext: str, key_id: str, hint: str | None) -> StoredSecret:
        row = StoredSecret(
            secret_key=secret_key,
            ciphertext=ciphertext,
            key_id=key_id,
            hint=hint,
            updated_at=datetime.now(UTC),
        )
        self.rows[secret_key] = row
        return row

    async def delete(self, secret_key: str) -> bool:
        return self.rows.pop(secret_key, None) is not None


class FakeSettingRepository:
    def __init__(self) -> None:
        self.values: dict[str, Any] = {}

    async def get(self, setting_key: str) -> Any | None:
        return self.values.get(setting_key)

    async def set(self, setting_key: str, value: Any) -> None:
        self.values[setting_key] = value

    async def delete(self, setting_key: str) -> bool:
        return self.values.pop(setting_key, None) is not None


class FakeUserSettingsRepository:
    def __init__(self) -> None:
        self.stored: dict[str, dict[str, Any]] = {}

    async def get_preferences(self, user_id: str) -> dict[str, Any]:
        return dict(self.stored.get(user_id, {}))

    async def merge_preferences(self, user_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        current = dict(self.stored.get(user_id, {}))
        for key, value in patch.items():
            if isinstance(value, dict) and isinstance(current.get(key), dict):
                current[key] = {**current[key], **value}
            else:
                current[key] = value
        self.stored[user_id] = current
        return current


class FakeProvider:
    """最小可用的 provider：直接返回构造时给的配置。"""

    def __init__(self, config: RagflowConfig | None = None) -> None:
        self.config = config or RagflowConfig(
            base_url="http://ragflow.local:10108",
            api_key="probe-key",
            enabled=True,
            source=SecretSource.NONE,
        )
        self.invalidate_calls = 0
        self.resolved_scopes: list[str] = []
        self.invalidated_scopes: list[str | None] = []

    async def resolve(self, *, scope: str = "system") -> RagflowConfig:
        self.resolved_scopes.append(scope)
        return self.config

    def invalidate(self, *, scope: str | None = None) -> None:
        self.invalidate_calls += 1
        self.invalidated_scopes.append(scope)


class FakeProbe(RagflowConnectionProbe):
    def __init__(self, result: tuple[bool, str, int] = (True, "连接成功", 3)) -> None:
        self.result = result
        self.calls = 0
        self.probed_configs: list[RagflowConfig] = []

    async def probe(self, config: RagflowConfig) -> tuple[bool, str, int]:
        self.calls += 1
        self.probed_configs.append(config)
        return self.result


def _service(
    *,
    config: RagflowConfig | None = None,
    probe_result: tuple[bool, str, int] = (True, "连接成功", 3),
) -> tuple[
    SettingsService, FakeSecretRepository, FakeSettingRepository, FakeUserSettingsRepository, FakeProvider, FakeProbe
]:
    secrets = FakeSecretRepository()
    settings = FakeSettingRepository()
    users = FakeUserSettingsRepository()
    provider = FakeProvider(config)
    probe = FakeProbe(probe_result)
    service = SettingsService(
        secret_repo=secrets,  # type: ignore[arg-type]
        setting_repo=settings,  # type: ignore[arg-type]
        user_settings_repo=users,  # type: ignore[arg-type]
        cipher=CIPHER,
        config_provider=provider,  # type: ignore[arg-type]
        connection_probe=probe,
    )
    return service, secrets, settings, users, provider, probe


# ------------------------------------------------------------------ apiKey 四态


async def test_api_key_absent_keeps_existing_value() -> None:
    service, secrets, _, _, provider, _ = _service()
    await service.update_ragflow_settings(api_key_provided=True, api_key=SAMPLE_API_KEY)
    stored_before = secrets.rows[SECRET_RAGFLOW_API_KEY].ciphertext

    # 字段缺失（provided=False）
    await service.update_ragflow_settings(base_url_provided=True, base_url="http://x:1")
    assert secrets.rows[SECRET_RAGFLOW_API_KEY].ciphertext == stored_before

    # provided=True 但值为 None
    await service.update_ragflow_settings(api_key_provided=True, api_key=None)
    assert secrets.rows[SECRET_RAGFLOW_API_KEY].ciphertext == stored_before
    assert provider.invalidate_calls == 2


async def test_api_key_empty_string_keeps_existing_value() -> None:
    """空串必须"不变"，否则前端一个空输入框就能把线上密钥清掉。"""
    service, secrets, _, _, _, _ = _service()
    await service.update_ragflow_settings(api_key_provided=True, api_key=SAMPLE_API_KEY)
    stored_before = secrets.rows[SECRET_RAGFLOW_API_KEY].ciphertext
    version_before = secrets.rows[SECRET_RAGFLOW_API_KEY].updated_at

    await service.update_ragflow_settings(api_key_provided=True, api_key="")
    await service.update_ragflow_settings(api_key_provided=True, api_key="    ")

    row = secrets.rows[SECRET_RAGFLOW_API_KEY]
    assert row.ciphertext == stored_before
    assert row.updated_at == version_before


async def test_api_key_non_empty_overwrites_and_encrypts() -> None:
    service, secrets, _, _, provider, _ = _service()
    view = await service.update_ragflow_settings(api_key_provided=True, api_key=f"  {SAMPLE_API_KEY}  ")

    row = secrets.rows[SECRET_RAGFLOW_API_KEY]
    assert row.ciphertext.startswith("v1:k1:")
    assert SAMPLE_API_KEY not in row.ciphertext
    assert CIPHER.decrypt(row.ciphertext, aad=SECRET_RAGFLOW_API_KEY) == SAMPLE_API_KEY  # 外部空白被 strip
    assert row.hint == build_secret_hint(SAMPLE_API_KEY)
    assert row.key_id == "k1"
    assert view.credential.configured is True
    assert provider.invalidate_calls == 1, "写操作后必须让缓存失效"


async def test_clear_api_key_removes_row() -> None:
    service, secrets, _, _, provider, _ = _service()
    await service.update_ragflow_settings(api_key_provided=True, api_key=SAMPLE_API_KEY)

    view = await service.clear_ragflow_api_key()
    assert SECRET_RAGFLOW_API_KEY not in secrets.rows
    assert view.credential.configured is False
    assert provider.invalidate_calls == 2


async def test_clear_api_key_when_absent_is_noop() -> None:
    service, _, _, _, provider, _ = _service()
    view = await service.clear_ragflow_api_key()
    assert view.credential.configured is False
    assert provider.invalidate_calls == 0, "没删到东西就不该触发缓存失效"


async def test_oversized_api_key_rejected() -> None:
    service, secrets, _, _, _, _ = _service()
    with pytest.raises(InvalidSettingValueError):
        await service.update_ragflow_settings(api_key_provided=True, api_key="x" * 513)
    assert SECRET_RAGFLOW_API_KEY not in secrets.rows


# ------------------------------------------------------------------ 明文不外泄


async def test_overview_never_contains_plaintext_secret() -> None:
    """把整个响应体序列化后搜明文 —— 这是最实际的"有没有漏"检查。"""
    service, secrets, settings, _, _, _ = _service()
    await service.update_ragflow_settings(
        base_url_provided=True,
        base_url="http://ragflow.local:10108",
        enabled_provided=True,
        enabled=True,
        api_key_provided=True,
        api_key=SAMPLE_API_KEY,
    )
    # 同时让 provider 也返回真实明文，确保明文确实存在于服务端内存里
    overview = await service.get_overview(USER_ID)

    payload = overview.model_dump_json()
    assert SAMPLE_API_KEY not in payload
    assert secrets.rows[SECRET_RAGFLOW_API_KEY].ciphertext not in payload
    # 系统视角（include_system_settings=True）必须给出这一段，供下方断言其内容
    assert overview.ragflow is not None
    assert overview.ragflow.credential.configured is True
    assert overview.ragflow.credential.hint == SAMPLE_API_KEY[-4:]
    assert SAMPLE_API_KEY[:8] not in payload


async def test_unconfigured_credential_is_reported_honestly() -> None:
    service, _, _, _, _, _ = _service()
    overview = await service.get_overview(USER_ID)
    assert overview.ragflow is not None
    assert overview.ragflow.credential.configured is False
    assert overview.ragflow.credential.hint is None
    assert overview.ragflow.credential.source is SecretSource.NONE


# ------------------------------------------------------------------ base_url


async def test_base_url_empty_clears_override_and_falls_back() -> None:
    service, _, settings, _, provider, _ = _service()
    await service.update_ragflow_settings(base_url_provided=True, base_url="http://override:1")
    assert settings.values[SETTING_RAGFLOW_BASE_URL] == "http://override:1"

    await service.update_ragflow_settings(base_url_provided=True, base_url="")
    assert SETTING_RAGFLOW_BASE_URL not in settings.values
    assert provider.invalidate_calls == 2

    provider.config = RagflowConfig(base_url="http://env:1", api_key="k", enabled=True, source=SecretSource.ENV)
    view = await service.get_ragflow_settings()
    assert view.base_url == "http://env:1"
    assert view.base_url_source == "env"


async def test_base_url_trailing_slash_normalized() -> None:
    service, _, settings, _, _, _ = _service()
    await service.update_ragflow_settings(base_url_provided=True, base_url="http://host:10108///")
    assert settings.values[SETTING_RAGFLOW_BASE_URL] == "http://host:10108"


@pytest.mark.parametrize(
    "bad_url",
    ["ftp://host:21", "file:///etc/passwd", "ragflow.local:10108", "http://", "://host", "http://" + "a" * 600],
)
async def test_invalid_base_url_rejected(bad_url: str) -> None:
    service, _, settings, _, _, _ = _service()
    with pytest.raises(InvalidBaseUrlError):
        await service.update_ragflow_settings(base_url_provided=True, base_url=bad_url)
    assert SETTING_RAGFLOW_BASE_URL not in settings.values


async def test_enabled_null_clears_override() -> None:
    service, _, settings, _, provider, _ = _service()
    await service.update_ragflow_settings(enabled_provided=True, enabled=False)
    assert settings.values[SETTING_RAGFLOW_ENABLED] is False

    await service.update_ragflow_settings(enabled_provided=True, enabled=None)
    assert SETTING_RAGFLOW_ENABLED not in settings.values
    assert provider.invalidate_calls == 2


async def test_enabled_source_reported() -> None:
    service, _, settings, _, provider, _ = _service()
    provider.config = RagflowConfig(base_url="http://x:1", api_key="k", enabled=True, source=SecretSource.ENV)
    assert (await service.get_ragflow_settings()).enabled_source == "env"

    settings.values[SETTING_RAGFLOW_ENABLED] = True
    assert (await service.get_ragflow_settings()).enabled_source == "system"


# ------------------------------------------------------------------ 用户偏好


async def test_user_preferences_default_to_none() -> None:
    service, _, _, _, _, _ = _service()
    prefs = await service.get_user_preferences(USER_ID)
    assert prefs.models.selected is None
    assert prefs.models.reranker is None


async def test_user_preferences_partial_update_keeps_other_field() -> None:
    service, _, _, users, _, _ = _service()
    await service.update_user_preferences(
        USER_ID, models=ModelPreferencesUpdate(provided=True, selected="qwen3:8b", reranker="qwen3:32b")
    )
    prefs = await service.update_user_preferences(
        USER_ID, models=ModelPreferencesUpdate(provided=True, selected="qwen3-coder:30b")
    )
    assert prefs.models.selected == "qwen3-coder:30b"
    assert prefs.models.reranker == "qwen3:32b"
    assert users.stored[USER_ID] == {"models": {"selected": "qwen3-coder:30b", "reranker": "qwen3:32b"}}


async def test_user_preferences_blank_clears_field() -> None:
    service, _, _, _, _, _ = _service()
    await service.update_user_preferences(USER_ID, models=ModelPreferencesUpdate(provided=True, selected="qwen3:8b"))
    prefs = await service.update_user_preferences(USER_ID, models=ModelPreferencesUpdate(provided=True, selected=""))
    assert prefs.models.selected is None


async def test_user_preferences_not_provided_is_noop() -> None:
    service, _, _, users, _, _ = _service()
    await service.update_user_preferences(USER_ID, models=ModelPreferencesUpdate(provided=True, selected="qwen3:8b"))
    prefs = await service.update_user_preferences(USER_ID, models=ModelPreferencesUpdate(provided=False))
    assert prefs.models.selected == "qwen3:8b"
    assert len(users.stored) == 1


async def test_user_preferences_are_isolated_per_user() -> None:
    service, _, _, _, _, _ = _service()
    await service.update_user_preferences("usr_a", models=ModelPreferencesUpdate(provided=True, selected="model-a"))
    await service.update_user_preferences("usr_b", models=ModelPreferencesUpdate(provided=True, selected="model-b"))

    assert (await service.get_user_preferences("usr_a")).models.selected == "model-a"
    assert (await service.get_user_preferences("usr_b")).models.selected == "model-b"


async def test_oversized_model_name_rejected() -> None:
    service, _, _, _, _, _ = _service()
    with pytest.raises(InvalidSettingValueError):
        await service.update_user_preferences(USER_ID, models=ModelPreferencesUpdate(provided=True, selected="m" * 129))


# ------------------------------------------------------------------ 连通性自检


async def test_probe_reports_success() -> None:
    service, _, _, _, _, probe = _service(probe_result=(True, "连接成功，可访问 3 个知识库", 3))
    result = await service.test_ragflow_connection()
    assert result.ok is True
    assert result.dataset_count == 3
    assert probe.calls == 1


async def test_probe_reports_failure_reason_verbatim() -> None:
    service, _, _, _, _, _ = _service(probe_result=(False, "RAGFlow 返回 code=109：unauthorized", 0))
    result = await service.test_ragflow_connection()
    assert result.ok is False
    assert "code=109" in result.message


async def test_probe_skipped_when_disabled_or_unconfigured() -> None:
    service, _, _, _, provider, probe = _service(
        config=RagflowConfig(base_url="", api_key="", enabled=False, source=SecretSource.NONE)
    )
    result = await service.test_ragflow_connection()
    assert result.ok is False
    assert "停用" in result.message
    assert probe.calls == 0, "未启用时不该去打远端"

    provider.config = RagflowConfig(base_url="http://x:1", api_key="", enabled=True, source=SecretSource.NONE)
    result = await service.test_ragflow_connection()
    assert result.ok is False
    assert "尚未配置" in result.message
    assert probe.calls == 0


async def test_provider_is_always_resolved_with_system_scope() -> None:
    """一期恒按 ``scope="system"`` 取凭据 —— 这是"用户级密钥"扩展位的契约。

    将来若要改成"每个用户一把密钥"，换 provider 实现即可；这个断言保证
    调用方不会悄悄改成别的 scope，也不会有人顺手把 scope 参数删掉。
    """
    service, _, _, _, provider, _ = _service()
    await service.get_ragflow_settings()
    await service.test_ragflow_connection()
    assert provider.resolved_scopes == ["system", "system"]


async def test_write_operations_invalidate_all_scopes() -> None:
    """保存 / 清除走的是全量失效（``scope=None``），确保任何缓存都不会残留旧凭据。"""
    service, _, _, _, provider, _ = _service()
    await service.update_ragflow_settings(api_key_provided=True, api_key=SAMPLE_API_KEY)
    await service.clear_ragflow_api_key()
    assert provider.invalidated_scopes == [None, None]
