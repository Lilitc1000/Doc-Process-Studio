"""RAGFlow 连接配置解析实现：系统级凭据 → 环境变量兜底 → 不可用。

**为什么要有这一层**：RAGFlow 的连接信息此前是从 ``settings`` 直接读的
（``knowledge_base/infrastructure/dependencies.py`` 与
``incident_report/infrastructure/dependencies.py``），而那两个装配点都被
``@lru_cache(maxsize=1)`` 钉成了进程级单例 —— 管理员在设置页改了密钥，
不重启进程就不会生效。本 provider 把"取凭据"从"构造客户端"里拆出来，
自身带一次性缓存 + 写入时失效，于是改完立即生效。

**缓存语义**：``(scope) → (过期时间, epoch, 配置)``。写操作调用
:meth:`invalidate` 会自增 epoch 并清空缓存，同进程内立即生效；
多 worker 部署时其他 worker 最长要等 ``system_settings_cache_ttl_seconds``。
"""

from __future__ import annotations

import logging
import time

from ...common.security.secret_cipher import SecretCipher, SecretCipherError
from ..application.ports import (
    RagflowConfigProvider,
    SystemSecretRepository,
    SystemSettingRepository,
)
from ..domain.values import (
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
    SETTING_RAGFLOW_DATASETS_JSON,
    SETTING_RAGFLOW_ENABLED,
    SETTING_RAGFLOW_ENABLED_SECTIONS,
    SETTING_RAGFLOW_MAX_CHUNKS_PER_DOCUMENT,
    SETTING_RAGFLOW_PARSE_TIMEOUT_SECONDS,
    SETTING_RAGFLOW_SIMILARITY_THRESHOLD,
    SETTING_RAGFLOW_TIMEOUT_SECONDS,
    SETTING_RAGFLOW_TOP_K,
    RagflowConfig,
    SecretSource,
)

logger = logging.getLogger(__name__)


