from typing import Any

from pydantic import BaseModel, Field

AgentTracePayload = dict[str, Any]


class AgentTraceRecord(BaseModel):
    trace_id: str = Field(..., description="追踪标识")
    payload: AgentTracePayload = Field(..., description="完整回放内容")


__all__ = ["AgentTracePayload", "AgentTraceRecord"]
