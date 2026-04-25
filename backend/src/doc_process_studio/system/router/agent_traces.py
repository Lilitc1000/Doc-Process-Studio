from fastapi import APIRouter, Depends, HTTPException, Query

from ..schemas import AgentTraceResponse
from ..service.trace_store import load_agent_trace
from ...core.security import get_current_user_id

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/agent-traces/{trace_id}", response_model=AgentTraceResponse)
async def get_agent_trace(
    trace_id: str,
    tenant_id: str = Query(default="default"),
    user_id: str = Depends(get_current_user_id),
) -> AgentTraceResponse:
    payload = await load_agent_trace(
        tenant_id=tenant_id,
        trace_id=trace_id,
    )
    if payload is None:
        raise HTTPException(status_code=404, detail="未找到对应 trace_id 的回放记录。")
    return AgentTraceResponse(trace_id=trace_id, payload=payload)
