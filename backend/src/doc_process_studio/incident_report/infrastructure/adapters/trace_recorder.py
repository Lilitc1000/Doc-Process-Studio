"""追踪记录器端口实现。

封装 system.infrastructure.trace_store 的跨域调用。
"""

import logging
from typing import Any

from ....system.infrastructure.trace_store import AgentTraceRecorder
from ...application.ports import TraceRecorderPort

logger = logging.getLogger(__name__)


class SystemTraceRecorder(TraceRecorderPort):
    """基于 system.trace_store 的追踪记录器。"""

    def create_recorder(
        self,
        *,
        trace_id: str,
        tenant_id: str,
        conversation_id: str,
        user_message_id: str,
        model: str,
        reranker_model: str,
    ) -> AgentTraceRecorder:
        return AgentTraceRecorder(
            trace_id=trace_id,
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            user_message_id=user_message_id,
            model=model,
            reranker_model=reranker_model,
        )

    async def add_event(self, recorder: AgentTraceRecorder, event_type: str, detail: dict[str, Any]) -> None:
        recorder.add_event(event_type=event_type, detail=detail)

    async def set_final(self, recorder: AgentTraceRecorder, *, done_reason: str, error: str | None) -> None:
        recorder.set_final(done_reason=done_reason, error=error)

    async def flush_recorder(self, recorder: AgentTraceRecorder) -> None:
        try:
            await recorder.flush()
        except Exception:
            logger.warning("Failed to flush trace recorder for trace_id=%s", recorder.trace_id, exc_info=True)
