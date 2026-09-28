"""settings 路由响应模型。

直接复用应用层 DTO —— 它们本身就是"对外安全形状"（**不含任何明文凭据**，
凭据只以"是否已配置 + 掩码 + 来源"出现）。再复制一层响应模型只会带来
"改了 DTO 忘了改 schema"的漂移风险。
"""

from ...application.dtos import (
    ModelPreferencesDTO,
    RagflowConnectionTestDTO,
    RagflowDatasetListDTO,
    RagflowSettingsDTO,
    SettingsOverviewDTO,
    SystemSecretListDTO,
    SystemSecretSummaryDTO,
    UserPreferencesDTO,
)

SettingsOverviewResponse = SettingsOverviewDTO
UserPreferencesResponse = UserPreferencesDTO
ModelPreferencesResponse = ModelPreferencesDTO
RagflowSettingsResponse = RagflowSettingsDTO
RagflowConnectionTestResponse = RagflowConnectionTestDTO
RagflowDatasetListResponse = RagflowDatasetListDTO
SystemSecretSummaryResponse = SystemSecretSummaryDTO
SystemSecretListResponse = SystemSecretListDTO

__all__ = [
    "ModelPreferencesResponse",
    "RagflowConnectionTestResponse",
    "RagflowDatasetListResponse",
    "RagflowSettingsResponse",
    "SettingsOverviewResponse",
    "SystemSecretListResponse",
    "SystemSecretSummaryResponse",
    "UserPreferencesResponse",
]
