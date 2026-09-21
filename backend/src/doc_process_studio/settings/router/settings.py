"""设置相关 HTTP 接口。

权限模型（两层）：

- **个人设置**（``/preferences``）—— 任何登录用户都能读写**自己的**偏好。
  user_id 一律取自 JWT，不接受请求体传入，从根上堵死越权。
- **系统设置**（``/ragflow*``）—— 只有管理员能读写。RAGFlow 的连接信息与密钥是
  **全系统共享**的，一旦被普通用户改错（比如把 Base URL 填错），
  全系统的知识库检索和报告参考都会立刻失效，这既是权限问题也是可用性问题。
  读侧同样分层：``GET /api/settings`` 的 ``ragflow`` 段对非管理员为 ``null``
  （见 ``read_settings``），普通用户**使用** RAGFlow 检索不受影响 ——
  那条链路在服务端，不经过本路由。

响应里**永远不含明文密钥**，也不提供任何"回显明文"的接口 —— 这是刻意的取舍：
一旦能回显，攻击面就从"防脱库"退化成"防不住任何有登录态的人"。眼睛图标只作用于
用户正在输入的内容。
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from ...auth.infrastructure.dependencies import is_admin, require_admin
from ...common.security.security import get_current_user_id
from ..application.settings_service import ModelPreferencesUpdate, SettingsService
from ..domain.errors import InvalidBaseUrlError, InvalidSettingValueError
from ..infrastructure.dependencies import get_settings_service
from .schemas.request import PreferencesUpdateRequest, RagflowSettingsUpdateRequest
from .schemas.response import (
    RagflowConnectionTestResponse,
    RagflowDatasetListResponse,
    RagflowSettingsResponse,
    SettingsOverviewResponse,
    UserPreferencesResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/settings",
    tags=["settings"],
    dependencies=[Depends(get_current_user_id)],
)


@router.get("", response_model=SettingsOverviewResponse)
async def read_settings(
    user_id: str = Depends(get_current_user_id),
    admin: bool = Depends(is_admin),
    service: SettingsService = Depends(get_settings_service),
) -> SettingsOverviewResponse:
    """一次性返回设置页所需的全部内容。

    **响应内容按身份分层**：所有人都拿得到 ``preferences``（自己的偏好），
    只有管理员才拿得到 ``ragflow``（系统级共享配置）。非管理员时该字段为 ``null``。

    刻意用软门禁（``is_admin``）而不是 ``require_admin``：普通用户仍然需要打开设置页
    改自己的模型偏好，所以本接口必须返回 200，只是内容少一段。
    """
    return await service.get_overview(user_id, include_system_settings=admin)


@router.put("/preferences", response_model=UserPreferencesResponse)
async def update_preferences(
    body: PreferencesUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    service: SettingsService = Depends(get_settings_service),
) -> UserPreferencesResponse:
    """部分更新当前用户的偏好（只改请求里出现的段落）。"""
    update = ModelPreferencesUpdate()
    if "models" in body.model_fields_set and body.models is not None:
        update = ModelPreferencesUpdate(
            provided=True,
            selected=body.models.selected,
            reranker=body.models.reranker,
        )
    try:
        return await service.update_user_preferences(user_id, models=update)
    except InvalidSettingValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put(
    "/ragflow",
    response_model=RagflowSettingsResponse,
    dependencies=[Depends(require_admin)],
)
async def update_ragflow_settings(
    body: RagflowSettingsUpdateRequest,
    service: SettingsService = Depends(get_settings_service),
) -> RagflowSettingsResponse:
    """更新系统级 RAGFlow 设置（仅管理员）。apiKey 的四态语义见请求模型 docstring。"""
    provided = body.model_fields_set
    try:
        return await service.update_ragflow_settings(
            base_url_provided="base_url" in provided,
            base_url=body.base_url,
            enabled_provided="enabled" in provided,
            enabled=body.enabled,
            api_key_provided="api_key" in provided,
            api_key=body.api_key,
            datasets_json_provided="datasets_json" in provided,
            datasets_json=body.datasets_json,
            similarity_threshold_provided="similarity_threshold" in provided,
            similarity_threshold=body.similarity_threshold,
            top_k_provided="top_k" in provided,
            top_k=body.top_k,
        )
    except (InvalidBaseUrlError, InvalidSettingValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/ragflow/datasets",
    response_model=RagflowDatasetListResponse,
    dependencies=[Depends(require_admin)],
)
async def list_ragflow_datasets(
    service: SettingsService = Depends(get_settings_service),
) -> RagflowDatasetListResponse:
    """列出当前生效凭据下可访问的知识库（供设置页选择，仅管理员）。

    刻意每次实时取：换了 Base URL / 密钥后，可访问的集合会完全不同 ——
    让管理员从"当前连接下真实存在"的列表里选，比让他手抄 dataset id 可靠得多。
    """
    return await service.list_ragflow_datasets()


@router.post(
    "/ragflow/test",
    response_model=RagflowConnectionTestResponse,
    dependencies=[Depends(require_admin)],
)
async def test_ragflow_connection(
    service: SettingsService = Depends(get_settings_service),
) -> RagflowConnectionTestResponse:
    """用**已保存的**服务器侧配置做一次连通性自检（仅管理员）。

    刻意不接收前端草稿值：自检的应该是"实际生效的配置"，否则会出现
    "测试通过但保存的是别的东西"这种误导。
    """
    return await service.test_ragflow_connection()


@router.delete(
    "/ragflow/api-key",
    response_model=RagflowSettingsResponse,
    dependencies=[Depends(require_admin)],
)
async def clear_ragflow_api_key(
    service: SettingsService = Depends(get_settings_service),
) -> RagflowSettingsResponse:
    """清除系统级 API Key（仅管理员）。独立接口，避免误清。"""
    return await service.clear_ragflow_api_key()
