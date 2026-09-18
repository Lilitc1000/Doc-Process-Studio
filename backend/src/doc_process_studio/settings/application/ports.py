"""settings 应用层端口。"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ..domain.values import RagflowConfig


@dataclass(frozen=True, slots=True)
class StoredSecret:
    """system_secrets 表的一行。``ciphertext`` 是密文，明文从不落库。"""

    secret_key: str
    ciphertext: str
    key_id: str
    hint: str | None
    updated_at: datetime


class SystemSecretRepository(ABC):
    """系统级密文凭据仓储端口。"""

    @abstractmethod
    async def get(self, secret_key: str) -> StoredSecret | None:
        """按键读取密文凭据，不存在返回 None。"""

    @abstractmethod
    async def upsert(self, *, secret_key: str, ciphertext: str, key_id: str, hint: str | None) -> StoredSecret:
        """写入或覆盖，返回写入后的行。"""

    @abstractmethod
    async def delete(self, secret_key: str) -> bool:
        """删除，返回是否确实删掉了一行。"""


class SystemSettingRepository(ABC):
    """系统级非敏感配置仓储端口（值为 JSON 标量或对象）。"""

    @abstractmethod
    async def get(self, setting_key: str) -> Any | None:
        """按键读取，不存在返回 None。"""

    @abstractmethod
    async def set(self, setting_key: str, value: Any) -> None:
        """写入或覆盖。"""

    @abstractmethod
    async def delete(self, setting_key: str) -> bool:
        """删除一条覆盖项（让该键回落到环境变量兜底），返回是否确实删掉了一行。"""


class UserSettingsRepository(ABC):
    """用户级偏好仓储端口。"""

    @abstractmethod
    async def get_preferences(self, user_id: str) -> dict[str, Any]:
        """读取偏好 dict；用户尚无记录时返回空 dict。"""

    @abstractmethod
    async def merge_preferences(self, user_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        """把 patch 合并进现有偏好（只覆盖 patch 里出现的键），返回合并后的完整 dict。"""


class RagflowConfigProvider(ABC):
    """RAGFlow 连接配置解析端口。

    实现负责走完"数据库里的系统级凭据 → 环境变量兜底 → 不可用"这条回退链，
    并做必要的缓存与失效。调用方只关心拿到一个可直接用的
    :class:`RagflowConfig`，不关心凭据来自哪里。

    ``scope`` 是**为"用户级密钥"方案预留的扩展位**：一期实现恒按
    ``scope="system"`` 读取管理员维护的共享凭据。将来若要改成"每个用户一把密钥"，
    只需换一个按 user_id 解析的实现，所有调用方一行都不用改。
    """

    @abstractmethod
    async def resolve(self, *, scope: str = "system") -> RagflowConfig:
        """解析出可用的 RAGFlow 配置；任何缺失都返回 ``RagflowConfig.disabled()`` 而非抛异常。"""

    @abstractmethod
    def invalidate(self, *, scope: str | None = None) -> None:
        """让已缓存的解析结果失效（写操作后调用，使变更立即生效）。

        不缓存的实现可以是空实现。
        """


class RagflowConnectionProbe(ABC):
    """RAGFlow 连通性自检端口。"""

    @abstractmethod
    async def probe(self, config: RagflowConfig) -> tuple[bool, str, int]:
        """用给定配置探一次远端，返回 (是否可用, 说明, 可访问 dataset 数量)。"""
