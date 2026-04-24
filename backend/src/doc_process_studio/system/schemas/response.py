from pydantic import BaseModel, Field

from ..models.agent_trace import AgentTracePayload


class AgentTraceResponse(BaseModel):
    trace_id: str = Field(...)
    payload: AgentTracePayload = Field(...)


class OllamaModelItem(BaseModel):
    name: str = Field(...)


class OllamaModelListResponse(BaseModel):
    models: list[OllamaModelItem] = Field(default_factory=list)


__all__ = [
    "AgentTraceResponse",
    "OllamaModelItem",
    "OllamaModelListResponse",
]