class SqlRagflowConfigProvider(RagflowConfigProvider):
    """按"库里配置优先、内置默认值兜底"的顺序解析 RAGFlow 连接配置。

    环境变量不再作为数据源：所有 RAGFLOW 配置均通过页面写入 ``system_settings``
    （及 ``system_secrets`` 存密钥），未配置时回落 ``values.py`` 中的 ``DEFAULT_RAGFLOW_*``。
    """

    def __init__(
        self,
        *,
        secret_repo: SystemSecretRepository,
        setting_repo: SystemSettingRepository,
        cipher: SecretCipher,
        ttl_seconds: int,
    ) -> None:
        self._secrets = secret_repo
        self._settings = setting_repo
        self._cipher = cipher
        self._ttl = max(0, int(ttl_seconds))
        self._cache: dict[str, tuple[float, int, RagflowConfig]] = {}
        self._epoch = 0

    # ------------------------------------------------------------------ 端口实现

    async def resolve(self, *, scope: str = "system") -> RagflowConfig:
        now = time.monotonic()
        cached = self._cache.get(scope)
        if cached is not None and cached[1] == self._epoch and cached[0] > now:
            return cached[2]

        config = await self._load()
        if self._ttl > 0:
            self._cache[scope] = (now + self._ttl, self._epoch, config)
        return config

    def invalidate(self, *, scope: str | None = None) -> None:
        """使缓存失效。

        指定 ``scope`` 时**只清那一个**，不动 epoch —— 因为 epoch 是所有缓存项的
        公共有效性标记，自增它等价于"全部失效"，那 ``scope`` 参数就成了摆设。
        """
        if scope is None:
            self._epoch += 1
            self._cache.clear()
        else:
            self._cache.pop(scope, None)

    # ------------------------------------------------------------------ 内部

    async def _load(self) -> RagflowConfig:
        stored_base_url = await self._settings.get(SETTING_RAGFLOW_BASE_URL)
        stored_enabled = await self._settings.get(SETTING_RAGFLOW_ENABLED)
        stored_secret = await self._secrets.get(SECRET_RAGFLOW_API_KEY)

        base_url = (
            stored_base_url.strip().rstrip("/")
            if isinstance(stored_base_url, str) and stored_base_url.strip()
            else DEFAULT_RAGFLOW_BASE_URL
        )

        # 库里有明确配置就用库里的；没有则回落到内置默认值
        enabled = stored_enabled if isinstance(stored_enabled, bool) else DEFAULT_RAGFLOW_ENABLED

        api_key = ""
        source = SecretSource.NONE
        if stored_secret is not None:
            try:
                api_key = self._cipher.decrypt(stored_secret.ciphertext, aad=SECRET_RAGFLOW_API_KEY)
                source = SecretSource.SYSTEM
            except SecretCipherError as exc:
                # 主密钥换了 / 密文被篡改 / 手工改过库 —— 不阻断启动，降级并留下明确线索
                logger.error(
                    "系统级 RAGFlow 凭据解密失败（key=%s, key_id=%s）：%s；将回落到未配置状态",
                    SECRET_RAGFLOW_API_KEY,
                    stored_secret.key_id,
                    exc,
                )

        return RagflowConfig(
            base_url=base_url,
            api_key=api_key,
            enabled=enabled,
            source=source,
            datasets_json=await self._load_datasets_json(),
            similarity_threshold=await self._load_float(
                SETTING_RAGFLOW_SIMILARITY_THRESHOLD, DEFAULT_RAGFLOW_SIMILARITY_THRESHOLD
            ),
            top_k=await self._load_int(SETTING_RAGFLOW_TOP_K, DEFAULT_RAGFLOW_TOP_K),
            timeout_seconds=await self._load_float(SETTING_RAGFLOW_TIMEOUT_SECONDS, DEFAULT_RAGFLOW_TIMEOUT_SECONDS),
            parse_timeout_seconds=await self._load_float(
                SETTING_RAGFLOW_PARSE_TIMEOUT_SECONDS, DEFAULT_RAGFLOW_PARSE_TIMEOUT_SECONDS
            ),
            max_chunks_per_document=await self._load_int(
                SETTING_RAGFLOW_MAX_CHUNKS_PER_DOCUMENT, DEFAULT_RAGFLOW_MAX_CHUNKS_PER_DOCUMENT
            ),
            enabled_sections=await self._load_str(SETTING_RAGFLOW_ENABLED_SECTIONS, DEFAULT_RAGFLOW_ENABLED_SECTIONS),
        )

    async def _load_datasets_json(self) -> str:
        """库里配置优先，未配置或不是字符串时回落内置默认 dataset 映射。"""
        stored = await self._settings.get(SETTING_RAGFLOW_DATASETS_JSON)
        if isinstance(stored, str) and stored.strip():
            return stored.strip()
        return DEFAULT_RAGFLOW_DATASETS_JSON

    async def _load_str(self, key: str, fallback: str) -> str:
        """读取字符串型设置；库里为空或非字符串时回落内置默认值。"""
        stored = await self._settings.get(key)
        if isinstance(stored, str) and stored.strip():
            return stored.strip()
        return fallback

    async def _load_float(self, key: str, fallback: float) -> float:
        """读取浮点型设置；库里没有、非数值或类型不对时回落内置默认值。"""
        stored = await self._settings.get(key)
        if isinstance(stored, bool):
            return fallback
        if isinstance(stored, (int, float)):
            return float(stored)
        if isinstance(stored, str):
            try:
                return float(stored)
            except ValueError:
                logger.warning("系统设置 %s 不是合法数值，回落内置默认值: %r", key, stored)
                return fallback
        return fallback

    async def _load_int(self, key: str, fallback: int) -> int:
        """读取整型设置；库里没有、非数值或类型不对时回落内置默认值。"""
        stored = await self._settings.get(key)
        if isinstance(stored, bool):
            return fallback
        if isinstance(stored, int):
            return stored
        if isinstance(stored, float):
            return int(stored)
        if isinstance(stored, str):
            try:
                return int(float(stored))
            except ValueError:
                logger.warning("系统设置 %s 不是合法数值，回落内置默认值: %r", key, stored)
                return fallback
        return fallback
