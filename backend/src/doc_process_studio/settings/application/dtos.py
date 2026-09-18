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


class RagflowCredentialDTO(BaseModel):
    """系统级 RAGFlow 凭据的**可展示信息**（无明文）。"""

    configured: bool = Field(..., description="是否已由管理员写入密钥")
    masked_api_key: str = Field(..., description="掩码串，如 ••••••••Y30tkYQ；未配置时为固定掩码")
    hint: str | None = Field(default=None, description="掩码尾串；明文过短时为 None")
    source: SecretSource = Field(..., description="当前生效凭据来源")
    updated_at: datetime | None = Field(default=None, description="密钥最后更新时间")


class RagflowSettingsDTO(BaseModel):
    """RAGFlow 系统设置视图。"""

    base_url: str = Field(..., description="当前生效的 Base URL")
    enabled: bool = Field(..., description="当前生效的启用状态")
    enabled_source: str = Field(..., description="启用状态来源：system（库里配置）或 env（环境变量兜底）")
    base_url_source: str = Field(..., description="Base URL 来源：system 或 env")
    credential: RagflowCredentialDTO = Field(..., description="凭据展示信息")
    similarity_threshold: float = Field(..., description="检索相似度阈值（当前为全局配置）")
    top_k: int = Field(..., description="检索条数（当前为全局配置）")


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


class RagflowConnectionTestDTO(BaseModel):
    """连通性自检结果。"""

    ok: bool = Field(..., description="是否连通且鉴权通过")
    message: str = Field(..., description="结果说明（失败时给出具体原因）")
    dataset_count: int = Field(default=0, description="可访问的 dataset 数量")
