from fastapi import APIRouter, Depends, HTTPException, Query

from ...common.security.security import get_current_user_id
from ..application.system_service import TraceQueryService
from ..domain.errors import TraceNotFoundError
from ..infrastructure.dependencies import get_trace_query_service
from .schemas import AgentTraceResponse

router = APIRouter(
    prefix="/api/system",
    tags=["system"],
    dependencies=[Depends(get_current_user_id)],
)


@router.get("/agent-traces/{trace_id}", response_model=AgentTraceResponse)
async def get_agent_trace(
    trace_id: str,
    tenant_id: str = Query(default="default"),
    service: TraceQueryService = Depends(get_trace_query_service),
) -> AgentTraceResponse:
    try:
        payload = await service.get_trace(tenant_id=tenant_id, trace_id=trace_id)
    except TraceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return AgentTraceResponse(trace_id=trace_id, payload=payload)
