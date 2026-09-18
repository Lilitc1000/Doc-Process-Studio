"""settings 领域值对象与常量。"""

from dataclasses import dataclass
from enum import StrEnum

# ---------------------------------------------------------------- 系统级键名
# 密文凭据的键（存在 system_secrets）
SECRET_RAGFLOW_API_KEY = "ragflow.api_key"
# 非敏感系统配置的键（存在 system_settings，值为 JSON 标量）
SETTING_RAGFLOW_BASE_URL = "ragflow.base_url"
SETTING_RAGFLOW_ENABLED = "ragflow.enabled"

# ---------------------------------------------------------------- 角色
ROLE_ADMIN = "admin"
ROLE_MEMBER = "member"
VALID_ROLES: frozenset[str] = frozenset({ROLE_ADMIN, ROLE_MEMBER})

# ---------------------------------------------------------------- 约束
MAX_BASE_URL_LENGTH = 512
MAX_SECRET_LENGTH = 512
MAX_MODEL_NAME_LENGTH = 128
ALLOWED_BASE_URL_SCHEMES = frozenset({"http", "https"})


class SecretSource(StrEnum):
    """凭据的实际来源，用于让前端能提示"当前用的是系统共享密钥还是环境变量兜底"。"""

    SYSTEM = "system"
    ENV = "env"
    NONE = "none"


@dataclass(frozen=True, slots=True)
class RagflowConfig:
    """解析完成的 RAGFlow 连接配置。

    ``scope`` 参数在端口上是预留的扩展位：一期恒为 ``"system"``（管理员维护的
    共享凭据）；将来若要改成"每个用户各自一把密钥"，换一个按 user_id 解析的
    provider 实现即可，调用方无需改动。
    """

    base_url: str
    api_key: str
    enabled: bool
    source: SecretSource

    @property
    def usable(self) -> bool:
        """是否具备真正发起请求的条件。"""
        return bool(self.enabled and self.base_url and self.api_key)

    @classmethod
    def disabled(cls) -> "RagflowConfig":
        return cls(base_url="", api_key="", enabled=False, source=SecretSource.NONE)
