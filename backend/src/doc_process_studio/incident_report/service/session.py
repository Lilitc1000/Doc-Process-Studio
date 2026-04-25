import base64
from typing import Any
from uuid import uuid4

from ..models.incident_report import (
    IncidentFormAnswer,
    IncidentGeneratedVersion,
    IncidentReportSessionSnapshot,
    IncidentReportSessionSummary,
    build_empty_incident_snapshot,
)
from ..schemas.response import (
    IncidentBodyGenerateResponse,
    IncidentReportFormSchemaResponse,
    IncidentReportPreviewResponse,
    IncidentReportSessionDetail,
    IncidentReportSessionListResponse,
)
from ...system.service.trace_store import delete_agent_traces_for_conversation
from ...shared.dtutils import utcnow
from ...chat.service.attachments import delete_attachments_for_conversation
from ...skill.service.conversation_store import clear_conversation_state
from .constants import INCIDENT_REPORT_SCHEMA_INTRO
from .generation import (
    _run_body_generation_with_trace,
    _build_default_title,
    _build_quick_generation_request,
    _build_section_generation_prompt,
    _build_summary_from_detail,
    _apply_quick_generation_payload,
    _apply_section_payload,
)
from .normalization import normalize_text
from .preview import (
    build_initial_output_name,
    build_preview_output_name,
    load_docx_bytes_from_attachment,
    preview_cache_get,
    preview_cache_set,
    preview_template_token,
    render_docx_bytes_from_report_data,
    save_docx_bytes_as_generated_attachment,
    build_preview_payload_from_docx_bytes,
)
from .report_data import answer_text, build_report_data_from_snapshot
from .translation import stable_payload_hash, translate_report_data_to_english
from .db_session_store import (
    delete_incident_session_records,
    list_incident_session_ids,
    load_incident_session_snapshot,
    load_incident_session_summary,
    save_incident_session_snapshot,
    save_incident_session_summary,
    touch_incident_session_updated_at,
)


async def list_incident_report_sessions() -> IncidentReportSessionListResponse:
    session_ids = await list_incident_session_ids()
    sessions: list[IncidentReportSessionSummary] = []
    for session_id in session_ids:
        summary = await load_incident_session_summary(session_id)
        if summary is not None:
            sessions.append(summary)
    return IncidentReportSessionListResponse(sessions=sessions)


async def get_incident_report_session(
    session_id: str,
) -> IncidentReportSessionDetail | None:
    summary = await load_incident_session_summary(session_id)
    snapshot = await load_incident_session_snapshot(session_id)
    if summary is None or snapshot is None:
        return None
    return IncidentReportSessionDetail(
        **summary.model_dump(),
        snapshot=snapshot,
    )


async def create_incident_report_session(
    *,
    title: str,
) -> IncidentReportSessionSummary:
    now = utcnow()
    session_id = uuid4().hex
    summary = IncidentReportSessionSummary(
        id=session_id,
        title=(title.strip() or _build_default_title(now)),
        status="draft",
        created_at=now,
        updated_at=now,
    )
    snapshot = build_empty_incident_snapshot()
    try:
        base_report_data, _ = build_report_data_from_snapshot(
            snapshot,
            strict_required=False,
        )
        if base_report_data is not None:
            english_base_report_data = await translate_report_data_to_english(
                report_data=base_report_data,
            )
            base_docx_bytes = render_docx_bytes_from_report_data(
                english_base_report_data
            )
            base_attachment = save_docx_bytes_as_generated_attachment(
                docx_bytes=base_docx_bytes,
                conversation_id=session_id,
                output_name=build_initial_output_name(
                    session_title=summary.title,
                    session_id=session_id,
                ),
            )
            base_label = f"V1 {now.strftime('%Y-%m-%d %H:%M:%S')}"
            snapshot.generated_versions = [
                IncidentGeneratedVersion(
                    version=1,
                    label=base_label,
                    generated_at=now,
                    attachment=base_attachment,
                    report_data=english_base_report_data,
                )
            ]
            snapshot.generated_attachment = base_attachment
            snapshot.report_data = english_base_report_data
            snapshot.generated_at = now
    except Exception:
        pass
    await save_incident_session_summary(summary)
    await save_incident_session_snapshot(session_id, snapshot)
    await touch_incident_session_updated_at(session_id)
    return summary


async def update_incident_report_session_snapshot(
    *,
    session_id: str,
    snapshot: IncidentReportSessionSnapshot,
) -> IncidentReportSessionDetail | None:
    existing = await get_incident_report_session(session_id)
    if existing is None:
        return None

    now = utcnow()
    next_summary = _build_summary_from_detail(
        existing,
        status="draft",
        updated_at=now,
    )
    next_snapshot = existing.snapshot.model_copy(deep=True)
    next_snapshot.form_answers = snapshot.form_answers
    next_snapshot.polish_error = None

    await save_incident_session_summary(next_summary)
    await save_incident_session_snapshot(session_id, next_snapshot)
    await touch_incident_session_updated_at(session_id)
    return IncidentReportSessionDetail(
        **next_summary.model_dump(),
        snapshot=next_snapshot,
    )


async def update_incident_report_session_title(
    *,
    session_id: str,
    title: str,
) -> IncidentReportSessionSummary | None:
    detail = await get_incident_report_session(session_id)
    if detail is None:
        return None
    now = utcnow()
    summary = _build_summary_from_detail(
        detail,
        title=title.strip(),
        updated_at=now,
    )
    await save_incident_session_summary(summary)
    await touch_incident_session_updated_at(session_id)
    return summary


