"""settings 应用服务。

职责边界：

- **用户级偏好**（模型选择等）：按 user_id 隔离，任何登录用户都能改自己的。
- **系统级 RAGFlow 共享凭据**：管理员维护，读写都在 router 层用 ``require_admin`` 把住；
  本服务只负责"校验 → 加密 → 落库"，绝不返回明文。

这里不负责 RAGFlow 的连接装配（那在
:mod:`doc_process_studio.settings.infrastructure.ragflow_config_provider`），
只负责"连通性自检"这类顺带的诊断动作。
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

from ...common.infrastructure.config import settings as app_settings
from ...common.security.secret_cipher import (
    SecretCipher,
    build_secret_hint,
    mask_secret_hint,
)
from ..domain.errors import InvalidBaseUrlError, InvalidSettingValueError
from ..domain.values import (
    ALLOWED_BASE_URL_SCHEMES,
    MAX_BASE_URL_LENGTH,
    MAX_MODEL_NAME_LENGTH,
    MAX_SECRET_LENGTH,
    SECRET_RAGFLOW_API_KEY,
    SETTING_RAGFLOW_BASE_URL,
    SETTING_RAGFLOW_DATASETS_JSON,
    SETTING_RAGFLOW_ENABLED,
    SETTING_RAGFLOW_SIMILARITY_THRESHOLD,
    SETTING_RAGFLOW_TOP_K,
    RagflowConfig,
)
from .dtos import (
    ModelPreferencesDTO,
    RagflowConnectionTestDTO,
    RagflowCredentialDTO,
    RagflowDatasetListDTO,
    RagflowDatasetSummaryDTO,
    RagflowSettingsDTO,
    SettingsOverviewDTO,
    UserPreferencesDTO,
)
from .ports import (
    RagflowConfigProvider,
    RagflowConnectionProbe,
    RagflowDatasetCatalog,
    SystemSecretRepository,
    SystemSettingRepository,
    UserSettingsRepository,
)

logger = logging.getLogger(__name__)

_ENABLED_SOURCE_SYSTEM = "system"
_ENABLED_SOURCE_ENV = "env"


@dataclass(slots=True)
class ModelPreferencesUpdate:
    """模型偏好的部分更新指令。

    ``provided=False`` 表示请求里没带这一段，整体跳过。
    ``selected`` / ``reranker`` 为 None 表示"这次不改这一项"；
    为空串表示"清空这一项"。
    """

    provided: bool = False
    selected: str | None = None
    reranker: str | None = None


def _validate_base_url(raw: str) -> str:
    value = (raw or "").strip().rstrip("/")
    if not value:
        return ""
    if len(value) > MAX_BASE_URL_LENGTH:
        raise InvalidBaseUrlError(f"Base URL 过长（上限 {MAX_BASE_URL_LENGTH} 字符）")
    parts = urlsplit(value)
    if parts.scheme.lower() not in ALLOWED_BASE_URL_SCHEMES:
        raise InvalidBaseUrlError("Base URL 只支持 http:// 或 https:// 开头")
    if not parts.netloc:
        raise InvalidBaseUrlError("Base URL 缺少主机名")
    return value


def _validate_model_name(raw: str) -> str | None:
    value = (raw or "").strip()
    if not value:
        return None
    if len(value) > MAX_MODEL_NAME_LENGTH:
        raise InvalidSettingValueError(f"模型名过长（上限 {MAX_MODEL_NAME_LENGTH} 字符）")
    return value


def _coerce_threshold(value: float | int | None) -> float:
    """相似度阈值：库里未配置时回落 env 默认值。"""
    if value is None:
        return app_settings.ragflow_similarity_threshold
    try:
        return float(value)
    except (TypeError, ValueError):
        return app_settings.ragflow_similarity_threshold


def _coerce_top_k(value: float | int | None) -> int:
    """检索条数：库里未配置时回落 env 默认值。"""
    if value is None:
        return app_settings.ragflow_top_k
    try:
        return int(value)
    except (TypeError, ValueError):
        return app_settings.ragflow_top_k


def _validate_datasets_json(raw: str) -> bool:
    """校验 dataset 映射：必须是 {"scope": ["<id>", ...]} 且值为数组。

    与 ``ragflow_knowledge._parse_datasets_json`` 保持一致——字符串值会被静默忽略，
    所以这里直接判为非法，避免管理员配了却"看起来没生效"。
    """
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return False
    if not isinstance(data, dict):
        return False
    return all(isinstance(value, list) for value in data.values())


def _clean_str(raw: Any) -> str | None:
    if not isinstance(raw, str):
        return None
    value = raw.strip()
    return value or None


class SettingsService:
    """设置用例服务。"""

    def __init__(
        self,
        *,
        secret_repo: SystemSecretRepository,
        setting_repo: SystemSettingRepository,
        user_settings_repo: UserSettingsRepository,
        cipher: SecretCipher,
        config_provider: RagflowConfigProvider,
        connection_probe: RagflowConnectionProbe,
        dataset_catalog: RagflowDatasetCatalog,
    ) -> None:
        self._secrets = secret_repo
        self._settings = setting_repo
        self._user_settings = user_settings_repo
        self._cipher = cipher
        self._provider = config_provider
        self._probe = connection_probe
        self._catalog = dataset_catalog

    async def list_ragflow_datasets(self) -> RagflowDatasetListDTO:
        """列出当前生效凭据下可访问的知识库，供设置页选择。

        **每次实时取，不缓存**：换了 Base URL 或密钥之后可访问的集合会变，
        缓存住只会让管理员选到早已不存在的 dataset。
        """
        config = await self._provider.resolve(scope="system")
        if not config.enabled:
            return RagflowDatasetListDTO(ok=False, message="RAGFlow 当前处于停用状态，无法读取知识库列表。")
        if not config.base_url or not config.api_key:
            return RagflowDatasetListDTO(ok=False, message="尚未配置 Base URL 或 API 密钥，无法读取知识库列表。")

        datasets = await self._catalog.list_datasets(config)
        if not datasets:
            return RagflowDatasetListDTO(
                ok=False,
                message="已连接但未取到任何知识库，请确认该密钥有访问权限，或服务端日志中的具体原因。",
            )
        return RagflowDatasetListDTO(
            ok=True,
            message=f"已取到 {len(datasets)} 个知识库",
            datasets=[
                RagflowDatasetSummaryDTO(
                    id=item.id,
                    name=item.name,
                    document_count=item.document_count,
                    chunk_count=item.chunk_count,
                )
                for item in datasets
            ],
        )

    # ------------------------------------------------------------------ 用户级偏好

    async def get_user_preferences(self, user_id: str) -> UserPreferencesDTO:
        raw = await self._user_settings.get_preferences(user_id)
        section = raw.get("models")
        models = section if isinstance(section, dict) else {}
        return UserPreferencesDTO(
            models=ModelPreferencesDTO(
                selected=_clean_str(models.get("selected")),
                reranker=_clean_str(models.get("reranker")),
            )
        )

    async def update_user_preferences(self, user_id: str, *, models: ModelPreferencesUpdate) -> UserPreferencesDTO:
        patch: dict[str, Any] = {}
        if models.provided:
            section: dict[str, Any] = {}
            if models.selected is not None:
                section["selected"] = _validate_model_name(models.selected)
            if models.reranker is not None:
                section["reranker"] = _validate_model_name(models.reranker)
            if section:
                patch["models"] = section

        if patch:
            await self._user_settings.merge_preferences(user_id, patch)
        return await self.get_user_preferences(user_id)

    # ------------------------------------------------------------------ 系统级 RAGFlow 设置

    async def get_overview(self, user_id: str, *, include_system_settings: bool = True) -> SettingsOverviewDTO:
        """设置页一次性拉取的完整视图。

        ``include_system_settings=False``（非管理员）时**不返回** ``ragflow`` 段，
        且**不会去解析它**（省掉一次解密与配置解析）。

        为什么非管理员不该看到这一段：它包含 Base URL、启用状态、以及密钥的掩码与
        尾 4 位 hint。普通用户**使用** RAGFlow 检索走的是服务端链路
        （对话工具、报告生成各自向 ``RagflowConfigProvider`` 现取配置），
        与本接口无关 —— 所以剥掉这段不影响任何功能，只是收掉不必要的暴露面。
        """
        return SettingsOverviewDTO(
            preferences=await self.get_user_preferences(user_id),
            ragflow=await self.get_ragflow_settings() if include_system_settings else None,
        )

    async def get_ragflow_settings(self) -> RagflowSettingsDTO:
        config = await self._provider.resolve(scope="system")
        stored_secret = await self._secrets.get(SECRET_RAGFLOW_API_KEY)
        stored_base_url = await self._settings.get(SETTING_RAGFLOW_BASE_URL)
        stored_enabled = await self._settings.get(SETTING_RAGFLOW_ENABLED)

        base_url_from_system = isinstance(stored_base_url, str) and bool(stored_base_url.strip())
        return RagflowSettingsDTO(
            base_url=config.base_url,
            enabled=config.enabled,
            enabled_source=_ENABLED_SOURCE_SYSTEM if isinstance(stored_enabled, bool) else _ENABLED_SOURCE_ENV,
            base_url_source=_ENABLED_SOURCE_SYSTEM if base_url_from_system else _ENABLED_SOURCE_ENV,
            credential=RagflowCredentialDTO(
                configured=stored_secret is not None,
                masked_api_key=mask_secret_hint(stored_secret.hint) if stored_secret else "",
                hint=stored_secret.hint if stored_secret else None,
                source=config.source,
                updated_at=stored_secret.updated_at if stored_secret else None,
            ),
            similarity_threshold=_coerce_threshold(config.similarity_threshold),
            top_k=_coerce_top_k(config.top_k),
            datasets_json=config.datasets_json,
        )

    async def update_ragflow_settings(
        self,
        *,
        base_url_provided: bool = False,
        base_url: str | None = None,
        enabled_provided: bool = False,
        enabled: bool | None = None,
        api_key_provided: bool = False,
        api_key: str | None = None,
        datasets_json_provided: bool = False,
        datasets_json: str | None = None,
        similarity_threshold_provided: bool = False,
        similarity_threshold: float | None = None,
        top_k_provided: bool = False,
        top_k: int | None = None,
    ) -> RagflowSettingsDTO:
        """更新系统级 RAGFlow 设置。

        ``api_key`` 的语义（最容易做错的地方，已定死）：

        - 请求里**没有** ``api_key`` 字段 → 保持不变
        - ``api_key`` 为空串 → 保持不变（避免前端空输入框误清密钥）
        - ``api_key`` 为非空字符串 → 加密后覆盖
        - 要清除，只能走 ``DELETE /api/settings/ragflow/api-key`` 这个独立接口

        ``base_url`` 传空串 / null 表示"撤销库内覆盖，回落到环境变量兜底"，
        与 api_key 的"空串不生效"不同 —— 因为 Base URL 不是敏感值，
        清空是常见且安全的操作。
        """
        changed = False

        if base_url_provided:
            validated = _validate_base_url(base_url or "")
            if validated:
                await self._settings.set(SETTING_RAGFLOW_BASE_URL, validated)
            else:
                await self._settings.delete(SETTING_RAGFLOW_BASE_URL)
            changed = True

        if enabled_provided:
            if enabled is None:
                await self._settings.delete(SETTING_RAGFLOW_ENABLED)
            else:
                await self._settings.set(SETTING_RAGFLOW_ENABLED, bool(enabled))
            changed = True

        if api_key_provided and api_key is not None:
            cleaned = api_key.strip()
            if cleaned:
                if len(cleaned) > MAX_SECRET_LENGTH:
                    raise InvalidSettingValueError(f"API Key 过长（上限 {MAX_SECRET_LENGTH} 字符）")
                await self._secrets.upsert(
                    secret_key=SECRET_RAGFLOW_API_KEY,
                    ciphertext=self._cipher.encrypt(cleaned, aad=SECRET_RAGFLOW_API_KEY),
                    key_id=self._cipher.active_key_id,
                    hint=build_secret_hint(cleaned),
                )
                changed = True
                # 只记事件与掩码，绝不记密钥内容
                logger.info("系统级 RAGFlow 凭据已更新（key=%s）", SECRET_RAGFLOW_API_KEY)

        if datasets_json_provided:
            cleaned = (datasets_json or "").strip()
            if cleaned:
                if not _validate_datasets_json(cleaned):
                    raise InvalidSettingValueError(
                        'datasets_json 必须是 {"scope": ["<dataset_id>", ...]} 形式，且值为数组'
                    )
                await self._settings.set(SETTING_RAGFLOW_DATASETS_JSON, cleaned)
            else:
                # 空串表示撤销库内覆盖，回落到环境变量兜底
                await self._settings.delete(SETTING_RAGFLOW_DATASETS_JSON)
            changed = True

        if similarity_threshold_provided:
            if similarity_threshold is None:
                await self._settings.delete(SETTING_RAGFLOW_SIMILARITY_THRESHOLD)
            else:
                if not 0.0 <= float(similarity_threshold) <= 1.0:
                    raise InvalidSettingValueError("similarity_threshold 必须落在 0.0 ~ 1.0")
                await self._settings.set(SETTING_RAGFLOW_SIMILARITY_THRESHOLD, float(similarity_threshold))
            changed = True

        if top_k_provided:
            if top_k is None:
                await self._settings.delete(SETTING_RAGFLOW_TOP_K)
            else:
                if int(top_k) < 1 or int(top_k) > 20:
                    raise InvalidSettingValueError("top_k 必须落在 1 ~ 20")
                await self._settings.set(SETTING_RAGFLOW_TOP_K, int(top_k))
            changed = True

        if changed:
            self._provider.invalidate()

        return await self.get_ragflow_settings()

    async def clear_ragflow_api_key(self) -> RagflowSettingsDTO:
        """清除系统级 API Key（回落环境变量兜底或变为不可用）。"""
        removed = await self._secrets.delete(SECRET_RAGFLOW_API_KEY)
        if removed:
            self._provider.invalidate()
            logger.info("系统级 RAGFlow 凭据已清除（key=%s）", SECRET_RAGFLOW_API_KEY)
        return await self.get_ragflow_settings()

    async def test_ragflow_connection(self) -> RagflowConnectionTestDTO:
        """用**当前生效的**服务器侧配置做一次连通性自检。

        注意这个方法不接收前端传来的草稿值 —— 自检的是"已经保存的配置"，
        避免把用户没保存的密钥在服务端拿着乱试。想验证新密钥请先保存再测试。
        """
        config: RagflowConfig = await self._provider.resolve(scope="system")
        if not config.usable:
            if not config.enabled:
                return RagflowConnectionTestDTO(ok=False, message="RAGFlow 当前处于停用状态")
            return RagflowConnectionTestDTO(ok=False, message="尚未配置 Base URL 或 API Key")
        ok, message, dataset_count = await self._probe.probe(config)
        return RagflowConnectionTestDTO(ok=ok, message=message, dataset_count=dataset_count)
