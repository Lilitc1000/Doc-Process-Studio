"""知识库基础设施依赖装配。

提供 FastAPI 依赖注入工厂，装配应用服务单例。
"""

from functools import lru_cache

from ..application.kb_service import KnowledgeBaseService
from ..application.ports import EmbeddingService, KnowledgeBaseRepository, VectorStore
from .embedding_service import OllamaEmbeddingService
from .kb_repository import SqlKnowledgeBaseRepository
from .vector_store import QdrantVectorStore


@lru_cache(maxsize=1)
def get_kb_repository() -> KnowledgeBaseRepository:
    return SqlKnowledgeBaseRepository()


@lru_cache(maxsize=1)
def get_vector_store() -> VectorStore:
    return QdrantVectorStore()


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    return OllamaEmbeddingService()


@lru_cache(maxsize=1)
def get_kb_service() -> KnowledgeBaseService:
    return KnowledgeBaseService(
        repository=get_kb_repository(),
        vector_store=get_vector_store(),
    )
