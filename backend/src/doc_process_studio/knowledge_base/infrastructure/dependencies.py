"""知识库基础设施依赖装配。

装配链路：``RagflowConfigProvider``（系统级凭据解析）→ ``RagflowClient``（HTTP）
→ ``RagflowKnowledgeBaseRepository``（缓存 + 映射）→ ``KnowledgeBaseService``（用例）。

**为什么这里不再用 ``@lru_cache`` 单例**：凭据现在来自数据库（管理员可在设置页修改），
而 ``@lru_cache(maxsize=1)`` 会把第一次构造时的 base_url / api_key 钉死到进程结束，
管理员改完密钥必须重启才生效。现在改为每次请求按当前配置构建。
代价可以忽略 —— ``RagflowClient`` 只是一层薄薄的参数容器，真正的
``httpx.AsyncClient`` 本来就是在每次调用时才创建和销毁的。
"""

from ...common.infrastructure.config import settings
from ...settings.infrastructure.dependencies import get_ragflow_config_provider
from ..application.kb_service import KnowledgeBaseService
from ..application.ports import KnowledgeBaseRepository
from .ragflow_client import RagflowClient
from .ragflow_repository import RagflowKnowledgeBaseRepository


async def get_ragflow_client() -> RagflowClient:
    """按当前生效的系统级配置装配 RAGFlow HTTP 客户端。

    管理员在设置页把 RAGFlow 停用时（``ragflow.enabled=false``），这里刻意传空凭据，
    让客户端的 ``enabled`` 属性为 False，从而所有调用都走"安全返回空值"的既有降级路径，
    而不是抛异常。
    """
    config = await get_ragflow_config_provider().resolve(scope="system")
    return RagflowClient(
        base_url=config.base_url if config.enabled else "",
        api_key=config.api_key if config.enabled else "",
        timeout_seconds=settings.ragflow_timeout_seconds,
        parse_timeout_seconds=settings.ragflow_parse_timeout_seconds,
        similarity_threshold=settings.ragflow_similarity_threshold,
        top_k=settings.kb_search_top_k,
    )


async def get_kb_repository() -> KnowledgeBaseRepository:
    return RagflowKnowledgeBaseRepository(
        client=await get_ragflow_client(),
        cache_ttl_seconds=settings.kb_cache_ttl_seconds,
    )


async def get_kb_service() -> KnowledgeBaseService:
    return KnowledgeBaseService(repository=await get_kb_repository())
