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
    SECRET_RAGFLOW_API_KEY,
    SETTING_RAGFLOW_BASE_URL,
    SETTING_RAGFLOW_ENABLED,
    RagflowConfig,
    SecretSource,
)

logger = logging.getLogger(__name__)


class SqlRagflowConfigProvider(RagflowConfigProvider):
    """按"库里配置优先、env 兜底"的顺序解析 RAGFlow 连接配置。"""

    def __init__(
        self,
        *,
        secret_repo: SystemSecretRepository,
        setting_repo: SystemSettingRepository,
        cipher: SecretCipher,
        ttl_seconds: int,
        env_base_url: str | None,
        env_api_key: str | None,
        env_enabled: bool,
    ) -> None:
        self._secrets = secret_repo
        self._settings = setting_repo
        self._cipher = cipher
        self._ttl = max(0, int(ttl_seconds))
        self._env_base_url = (env_base_url or "").strip().rstrip("/")
        self._env_api_key = (env_api_key or "").strip()
        self._env_enabled = bool(env_enabled)
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

        if isinstance(stored_base_url, str) and stored_base_url.strip():
            base_url = stored_base_url.strip().rstrip("/")
        else:
            base_url = self._env_base_url

        # 库里有明确配置就用库里的；没有则回落到 env（保持既有部署行为不变）
        enabled = stored_enabled if isinstance(stored_enabled, bool) else self._env_enabled

        api_key = ""
        source = SecretSource.NONE
        if stored_secret is not None:
            try:
                api_key = self._cipher.decrypt(stored_secret.ciphertext, aad=SECRET_RAGFLOW_API_KEY)
                source = SecretSource.SYSTEM
            except SecretCipherError as exc:
                # 主密钥换了 / 密文被篡改 / 手工改过库 —— 不阻断启动，降级并留下明确线索
                logger.error(
                    "系统级 RAGFlow 凭据解密失败（key=%s, key_id=%s）：%s；将回落到环境变量兜底",
                    SECRET_RAGFLOW_API_KEY,
                    stored_secret.key_id,
                    exc,
                )
        if not api_key and self._env_api_key:
            api_key = self._env_api_key
            source = SecretSource.ENV

        return RagflowConfig(base_url=base_url, api_key=api_key, enabled=enabled, source=source)
