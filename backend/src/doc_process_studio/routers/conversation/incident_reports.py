from fastapi import APIRouter, HTTPException

from ...models.conversation.incident_report import (
    IncidentReportFormSchemaResponse,
    IncidentReportGenerateRequest,
    IncidentReportGenerateResponse,
    IncidentReportSessionCreateRequest,
    IncidentReportSessionDetail,
    IncidentReportSessionListResponse,
    IncidentReportSessionSummary,
    IncidentReportSessionTitleUpdateRequest,
    IncidentReportSessionUpdateRequest,
)
from ...services.chat.incident_reports import (
    create_incident_report_session,
    delete_incident_report_session,
    generate_incident_report_session_attachment,
    get_incident_report_form_schema,
    get_incident_report_session,
    list_incident_report_sessions,
    update_incident_report_session_title,
    update_incident_report_session_snapshot,
)

router = APIRouter(prefix="/api/incident-report", tags=["incident-report"])


@router.get("/schema", response_model=IncidentReportFormSchemaResponse)
async def get_form_schema() -> IncidentReportFormSchemaResponse:
    return get_incident_report_form_schema()


@router.get("/sessions", response_model=IncidentReportSessionListResponse)
async def list_sessions() -> IncidentReportSessionListResponse:
    return await list_incident_report_sessions()


@router.post("/sessions", response_model=IncidentReportSessionSummary)
async def create_session(
    payload: IncidentReportSessionCreateRequest,
) -> IncidentReportSessionSummary:
    return await create_incident_report_session(title=payload.title)


@router.get("/sessions/{session_id}", response_model=IncidentReportSessionDetail)
async def get_session(session_id: str) -> IncidentReportSessionDetail:
    session = await get_incident_report_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="未找到对应事故报告会话。")
    return session


@router.put("/sessions/{session_id}", response_model=IncidentReportSessionDetail)
async def update_session(
    session_id: str,
    payload: IncidentReportSessionUpdateRequest,
) -> IncidentReportSessionDetail:
    try:
        session = await update_incident_report_session_snapshot(
            session_id=session_id,
            snapshot=payload.snapshot,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if session is None:
        raise HTTPException(status_code=404, detail="未找到对应事故报告会话。")
    return session


@router.post(
    "/sessions/{session_id}/generate",
    response_model=IncidentReportGenerateResponse,
)
async def generate_session_attachment(
    session_id: str,
    payload: IncidentReportGenerateRequest,
) -> IncidentReportGenerateResponse:
    try:
        response = await generate_incident_report_session_attachment(
            session_id=session_id,
            model=payload.model,
            reranker_model=payload.reranker_model,
            output_name=payload.output_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    if response is None:
        raise HTTPException(status_code=404, detail="未找到对应事故报告会话。")
    return response


@router.patch("/sessions/{session_id}/title", response_model=IncidentReportSessionSummary)
async def rename_session(
    session_id: str,
    payload: IncidentReportSessionTitleUpdateRequest,
) -> IncidentReportSessionSummary:
    session = await update_incident_report_session_title(
        session_id=session_id,
        title=payload.title,
    )
    if session is None:
        raise HTTPException(status_code=404, detail="未找到对应事故报告会话。")
    return session


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str) -> dict[str, bool]:
    deleted = await delete_incident_report_session(session_id)
    return {"deleted": deleted}
