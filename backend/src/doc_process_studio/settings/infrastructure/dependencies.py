"""settings 基础设施依赖装配。

全部为进程内单例。其中 ``get_ragflow_config_provider`` **必须是单例**：
它内部持有解析缓存与失效 epoch，如果每次请求都新建实例，管理员的写操作调用
``invalidate()`` 就作用不到知识库 / 事故报告那两条链路正在用的那个实例上，
"改完立即生效"就落空了。
"""

from functools import lru_cache

from ...common.infrastructure.config import settings
from ...common.security.secret_cipher import get_secret_cipher
from ..application.ports import (
    RagflowConfigProvider,
    RagflowConnectionProbe,
    RagflowDatasetCatalog,
    SystemSecretRepository,
    SystemSettingRepository,
    UserSettingsRepository,
)
from ..application.settings_service import SettingsService
from .ragflow_config_provider import SqlRagflowConfigProvider
from .ragflow_dataset_catalog import RagflowClientDatasetCatalog
from .ragflow_probe import RagflowClientConnectionProbe
from .repositories.sql_repositories import (
    SqlSystemSecretRepository,
    SqlSystemSettingRepository,
    SqlUserSettingsRepository,
)


@lru_cache(maxsize=1)
def get_system_secret_repository() -> SystemSecretRepository:
    return SqlSystemSecretRepository()


@lru_cache(maxsize=1)
def get_system_setting_repository() -> SystemSettingRepository:
    return SqlSystemSettingRepository()


@lru_cache(maxsize=1)
def get_user_settings_repository() -> UserSettingsRepository:
    return SqlUserSettingsRepository()


@lru_cache(maxsize=1)
def get_ragflow_config_provider() -> RagflowConfigProvider:
    """RAGFlow 连接配置解析器（全局单例，见模块 docstring）。

    RAGFLOW 配置全部来自数据库（页面写入），不再读环境变量。
    """
    return SqlRagflowConfigProvider(
        secret_repo=get_system_secret_repository(),
        setting_repo=get_system_setting_repository(),
        cipher=get_secret_cipher(),
        ttl_seconds=settings.system_settings_cache_ttl_seconds,
    )


@lru_cache(maxsize=1)
def get_ragflow_connection_probe() -> RagflowConnectionProbe:
    return RagflowClientConnectionProbe()


@lru_cache(maxsize=1)
def get_ragflow_dataset_catalog() -> RagflowDatasetCatalog:
    """知识库列表读取器。

    刻意**不加进程内缓存**：列表要反映当前生效凭据下的真实情况，
    管理员换连接后必须立刻看到变化。
    """
    return RagflowClientDatasetCatalog()


@lru_cache(maxsize=1)
def get_settings_service() -> SettingsService:
    return SettingsService(
        secret_repo=get_system_secret_repository(),
        setting_repo=get_system_setting_repository(),
        user_settings_repo=get_user_settings_repository(),
        cipher=get_secret_cipher(),
        config_provider=get_ragflow_config_provider(),
        connection_probe=get_ragflow_connection_probe(),
        dataset_catalog=get_ragflow_dataset_catalog(),
    )