async def generate_incident_report_body_from_quick_input(
    *,
    session_id: str,
    model: str,
    reranker_model: str | None = None,
) -> IncidentBodyGenerateResponse | None:
    detail = await get_incident_report_session(session_id)
    if detail is None:
        return None
    if not answer_text(detail.snapshot, "quick_narrative"):
        raise ValueError("请先填写快填模式的事故简述。")

    prompt, context_json = _build_quick_generation_request(
        detail.snapshot
    )

    def _apply(form_answers: dict[str, IncidentFormAnswer], payload: dict[str, Any]) -> None:
        _apply_quick_generation_payload(form_answers=form_answers, payload=payload)

    return await _run_body_generation_with_trace(
        detail=detail,
        model=model,
        reranker_model=reranker_model,
        section_id="quick",
        timeline_index=None,
        prompt=prompt,
        context_json=context_json,
        apply_payload=_apply,
    )


async def polish_incident_report_section(
    *,
    session_id: str,
    model: str,
    reranker_model: str | None = None,
    section_id: str,
    timeline_index: int | None = None,
) -> IncidentBodyGenerateResponse | None:
    detail = await get_incident_report_session(session_id)
    if detail is None:
        return None
    prompt, context_json = _build_section_generation_prompt(
        detail.snapshot,
        section_id=section_id,
        timeline_index=timeline_index,
    )

    def _apply(form_answers: dict[str, IncidentFormAnswer], payload: dict[str, Any]) -> None:
        _apply_section_payload(
            form_answers=form_answers,
            section_id=section_id,
            timeline_index=timeline_index,
            payload=payload,
        )

    return await _run_body_generation_with_trace(
        detail=detail,
        model=model,
        reranker_model=reranker_model,
        section_id=section_id,
        timeline_index=timeline_index,
        prompt=prompt,
        context_json=context_json,
        apply_payload=_apply,
    )


async def preview_incident_report_attachment(
    *,
    session_id: str,
    version: int | None = None,
    model: str | None = None,
    reranker_model: str | None = None,
) -> IncidentReportPreviewResponse | None:
    detail = await get_incident_report_session(session_id)
    if detail is None:
        return None

    template_token = preview_template_token()

    if version is not None:
        target_version = next(
            (item for item in detail.snapshot.generated_versions if item.version == version),
            None,
        )
        if target_version is None:
            raise ValueError("未找到对应历史版本。")
        version_cache_key = (
            f"version:{target_version.attachment.attachment_id}:{template_token}"
        )
        cached_version_preview = preview_cache_get(version_cache_key)
        if cached_version_preview is not None:
            return cached_version_preview
        docx_bytes = load_docx_bytes_from_attachment(
            target_version.attachment.attachment_id
        )
        html, pdf_base64, warnings = build_preview_payload_from_docx_bytes(
            docx_bytes
        )
        version_payload = IncidentReportPreviewResponse(
            source="version",
            version=target_version.version,
            label=target_version.label,
            html=html,
            docx_base64=None,
            docx_file_name=None,
            pdf_base64=pdf_base64,
            warnings=warnings,
        )
        preview_cache_set(cache_key=version_cache_key, payload=version_payload)
        return version_payload

    draft_report_data, _ = build_report_data_from_snapshot(
        detail.snapshot,
        strict_required=False,
    )
    if draft_report_data is None:
        raise RuntimeError("当前草稿无法生成预览。")
    preview_model = normalize_text(model) or normalize_text(reranker_model)
    draft_hash = stable_payload_hash(draft_report_data)
    draft_cache_key = (
        f"draft:{session_id}:{preview_model}:{template_token}:{draft_hash}"
    )
    cached_draft_preview = preview_cache_get(draft_cache_key)
    if cached_draft_preview is not None:
        return cached_draft_preview
    translated_report_data = await translate_report_data_to_english(
        report_data=draft_report_data,
    )
    draft_docx_bytes = render_docx_bytes_from_report_data(translated_report_data)
    html, pdf_base64, warnings = build_preview_payload_from_docx_bytes(
        draft_docx_bytes
    )
    draft_payload = IncidentReportPreviewResponse(
        source="draft",
        version=None,
        label="Realtime Draft Preview",
        html=html,
        docx_base64=base64.b64encode(draft_docx_bytes).decode("ascii"),
        docx_file_name=build_preview_output_name(
            session_title=detail.title,
            session_id=detail.id,
        ),
        pdf_base64=pdf_base64,
        warnings=warnings,
    )
    preview_cache_set(cache_key=draft_cache_key, payload=draft_payload)
    return draft_payload


async def delete_incident_report_session(session_id: str) -> bool:
    deleted_session = await delete_incident_session_records(session_id)
    deleted_attachments = delete_attachments_for_conversation(session_id)
    deleted_traces = await delete_agent_traces_for_conversation(
        conversation_id=session_id
    )
    await clear_conversation_state(session_id)
    return bool(deleted_session or deleted_attachments > 0 or deleted_traces > 0)


def get_incident_report_form_schema() -> IncidentReportFormSchemaResponse:
    return IncidentReportFormSchemaResponse(
        intro_message=INCIDENT_REPORT_SCHEMA_INTRO,
        steps=[],
    )
