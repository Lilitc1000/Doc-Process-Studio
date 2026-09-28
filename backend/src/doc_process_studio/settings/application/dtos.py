"""settings 应用层数据传输对象。

所有对外 DTO **绝不包含任何明文凭据**：凭据只以"是否已配置 + 掩码 + 来源"的形式出现。
"""

from datetime import datetime

from pydantic import BaseModel, Field

from ..domain.values import SecretSource


class ModelPreferencesDTO(BaseModel):
    """模型选择偏好。所有字段可为 None 表示"用户没有设置过"，由前端回落到默认值。"""

    selected: str | None = Field(default=None, description="生成模型名")
    reranker: str | None = Field(default=None, description="重排序模型名")


class UserPreferencesDTO(BaseModel):
    """用户级非敏感偏好。"""

    models: ModelPreferencesDTO = Field(default_factory=ModelPreferencesDTO, description="模型偏好")


class RagflowSettingsDTO(BaseModel):
    """RAGFlow 系统设置视图（**不含密钥**——密钥统一走通用系统密钥清单）。

    凭据（是否已配置 / 掩码 / 来源）由 ``GET /api/settings/secrets`` 提供，
    这样密钥的存储、展示、清除都是单一来源，避免与 RAGFlow 专属端点重复。
    """

    base_url: str = Field(..., description="当前生效的 Base URL")
    enabled: bool = Field(..., description="当前生效的启用状态")
    enabled_source: str = Field(..., description="启用状态来源：system（库里配置）或 default（内置默认值）")
    base_url_source: str = Field(..., description="Base URL 来源：system 或 default")
    similarity_threshold: float = Field(..., description="检索相似度阈值（当前为全局配置）")
    top_k: int = Field(..., description="检索条数（当前为全局配置）")
    datasets_json: str = Field(
        default="",
        description=(
            '报告侧检索使用的 dataset 映射，形如 {"history": ["<dataset_id>"]}。'
            "库里未配置时返回内置默认 dataset 映射；空串表示未配置任何 dataset"
        ),
    )
    timeout_seconds: float = Field(..., description="RAGFlow 请求超时（秒），库里未配置时取内置默认值")
    parse_timeout_seconds: float = Field(..., description="触发服务端解析的超时（秒），库里未配置时取内置默认值")
    max_chunks_per_document: int = Field(..., description="同一文档最多注入的片段数，库里未配置时取内置默认值")
    enabled_sections: str = Field(
        ..., description="启用 RAGFlow 知识增强的报告章节（逗号分隔）；库里未配置时取内置默认值"
    )


class SettingsOverviewDTO(BaseModel):
    """设置页一次性拉取的完整视图。

    ``ragflow`` 为 ``None`` 表示**调用者无权查看系统级共享配置**（即非管理员）。
    这是刻意用"整段缺失"而不是"字段置空"表达的：置空会让人以为是"未配置"，
    缺失才能明确表达"这段不对你开放"。
    """

    preferences: UserPreferencesDTO = Field(..., description="当前用户的偏好")
    ragflow: RagflowSettingsDTO | None = Field(
        default=None,
        description="RAGFlow 系统设置；非管理员（或未请求系统段）时为 None",
    )


class RagflowDatasetSummaryDTO(BaseModel):
    """设置页下拉用的知识库条目。"""

    id: str = Field(..., description="RAGFlow dataset id")
    name: str = Field(..., description="知识库名称")
    document_count: int = Field(default=0, description="文档数")
    chunk_count: int = Field(default=0, description="片段数")


class RagflowDatasetListDTO(BaseModel):
    """知识库列表视图。

    ``ok=False`` 时 ``message`` 说明原因（未启用 / 未配置凭据 / 连不上 / 无权限），
    ``datasets`` 一律为已取到的部分，前端据此区分"连接有问题"与"这个连接下确实没有知识库"。
    """

    ok: bool = Field(..., description="是否成功取到列表")
    message: str = Field(default="", description="结果说明，失败时给出原因")
    datasets: list[RagflowDatasetSummaryDTO] = Field(default_factory=list, description="知识库列表")


class RagflowConnectionTestDTO(BaseModel):
    """连通性自检结果。"""

    ok: bool = Field(..., description="是否连通且鉴权通过")
    message: str = Field(..., description="结果说明（失败时给出具体原因）")
    dataset_count: int = Field(default=0, description="可访问的 dataset 数量")


class SystemSecretSummaryDTO(BaseModel):
    """通用系统密钥的可展示信息（无明文）。"""

    key: str = Field(..., description="密钥槽位 key，如 ragflow.api_key")
    label: str = Field(..., description="展示名")
    description: str = Field(..., description="用途说明")
    kind: str = Field(..., description="密钥种类：api_key / oauth2 / generic_token，前端按此分发渲染")
    configured: bool = Field(..., description="是否已由管理员写入")
    masked_value: str = Field(..., description="掩码串；未配置时为空串")
    hint: str | None = Field(default=None, description="掩码尾串；明文过短时为 None")
    source: SecretSource = Field(..., description="当前生效来源：system / env / none")
    updated_at: datetime | None = Field(default=None, description="最后更新时间")


class SystemSecretListDTO(BaseModel):
    """系统密钥列表视图。"""

    secrets: list[SystemSecretSummaryDTO] = Field(default_factory=list, description="已注册的密钥槽位")
