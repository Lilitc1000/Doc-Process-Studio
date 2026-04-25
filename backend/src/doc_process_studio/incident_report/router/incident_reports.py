from fastapi import APIRouter, Depends, HTTPException

from ..models.incident_report import IncidentReportSessionSummary
from ..schemas.request import (
    IncidentBodyQuickGenerateRequest,
    IncidentBodySectionGenerateRequest,
    IncidentReportPreviewRequest,
    IncidentReportSessionCreateRequest,
    IncidentReportSessionTitleUpdateRequest,
    IncidentReportSessionUpdateRequest,
)
from ..schemas.response import (
    IncidentBodyGenerateResponse,
    IncidentReportFormSchemaResponse,
    IncidentReportPreviewResponse,
    IncidentReportSessionDetail,
    IncidentReportSessionListResponse,
)
from ..service.session import (
    create_incident_report_session,
    delete_incident_report_session,
    generate_incident_report_body_from_quick_input,
    get_incident_report_form_schema,
    get_incident_report_session,
    list_incident_report_sessions,
    preview_incident_report_attachment,
    polish_incident_report_section,
    update_incident_report_session_title,
    update_incident_report_session_snapshot,
)
from ...core.security import get_current_user_id

router = APIRouter(prefix="/api/incident-report", tags=["incident-report"])


@router.get("/schema", response_model=IncidentReportFormSchemaResponse)
async def get_form_schema() -> IncidentReportFormSchemaResponse:
    return get_incident_report_form_schema()


@router.get("/sessions", response_model=IncidentReportSessionListResponse)
async def list_sessions(
    user_id: str = Depends(get_current_user_id),
) -> IncidentReportSessionListResponse:
    return await list_incident_report_sessions()


@router.post("/sessions", response_model=IncidentReportSessionSummary)
async def create_session(
    payload: IncidentReportSessionCreateRequest,
    user_id: str = Depends(get_current_user_id),
) -> IncidentReportSessionSummary:
    return await create_incident_report_session(title=payload.title)


@router.get("/sessions/{session_id}", response_model=IncidentReportSessionDetail)
async def get_session(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
) -> IncidentReportSessionDetail:
    session = await get_incident_report_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="未找到对应事故报告会话。")
    return session


@router.put("/sessions/{session_id}", response_model=IncidentReportSessionDetail)
async def update_session(
    session_id: str,
    payload: IncidentReportSessionUpdateRequest,
    user_id: str = Depends(get_current_user_id),
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
    "/sessions/{session_id}/body/quick-generate",
    response_model=IncidentBodyGenerateResponse,
)
async def quick_generate_body(
    session_id: str,
    payload: IncidentBodyQuickGenerateRequest,
    user_id: str = Depends(get_current_user_id),
) -> IncidentBodyGenerateResponse:
    try:
        response = await generate_incident_report_body_from_quick_input(
            session_id=session_id,
            model=payload.model,
            reranker_model=payload.reranker_model,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    if response is None:
        raise HTTPException(status_code=404, detail="未找到对应事故报告会话。")
    return response


@router.post(
    "/sessions/{session_id}/body/section-generate",
    response_model=IncidentBodyGenerateResponse,
)
async def generate_body_section(
    session_id: str,
    payload: IncidentBodySectionGenerateRequest,
    user_id: str = Depends(get_current_user_id),
) -> IncidentBodyGenerateResponse:
    try:
        response = await polish_incident_report_section(
            session_id=session_id,
            model=payload.model,
            reranker_model=payload.reranker_model,
            section_id=payload.section_id,
            timeline_index=payload.timeline_index,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    if response is None:
        raise HTTPException(status_code=404, detail="未找到对应事故报告会话。")
    return response


@router.post(
    "/sessions/{session_id}/preview",
    response_model=IncidentReportPreviewResponse,
)
async def preview_session_attachment(
    session_id: str,
    payload: IncidentReportPreviewRequest,
    user_id: str = Depends(get_current_user_id),
) -> IncidentReportPreviewResponse:
    try:
        response = await preview_incident_report_attachment(
            session_id=session_id,
            version=payload.version,
            model=payload.model,
            reranker_model=payload.reranker_model,
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
    user_id: str = Depends(get_current_user_id),
) -> IncidentReportSessionSummary:
    session = await update_incident_report_session_title(
        session_id=session_id,
        title=payload.title,
    )
    if session is None:
        raise HTTPException(status_code=404, detail="未找到对应事故报告会话。")
    return session


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
) -> dict[str, bool]:
    deleted = await delete_incident_report_session(session_id)
    return {"deleted": deleted}
