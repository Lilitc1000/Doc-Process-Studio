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
    """系统级 RAGFlow 设置更新（仅管理员）。

    ``api_key`` 的四种语义在服务层定死（router 用 ``model_fields_set`` 把"字段缺失"
    和"值为空"分开）：

    ====================  ==========================
    请求里的 apiKey       行为
    ====================  ==========================
    字段缺失              保持不变
    ``""``                保持不变（避免前端空输入框误清密钥）
    非空字符串            加密后覆盖
    走 DELETE 专用接口    清除
    ====================  ==========================

    ``base_url`` 则相反：传空串或 ``null`` 表示"撤销库内覆盖、回落环境变量兜底"，
    因为 Base URL 不是敏感值，清空是常见且安全的操作。
    """

    base_url: str | None = Field(
        default=None,
        max_length=MAX_BASE_URL_LENGTH,
        description="Base URL；传空串或 null 表示撤销库内覆盖，回落环境变量兜底",
    )
    enabled: bool | None = Field(
        default=None,
        description="运行期启用开关；传 null 表示撤销库内覆盖，回落环境变量",
    )
    api_key: str | None = Field(
        default=None,
        max_length=MAX_SECRET_LENGTH,
        description="API Key；字段缺失或空串表示不修改。清除请走 DELETE /api/settings/ragflow/api-key",
    )
    datasets_json: str | None = Field(
        default=None,
        max_length=2000,
        description=(
            '报告侧检索的 dataset 映射，形如 {"history": ["<dataset_id>"]}；'
            "传空串或 null 表示撤销库内覆盖，回落环境变量兜底"
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
