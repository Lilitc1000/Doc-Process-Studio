"""Redis trace 存储实现。

实现 TraceStore 端口，委托 service/trace_store.py 的 load_agent_trace。
"""

from typing import Any

from ..application.ports import TraceStore
from ..service.trace_store import load_agent_trace


class RedisTraceStore(TraceStore):
    """基于 Redis 的 agent trace 存储。"""

    async def load(self, *, tenant_id: str, trace_id: str) -> dict[str, Any] | None:
        return await load_agent_trace(tenant_id=tenant_id, trace_id=trace_id)
