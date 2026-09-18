"""RAGFlow 连通性自检实现。

复用 :class:`RagflowClient` 的 ``probe_connection``，不另写一套 HTTP 逻辑，
避免"设置页测通了、实际检索却失败"这种两套判断标准的问题。
"""

from __future__ import annotations

from ...common.infrastructure.config import settings
from ...knowledge_base.infrastructure.ragflow_client import RagflowClient
from ..application.ports import RagflowConnectionProbe
from ..domain.values import RagflowConfig


class RagflowClientConnectionProbe(RagflowConnectionProbe):
    """用 RagflowClient 打一次 ``GET /api/v1/datasets`` 做自检。"""

    def __init__(self, *, timeout_seconds: float | None = None) -> None:
        self._timeout = timeout_seconds if timeout_seconds is not None else settings.ragflow_timeout_seconds

    async def probe(self, config: RagflowConfig) -> tuple[bool, str, int]:
        client = RagflowClient(
            base_url=config.base_url,
            api_key=config.api_key,
            timeout_seconds=self._timeout,
        )
        return await client.probe_connection()
