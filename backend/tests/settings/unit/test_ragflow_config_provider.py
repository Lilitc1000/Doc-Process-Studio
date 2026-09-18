"""RAGFlow 配置解析（三级回退 + 缓存失效）单元测试。

这是"管理员改完密钥立不立即生效"这条承诺的实现处，所以重点验证：

- 回退顺序：系统级密文 → 环境变量兜底 → 不可用
- 密文解不开时**降级而不是抛异常**（否则改错主密钥会让整个服务起不来）
- 写入后 ``invalidate()`` 能立刻穿透缓存（这是修掉 ``@lru_cache`` 钉死凭据那个老问题的关键）
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

from doc_process_studio.common.security.secret_cipher import SecretCipher
from doc_process_studio.settings.application.ports import StoredSecret
from doc_process_studio.settings.domain.values import (
    SECRET_RAGFLOW_API_KEY,
    SETTING_RAGFLOW_BASE_URL,
    SETTING_RAGFLOW_ENABLED,
    SecretSource,
)
from doc_process_studio.settings.infrastructure.ragflow_config_provider import SqlRagflowConfigProvider

KEY = os.urandom(32)
CIPHER = SecretCipher(keys={"k1": KEY}, active_key_id="k1")

ENV_BASE_URL = "http://env-fallback:10108"
ENV_API_KEY = "env-fallback-key"
ENV_ENABLED = True


class FakeSecretRepository:
    def __init__(self, ciphertext: str | None = None) -> None:
        self.ciphertext = ciphertext
        self.get_calls = 0

    async def get(self, secret_key: str) -> StoredSecret | None:
        self.get_calls += 1
        if self.ciphertext is None:
            return None
        return StoredSecret(
            secret_key=secret_key,
            ciphertext=self.ciphertext,
            key_id="k1",
            hint="tkYQ",
            updated_at=datetime.now(UTC),
        )

    async def upsert(self, **kwargs: Any) -> StoredSecret:  # pragma: no cover - 本测试不用
        raise NotImplementedError

    async def delete(self, secret_key: str) -> bool:  # pragma: no cover - 本测试不用
        raise NotImplementedError


class FakeSettingRepository:
    def __init__(self, values: dict[str, Any] | None = None) -> None:
        self.values = dict(values or {})
        self.get_calls = 0

    async def get(self, setting_key: str) -> Any | None:
        self.get_calls += 1
        return self.values.get(setting_key)

    async def set(self, setting_key: str, value: Any) -> None:  # pragma: no cover - 本测试不用
        self.values[setting_key] = value

    async def delete(self, setting_key: str) -> bool:  # pragma: no cover - 本测试不用
        return self.values.pop(setting_key, None) is not None


def _provider(
    *,
    settings: dict[str, Any] | None = None,
    ciphertext: str | None = None,
    cipher: SecretCipher = CIPHER,
    ttl: int = 60,
) -> tuple[SqlRagflowConfigProvider, FakeSecretRepository, FakeSettingRepository]:
    secret_repo = FakeSecretRepository(ciphertext)
    setting_repo = FakeSettingRepository(settings)
    provider = SqlRagflowConfigProvider(
        secret_repo=secret_repo,  # type: ignore[arg-type]
        setting_repo=setting_repo,  # type: ignore[arg-type]
        cipher=cipher,
        ttl_seconds=ttl,
        env_base_url=ENV_BASE_URL,
        env_api_key=ENV_API_KEY,
        env_enabled=ENV_ENABLED,
    )
    return provider, secret_repo, setting_repo


async def test_empty_database_falls_back_to_env() -> None:
    provider, _, _ = _provider()
    config = await provider.resolve()
    assert config.base_url == ENV_BASE_URL
    assert config.api_key == ENV_API_KEY
    assert config.enabled is True
    assert config.source is SecretSource.ENV
    assert config.usable is True


async def test_system_secret_wins_over_env() -> None:
    ciphertext = CIPHER.encrypt("system-key-value", aad=SECRET_RAGFLOW_API_KEY)
    provider, _, _ = _provider(
        settings={
            SETTING_RAGFLOW_BASE_URL: "http://system-host:10108/",
            SETTING_RAGFLOW_ENABLED: True,
        },
        ciphertext=ciphertext,
    )
    config = await provider.resolve()
    assert config.api_key == "system-key-value"
    assert config.source is SecretSource.SYSTEM
    assert config.base_url == "http://system-host:10108"  # 尾部斜杠被规整


async def test_system_enabled_false_overrides_env_true() -> None:
    """管理员停用后，即使 env 里开着也必须停用。"""
    ciphertext = CIPHER.encrypt("k", aad=SECRET_RAGFLOW_API_KEY)
    provider, _, _ = _provider(settings={SETTING_RAGFLOW_ENABLED: False}, ciphertext=ciphertext)
    config = await provider.resolve()
    assert config.enabled is False
    assert config.usable is False


async def test_system_base_url_without_secret_uses_env_key() -> None:
    """允许"只覆盖 Base URL、密钥仍走环境变量"的中间状态。"""
    provider, _, _ = _provider(settings={SETTING_RAGFLOW_BASE_URL: "http://only-url:10108"})
    config = await provider.resolve()
    assert config.base_url == "http://only-url:10108"
    assert config.api_key == ENV_API_KEY
    assert config.source is SecretSource.ENV


async def test_undecryptable_secret_degrades_instead_of_raising() -> None:
    """主密钥换了 / 密文被改过时，必须降级并继续服务，而不是把整个请求打挂。"""
    foreign = SecretCipher(keys={"k1": os.urandom(32)}, active_key_id="k1")
    broken = foreign.encrypt("unreadable", aad=SECRET_RAGFLOW_API_KEY)
    provider, _, _ = _provider(ciphertext=broken)
    config = await provider.resolve()
    assert config.api_key == ENV_API_KEY
    assert config.source is SecretSource.ENV


async def test_no_env_and_no_database_is_disabled() -> None:
    secret_repo = FakeSecretRepository(None)
    setting_repo = FakeSettingRepository({})
    provider = SqlRagflowConfigProvider(
        secret_repo=secret_repo,  # type: ignore[arg-type]
        setting_repo=setting_repo,  # type: ignore[arg-type]
        cipher=CIPHER,
        ttl_seconds=60,
        env_base_url=None,
        env_api_key=None,
        env_enabled=False,
    )
    config = await provider.resolve()
    assert config.base_url == ""
    assert config.api_key == ""
    assert config.usable is False
    assert config.source is SecretSource.NONE


async def test_ttl_caches_and_invalidate_breaks_through() -> None:
    """这是"改完立即生效"的核心断言：写操作后不用等 TTL。"""
    provider, secret_repo, setting_repo = _provider()
    await provider.resolve()
    first_secret_calls = secret_repo.get_calls
    first_setting_calls = setting_repo.get_calls

    await provider.resolve()
    assert secret_repo.get_calls == first_secret_calls, "TTL 内不应重复查库"
    assert setting_repo.get_calls == first_setting_calls

    # 模拟管理员保存了新配置，再 invalidate
    ciphertext = CIPHER.encrypt("brand-new-key", aad=SECRET_RAGFLOW_API_KEY)
    secret_repo.ciphertext = ciphertext
    provider.invalidate()

    config = await provider.resolve()
    assert config.api_key == "brand-new-key", "invalidate 后必须立刻读到新值"
    assert config.source is SecretSource.SYSTEM
    assert secret_repo.get_calls > first_secret_calls


async def test_ttl_zero_disables_caching() -> None:
    provider, secret_repo, _ = _provider(ttl=0)
    for _ in range(3):
        await provider.resolve()
    assert secret_repo.get_calls == 3


async def test_scoped_invalidate_only_drops_that_scope() -> None:
    """``scope`` 是为"用户级密钥"预留的扩展位，这里验证作用域隔离没写错。"""
    provider, secret_repo, _ = _provider()
    await provider.resolve(scope="system")
    await provider.resolve(scope="usr_a")
    calls = secret_repo.get_calls

    provider.invalidate(scope="usr_a")
    await provider.resolve(scope="system")
    assert secret_repo.get_calls == calls, "system 作用域的缓存不该被 usr_a 的失效连带清掉"

    await provider.resolve(scope="usr_a")
    assert secret_repo.get_calls > calls
