"""系统基础设施依赖装配。

提供 FastAPI 依赖注入工厂，装配应用服务单例。
"""

from functools import lru_cache

from ..application.ports import ModelCatalog, TraceStore
from ..application.system_service import ModelQueryService, TraceQueryService
from .model_catalog import OllamaModelCatalog
from .trace_store import RedisTraceStore


@lru_cache(maxsize=1)
def get_trace_store() -> TraceStore:
    return RedisTraceStore()


@lru_cache(maxsize=1)
def get_model_catalog() -> ModelCatalog:
    return OllamaModelCatalog()


@lru_cache(maxsize=1)
def get_trace_query_service() -> TraceQueryService:
    return TraceQueryService(trace_store=get_trace_store())


@lru_cache(maxsize=1)
def get_model_query_service() -> ModelQueryService:
    return ModelQueryService(model_catalog=get_model_catalog())
