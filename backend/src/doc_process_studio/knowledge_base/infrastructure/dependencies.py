"""知识库基础设施依赖装配。

装配链路：``RagflowClient``（HTTP）→ ``RagflowKnowledgeBaseRepository``（缓存 + 映射）
→ ``KnowledgeBaseService``（用例）。全部为进程内单例。
"""

from functools import lru_cache

from ...common.infrastructure.config import settings
from ..application.kb_service import KnowledgeBaseService
from ..application.ports import KnowledgeBaseRepository
from .ragflow_client import RagflowClient
from .ragflow_repository import RagflowKnowledgeBaseRepository


@lru_cache(maxsize=1)
def get_ragflow_client() -> RagflowClient:
    """装配 RAGFlow HTTP 客户端。"""
    return RagflowClient(
        base_url=settings.ragflow_base_url,
        api_key=settings.ragflow_api_key,
        timeout_seconds=settings.ragflow_timeout_seconds,
        parse_timeout_seconds=settings.ragflow_parse_timeout_seconds,
        similarity_threshold=settings.ragflow_similarity_threshold,
        top_k=settings.kb_search_top_k,
    )


@lru_cache(maxsize=1)
def get_kb_repository() -> KnowledgeBaseRepository:
    return RagflowKnowledgeBaseRepository(
        client=get_ragflow_client(),
        cache_ttl_seconds=settings.kb_cache_ttl_seconds,
    )


@lru_cache(maxsize=1)
def get_kb_service() -> KnowledgeBaseService:
    return KnowledgeBaseService(repository=get_kb_repository())
