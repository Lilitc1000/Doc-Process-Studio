"""settings 路由请求模型。"""

from pydantic import BaseModel, Field

from ...domain.values import MAX_BASE_URL_LENGTH, MAX_MODEL_NAME_LENGTH, MAX_SECRET_LENGTH


class ModelPreferencesRequest(BaseModel):
    """模型偏好部分更新。

    - 字段缺失 / ``null`` → 不改这一项
    - 空串 → 清空这一项（前端回落到默认模型）
    """

    selected: str | None = Field(default=None, max_length=MAX_MODEL_NAME_LENGTH, description="生成模型名")
    reranker: str | None = Field(default=None, max_length=MAX_MODEL_NAME_LENGTH, description="重排序模型名")


class PreferencesUpdateRequest(BaseModel):
    """用户偏好部分更新；不传的段落整体跳过。"""

    models: ModelPreferencesRequest | None = Field(default=None, description="模型偏好；不传表示不改")


class RagflowSettingsUpdateRequest(BaseModel):
    """系统级 RAGFlow 非密钥设置更新（仅管理员）。

    密钥（API Key）统一走通用系统密钥端点 ``PUT/DELETE /api/settings/secrets/{key}``，
    不在本模型里出现，避免两套密钥写入路径并存。

    ``base_url`` 传空串或 ``null`` 表示"撤销库内覆盖、回落内置默认值"，
    因为 Base URL 不是敏感值，清空是常见且安全的操作。
    """

    base_url: str | None = Field(
        default=None,
        max_length=MAX_BASE_URL_LENGTH,
        description="Base URL；传空串或 null 表示撤销库内覆盖，回落内置默认值",
    )
    enabled: bool | None = Field(
        default=None,
        description="运行期启用开关；传 null 表示撤销库内覆盖，回落内置默认值",
    )
    datasets_json: str | None = Field(
        default=None,
        max_length=2000,
        description=(
            '报告侧检索的 dataset 映射，形如 {"history": ["<dataset_id>"]}；'
            "传空串或 null 表示撤销库内覆盖，回落内置默认 dataset 映射"
        ),
    )
    similarity_threshold: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="检索相似度阈值 0.0~1.0；传 null 表示撤销库内覆盖",
    )
    top_k: int | None = Field(
        default=None,
        ge=1,
        le=20,
        description="检索条数 1~20；传 null 表示撤销库内覆盖",
    )
    timeout_seconds: float | None = Field(
        default=None,
        gt=0,
        le=600,
        description="RAGFlow 请求超时（秒）；传 null 表示撤销库内覆盖，回落内置默认值",
    )
    parse_timeout_seconds: float | None = Field(
        default=None,
        gt=0,
        le=600,
        description="触发服务端解析的超时（秒）；传 null 表示撤销库内覆盖，回落内置默认值",
    )
    max_chunks_per_document: int | None = Field(
        default=None,
        ge=1,
        le=50,
        description="同一文档最多注入的片段数；传 null 表示撤销库内覆盖，回落内置默认值",
    )
    enabled_sections: str | None = Field(
        default=None,
        max_length=200,
        description="启用 RAGFlow 知识增强的报告章节（逗号分隔）；传空串或 null 表示撤销库内覆盖",
    )


class SecretSetRequest(BaseModel):
    """通用系统密钥写入请求（仅管理员）。

    与 RAGFlow 专属路径共用底层 ``system_secrets`` 存储；新增第三方密钥只需在
    ``values.KNOWN_SYSTEM_SECRET_SLOTS`` 注册槽位，无需新增接口。
    """

    value: str = Field(
        ...,
        min_length=1,
        max_length=MAX_SECRET_LENGTH,
        description="明文密钥；服务端加密入库，不回显",
    )
