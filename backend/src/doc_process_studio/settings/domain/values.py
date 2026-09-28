"""settings 领域值对象与常量。"""

from dataclasses import dataclass
from enum import StrEnum

# ---------------------------------------------------------------- 系统级键名
# 密文凭据的键（存在 system_secrets）
SECRET_RAGFLOW_API_KEY = "ragflow.api_key"
# 非敏感系统配置的键（存在 system_settings，值为 JSON 标量）
SETTING_RAGFLOW_BASE_URL = "ragflow.base_url"
SETTING_RAGFLOW_ENABLED = "ragflow.enabled"
# 检索参数：报告侧检索用的 dataset 映射与召回参数。
# 放在库里是为了让管理员能在设置页调整并立即生效，而不必改 env 再重启进程。
SETTING_RAGFLOW_DATASETS_JSON = "ragflow.datasets_json"
SETTING_RAGFLOW_SIMILARITY_THRESHOLD = "ragflow.similarity_threshold"
SETTING_RAGFLOW_TOP_K = "ragflow.top_k"
# 其余 RAGFLOW 配置（此前来自环境变量，现统一改为页面配置、库内持久化）
SETTING_RAGFLOW_TIMEOUT_SECONDS = "ragflow.timeout_seconds"
SETTING_RAGFLOW_PARSE_TIMEOUT_SECONDS = "ragflow.parse_timeout_seconds"
SETTING_RAGFLOW_MAX_CHUNKS_PER_DOCUMENT = "ragflow.max_chunks_per_document"
SETTING_RAGFLOW_ENABLED_SECTIONS = "ragflow.enabled_sections"

# ------------------------------------------------------------------ 代码内置默认值
# RAGFLOW 配置全部改为页面化、库内持久化后，环境变量不再作为数据源；
# 库里未配置时使用以下内置默认值，保证开箱可用且无需改动 .env。
DEFAULT_RAGFLOW_BASE_URL = ""
DEFAULT_RAGFLOW_ENABLED = False
DEFAULT_RAGFLOW_DATASETS_JSON = '{"history":["f05e5a4aadac11f1b9211b18c23af0c8"]}'
DEFAULT_RAGFLOW_SIMILARITY_THRESHOLD = 0.55
DEFAULT_RAGFLOW_TOP_K = 6
DEFAULT_RAGFLOW_TIMEOUT_SECONDS = 15.0
DEFAULT_RAGFLOW_PARSE_TIMEOUT_SECONDS = 60.0
DEFAULT_RAGFLOW_MAX_CHUNKS_PER_DOCUMENT = 2
DEFAULT_RAGFLOW_ENABLED_SECTIONS = "quick,impact,root_cause,follow_up"


class SecretKind(StrEnum):
    """密钥种类：前端按种类分发渲染（基类=通用密钥，派生=具体集成实例）。

    新增一类密钥时优先复用现有种类；若需要完全不同的字段 / 校验 / UI，
    再扩展此枚举并让 ``SecretSlot`` 派生子类（如 ``OAuth2SecretSlot``）。
    """

    API_KEY = "api_key"
    OAUTH2 = "oauth2"
    GENERIC_TOKEN = "generic_token"


# ---------------------------------------------------------------- 通用系统密钥槽
# 任何"系统级密文凭据"都注册到这里，前端『系统密钥』页（父卡片）即可列出并管理；
# 新增第三方密钥（新 LLM / 支付 / 外部 API 等）只需在此加一个槽位，
# 无需改动端口 / 服务 / 路由 / 前端接口。底层 system_secrets 本就是按 key 通用存储。
@dataclass(frozen=True, slots=True)
class SecretSlot:
    """一个可在设置页管理的系统级密文凭据槽位（派生实例的基类描述）。"""

    key: str
    label: str
    description: str
    #: 密钥种类；用于前端按类型分发渲染。默认 API_KEY。
    kind: SecretKind = SecretKind.API_KEY
    #: 预留：若某个密钥允许"环境变量兜底"，则填对应的 app_settings 字段名。
    #: RAGFLOW 等凭据已全面页面化、库内持久化，不读环境变量，故此槽位为 None。
    env_field: str | None = None
    placeholder: str = ""


KNOWN_SYSTEM_SECRET_SLOTS: tuple[SecretSlot, ...] = (
    SecretSlot(
        key=SECRET_RAGFLOW_API_KEY,
        label="RAGFlow API Key",
        description="RAGFlow 服务端 API 密钥，用于报告侧知识库检索；加密入库，立即生效。",
        kind=SecretKind.API_KEY,
        env_field=None,
        placeholder="ragflow-xxxxxxxx",
    ),
)

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
    """凭据的实际来源，用于让前端提示"当前用的是系统共享密钥，还是未配置"。

    RAGFLOW 等凭据已全面页面化、库内持久化，不再有环境变量兜底来源，
    因此只有 SYSTEM（库里已配置）与 NONE（未配置）两种。
    """

    SYSTEM = "system"
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
    # 检索参数。库里未配置时回落到 values.py 中的 DEFAULT_RAGFLOW_* 内置默认值
    # （不再读环境变量）。
    datasets_json: str = ""
    similarity_threshold: float | None = None
    top_k: int | None = None
    timeout_seconds: float = DEFAULT_RAGFLOW_TIMEOUT_SECONDS
    parse_timeout_seconds: float = DEFAULT_RAGFLOW_PARSE_TIMEOUT_SECONDS
    max_chunks_per_document: int = DEFAULT_RAGFLOW_MAX_CHUNKS_PER_DOCUMENT
    enabled_sections: str = DEFAULT_RAGFLOW_ENABLED_SECTIONS

    @property
    def usable(self) -> bool:
        """是否具备真正发起请求的条件。"""
        return bool(self.enabled and self.base_url and self.api_key)

    @classmethod
    def disabled(cls) -> "RagflowConfig":
        return cls(base_url="", api_key="", enabled=False, source=SecretSource.NONE)
