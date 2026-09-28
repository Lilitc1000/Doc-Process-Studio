"""RAGFlow 配置解析（库优先 + 内置默认兜底 + 缓存失效）单元测试。

重点验证"管理员改完密钥立即可生效"这条承诺的实现：

- 回退顺序：系统级密文 / 系统设置 → 内置默认值（不再读环境变量）
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
    DEFAULT_RAGFLOW_BASE_URL,
    DEFAULT_RAGFLOW_DATASETS_JSON,
    DEFAULT_RAGFLOW_ENABLED,
    DEFAULT_RAGFLOW_ENABLED_SECTIONS,
    DEFAULT_RAGFLOW_MAX_CHUNKS_PER_DOCUMENT,
    DEFAULT_RAGFLOW_PARSE_TIMEOUT_SECONDS,
    DEFAULT_RAGFLOW_SIMILARITY_THRESHOLD,
    DEFAULT_RAGFLOW_TIMEOUT_SECONDS,
    DEFAULT_RAGFLOW_TOP_K,
    SECRET_RAGFLOW_API_KEY,
    SETTING_RAGFLOW_BASE_URL,
    SETTING_RAGFLOW_ENABLED,
    SETTING_RAGFLOW_ENABLED_SECTIONS,
    SETTING_RAGFLOW_MAX_CHUNKS_PER_DOCUMENT,
    SETTING_RAGFLOW_PARSE_TIMEOUT_SECONDS,
    SETTING_RAGFLOW_SIMILARITY_THRESHOLD,
    SETTING_RAGFLOW_TIMEOUT_SECONDS,
    SETTING_RAGFLOW_TOP_K,
    SecretSource,
)
from doc_process_studio.settings.infrastructure.ragflow_config_provider import SqlRagflowConfigProvider

KEY = os.urandom(32)
CIPHER = SecretCipher(keys={"k1": KEY}, active_key_id="k1")


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
    )
    return provider, secret_repo, setting_repo


async def test_empty_database_falls_back_to_defaults() -> None:
    provider, _, _ = _provider()
    config = await provider.resolve()
    assert config.base_url == DEFAULT_RAGFLOW_BASE_URL
    assert config.api_key == ""
    assert config.enabled is DEFAULT_RAGFLOW_ENABLED
    assert config.source is SecretSource.NONE
    assert config.usable is False
    # 检索参数回落内置默认值
    assert config.similarity_threshold == DEFAULT_RAGFLOW_SIMILARITY_THRESHOLD
    assert config.top_k == DEFAULT_RAGFLOW_TOP_K
    assert config.timeout_seconds == DEFAULT_RAGFLOW_TIMEOUT_SECONDS
    assert config.parse_timeout_seconds == DEFAULT_RAGFLOW_PARSE_TIMEOUT_SECONDS
    assert config.max_chunks_per_document == DEFAULT_RAGFLOW_MAX_CHUNKS_PER_DOCUMENT
    assert config.enabled_sections == DEFAULT_RAGFLOW_ENABLED_SECTIONS
    assert config.datasets_json == DEFAULT_RAGFLOW_DATASETS_JSON


async def test_system_secret_wins_over_defaults() -> None:
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


async def test_system_enabled_false_overrides_default_true() -> None:
    """管理员停用后，默认开启也必须被覆盖为停用。"""
    ciphertext = CIPHER.encrypt("k", aad=SECRET_RAGFLOW_API_KEY)
    provider, _, _ = _provider(settings={SETTING_RAGFLOW_ENABLED: False}, ciphertext=ciphertext)
    config = await provider.resolve()
    assert config.enabled is False
    assert config.usable is False


async def test_system_base_url_without_secret_is_not_usable() -> None:
    """只覆盖 Base URL、密钥仍空缺时，凭据不可用（不再有环境变量兜底）。"""
    provider, _, _ = _provider(settings={SETTING_RAGFLOW_BASE_URL: "http://only-url:10108"})
    config = await provider.resolve()
    assert config.base_url == "http://only-url:10108"
    assert config.api_key == ""
    assert config.source is SecretSource.NONE
    assert config.usable is False


async def test_undecryptable_secret_degrades_instead_of_raising() -> None:
    """主密钥换了 / 密文被改过时，必须降级并继续服务，而不是把整个请求打挂。"""
    foreign = SecretCipher(keys={"k1": os.urandom(32)}, active_key_id="k1")
    broken = foreign.encrypt("unreadable", aad=SECRET_RAGFLOW_API_KEY)
    provider, _, _ = _provider(ciphertext=broken)
    config = await provider.resolve()
    assert config.api_key == ""
    assert config.source is SecretSource.NONE


async def test_explicit_setting_overrides_default_value() -> None:
    """库里写了具体值就覆盖内置默认（验证阈值 / 条数 / 超时 / 章节字段）。"""
    provider, _, _ = _provider(
        settings={
            SETTING_RAGFLOW_SIMILARITY_THRESHOLD: 0.42,
            SETTING_RAGFLOW_TOP_K: 12,
            SETTING_RAGFLOW_TIMEOUT_SECONDS: 30.0,
            SETTING_RAGFLOW_PARSE_TIMEOUT_SECONDS: 90.0,
            SETTING_RAGFLOW_MAX_CHUNKS_PER_DOCUMENT: 5,
            SETTING_RAGFLOW_ENABLED_SECTIONS: "quick,impact",
        }
    )
    config = await provider.resolve()
    assert config.similarity_threshold == 0.42
    assert config.top_k == 12
    assert config.timeout_seconds == 30.0
    assert config.parse_timeout_seconds == 90.0
    assert config.max_chunks_per_document == 5
    assert config.enabled_sections == "quick,impact"


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
