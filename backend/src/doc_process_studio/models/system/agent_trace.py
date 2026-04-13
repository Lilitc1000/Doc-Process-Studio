from pydantic import BaseModel, Field


class AgentTraceResponse(BaseModel):
    trace_id: str = Field(..., description="追踪标识")
    payload: dict = Field(..., description="完整回放内容")

