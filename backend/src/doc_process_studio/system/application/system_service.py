"""系统应用服务。

用例编排：agent trace 查询、模型列表查询。
"""

from typing import Any

from ..domain.errors import TraceNotFoundError
from .ports import ModelCatalog, TraceStore


class TraceQueryService:
    """Agent trace 查询用例服务。"""

    def __init__(self, *, trace_store: TraceStore) -> None:
        self._traces = trace_store

    async def get_trace(self, *, tenant_id: str, trace_id: str) -> dict[str, Any]:
        payload = await self._traces.load(tenant_id=tenant_id, trace_id=trace_id)
        if payload is None:
            raise TraceNotFoundError("未找到对应 trace_id 的回放记录。")
        return payload


class ModelQueryService:
    """模型列表查询用例服务。"""

    def __init__(self, *, model_catalog: ModelCatalog) -> None:
        self._catalog = model_catalog

    async def list_remote_models(self) -> list[str]:
        return await self._catalog.list_remote_model_names()
