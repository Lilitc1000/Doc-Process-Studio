import json
import logging
import re
from copy import deepcopy
from typing import Any, Callable

import httpx

from ..schemas.common import (
    IncidentFormAnswer,
    IncidentFormSnapshot,
    PermissionDenied,
)
from ..schemas.response import IncidentBodyGenerateResponse
from ...system.service.error_detail import summarize_exception
from ...system.service.trace_store import AgentTraceRecorder
from ...shared.dtutils import utcnow
from ...shared.text_utils import parse_json_object
from ...core.config import settings
from ...core.ollama import stream_chat_completion
from .constants import (
    BODY_AFFECTED_DATE,
    BODY_BUSINESS_IMPACT,
    BODY_DESCRIPTION,
    BODY_FOLLOW_UP,
    BODY_IMPACT_SCOPE,
    BODY_IMPACT_SEVERITY,
    BODY_ROOT_CAUSE,
    BODY_TIMELINE,
    BODY_TRIGGER,
    MANUAL_FAULT_DATE,
    MANUAL_FAULT_TIME,
    QUICK_FOLLOW_UP_ACTION,
    QUICK_IMPACT_SCOPE,
    QUICK_IMPACT_SEVERITY,
    QUICK_NARRATIVE,
    QUICK_ROOT_CAUSE_GUESS,
    QUICK_TIMELINE,
    SYSTEM_DOCUMENT_SKILL_ID,
)
from .normalization import (
    compose_datetime_text,
    normalize_text,
    normalize_timeline_items,
    normalize_time_text,
    split_lines,
)
from .reference import resolve_generation_reference_context
from .report_data import answer_text, answer_value, answer_value_from_answers, set_answer, set_answer_if_non_empty
from ...chat.service.streaming import extract_delta_text, extract_done_reason
from .report_store import load_report_orm, update_report_record

logger = logging.getLogger(__name__)


def _build_default_title(now: Any = None) -> str:
    current = now or utcnow()
    return f"Incident-Report-{current.strftime('%Y/%m/%d %H:%M')}"


def _resolve_document_assistant_prompt() -> str:
    from ...skill.service.registry import get_skill_interface
    try:
        return normalize_text(get_skill_interface(SYSTEM_DOCUMENT_SKILL_ID).default_prompt)
    except Exception:
        logger.debug("Failed to resolve document assistant prompt for skill_id=%s", SYSTEM_DOCUMENT_SKILL_ID)
        return ""


async def _run_plain_chat_completion(
    *,
    model: str,
    messages: list[dict[str, Any]],
) -> tuple[str, str]:
    content_parts: list[str] = []
    done_reason = "stop"
    async for chunk_payload in stream_chat_completion(
        model=model,
        messages=messages,
        tools=[],
    ):
        if chunk_payload is None:
            break
        delta_text = extract_delta_text(chunk_payload)
        if delta_text:
            content_parts.append(delta_text)
        chunk_done_reason = extract_done_reason(chunk_payload)
        if chunk_done_reason:
            done_reason = chunk_done_reason
    return "".join(content_parts), done_reason


async def _flush_trace_safely(recorder: AgentTraceRecorder) -> None:
    try:
        await recorder.flush()
    except Exception:
        logger.warning("Failed to flush trace recorder for trace_id=%s", recorder.trace_id, exc_info=True)


def _build_quick_generation_context(
    snapshot: IncidentFormSnapshot,
) -> dict[str, Any]:
    return {
        "quick_inputs": {
            "narrative": answer_text(snapshot, QUICK_NARRATIVE),
            "timeline": normalize_timeline_items(answer_value(snapshot, QUICK_TIMELINE)),
            "impact_scope": answer_text(snapshot, QUICK_IMPACT_SCOPE),
            "impact_severity": answer_text(snapshot, QUICK_IMPACT_SEVERITY),
            "root_cause_guess": answer_text(snapshot, QUICK_ROOT_CAUSE_GUESS),
            "follow_up_action": answer_text(snapshot, QUICK_FOLLOW_UP_ACTION),
        },
        "manual_cover_context": {
            "fault_date": answer_text(snapshot, MANUAL_FAULT_DATE),
            "fault_time": answer_text(snapshot, MANUAL_FAULT_TIME),
            "site_id": answer_text(snapshot, "manual_site_id"),
            "system": answer_text(snapshot, "manual_system"),
            "location": answer_text(snapshot, "manual_location"),
            "fault_symptom": answer_text(snapshot, "manual_fault_symptom"),
        },
        "existing_full_body": {
            "description": answer_text(snapshot, BODY_DESCRIPTION),
            "affected_date_summary": answer_text(snapshot, BODY_AFFECTED_DATE),
            "timeline": normalize_timeline_items(answer_value(snapshot, BODY_TIMELINE)),
            "impact_scope": answer_text(snapshot, BODY_IMPACT_SCOPE),
            "impact_severity": answer_text(snapshot, BODY_IMPACT_SEVERITY),
            "business_impact": answer_text(snapshot, BODY_BUSINESS_IMPACT),
            "trigger": answer_text(snapshot, BODY_TRIGGER),
            "root_cause": answer_text(snapshot, BODY_ROOT_CAUSE),
            "follow_up_actions": answer_text(snapshot, BODY_FOLLOW_UP),
        },
    }


def _build_quick_generation_request(
    snapshot: IncidentFormSnapshot,
) -> tuple[str, str]:
    prompt = (
        "You will perform a quick-fill to full-mode generation. "
        "Expand the quick-fill inputs into complete mode fields according to the reference documentation. "
        "Do not fabricate facts not present in the context; use conservative but actionable expressions when information is insufficient. "
        "Output JSON only, no explanations. "
        "JSON keys must be: description, affected_date_summary, timeline, impact_scope, impact_severity, "
        "business_impact, trigger, root_cause, follow_up_actions. "
        "timeline is an array, each item must contain time, event, resolution, evidence."
    )
    return prompt, json.dumps(_build_quick_generation_context(snapshot), ensure_ascii=False)


def _build_section_generation_prompt(
    snapshot: IncidentFormSnapshot,
    *,
    section_id: str,
    timeline_index: int | None,
) -> tuple[str, str]:
    section_key = section_id.strip().lower()
    body_context = {
        "description": answer_text(snapshot, BODY_DESCRIPTION),
        "affected_date_summary": answer_text(snapshot, BODY_AFFECTED_DATE),
        "timeline": normalize_timeline_items(answer_value(snapshot, BODY_TIMELINE)),
        "impact_scope": answer_text(snapshot, BODY_IMPACT_SCOPE),
        "impact_severity": answer_text(snapshot, BODY_IMPACT_SEVERITY),
        "business_impact": answer_text(snapshot, BODY_BUSINESS_IMPACT),
        "trigger": answer_text(snapshot, BODY_TRIGGER),
        "root_cause": answer_text(snapshot, BODY_ROOT_CAUSE),
        "follow_up_actions": answer_text(snapshot, BODY_FOLLOW_UP),
        "quick_narrative": answer_text(snapshot, QUICK_NARRATIVE),
    }

    if section_key == "description":
        return (
            'Generate the incident description section only. Output JSON: {"body_description":"..."}. Do not modify other sections.',
            json.dumps(body_context, ensure_ascii=False),
        )
    if section_key == "timeline":
        return (
            'Generate the timeline section only. Output JSON: {"body_timeline":[{"time":"","event":"","resolution":"","evidence":""}],'
            '"body_affected_date_summary":"..."}. Do not modify other sections.',
            json.dumps(body_context, ensure_ascii=False),
        )
    if section_key == "impact":
        return (
            'Generate impact scope, severity, and business impact only. Output JSON: {"body_impact_scope":"...",'
            '"body_impact_severity":"...","body_business_impact":"separated by newlines"}. Do not modify other sections.',
            json.dumps(body_context, ensure_ascii=False),
        )
    if section_key == "root_cause":
        return (
            'Generate trigger and root cause only. Output JSON: {"body_trigger":"...","body_root_cause":"..."}. Do not modify other sections.',
            json.dumps(body_context, ensure_ascii=False),
        )
    if section_key == "follow_up":
        return (
            'Generate follow-up actions only. Output JSON: {"body_follow_up":"separated by newlines"}. Do not modify other sections.',
            json.dumps(body_context, ensure_ascii=False),
        )
    if section_key == "timeline_item":
        timeline = body_context["timeline"]
        if timeline_index is None or timeline_index < 0 or timeline_index >= len(timeline):
            raise ValueError("Invalid timeline item index.")
        return (
            'Generate the specified timeline item only. Output JSON: {"item":{"time":"","event":"","resolution":"","evidence":""}}. '
            "Do not modify other timeline items.",
            json.dumps(
                {
                    "target_item": timeline[timeline_index],
                    "full_timeline": timeline,
                    "description": body_context["description"],
                    "quick_narrative": body_context["quick_narrative"],
                },
                ensure_ascii=False,
            ),
        )
    raise ValueError("Unsupported section_id.")


def _build_body_generation_messages(
    *,
    prompt: str,
    context_json: str,
    reference_context: str,
) -> list[dict[str, Any]]:
    document_assistant_prompt = _resolve_document_assistant_prompt()
    system_prompt_prefix = (
        f"System-level skill prompt ({SYSTEM_DOCUMENT_SKILL_ID}): {document_assistant_prompt}\n"
        if document_assistant_prompt
        else ""
    )
    return [
        {
            "role": "system",
            "content": (
                f"{system_prompt_prefix}"
                "You are an incident report body assistant. "
                "Follow the reference documentation first, then generate content based on the current context. "
                "All output must be in English. "
                "Output JSON only, no code blocks, no fabricated facts."
            ),
        },
        {
            "role": "user",
            "content": (
                f"{prompt}\n"
                f"Reference documentation:\n{reference_context}\n"
                f"Current context:\n{context_json}"
            ),
        },
    ]


def _apply_quick_generation_payload(
    *,
    form_answers: dict[str, IncidentFormAnswer],
    payload: dict[str, Any],
) -> None:
    def _pick_non_empty_text(*values: Any) -> str:
        for value in values:
            text = normalize_text(value)
            if text:
                return text
        return ""

    set_answer(
        form_answers,
        BODY_DESCRIPTION,
        _pick_non_empty_text(
            payload.get("description"),
            answer_value_from_answers(form_answers, BODY_DESCRIPTION),
            answer_value_from_answers(form_answers, QUICK_NARRATIVE),
        ),
    )
    set_answer(
        form_answers,
        BODY_AFFECTED_DATE,
        _pick_non_empty_text(
            payload.get("affected_date_summary"),
            answer_value_from_answers(form_answers, BODY_AFFECTED_DATE),
        ),
    )
    timeline = normalize_timeline_items(payload.get("timeline"))
    if not timeline:
        timeline = normalize_timeline_items(
            answer_value_from_answers(form_answers, BODY_TIMELINE)
        )
    if not timeline:
        timeline = normalize_timeline_items(
            answer_value_from_answers(form_answers, QUICK_TIMELINE)
        )
    if timeline:
        set_answer(form_answers, BODY_TIMELINE, timeline)
        set_answer(form_answers, QUICK_TIMELINE, timeline)
    set_answer(
        form_answers,
        BODY_IMPACT_SCOPE,
        _pick_non_empty_text(
            payload.get("impact_scope"),
            answer_value_from_answers(form_answers, BODY_IMPACT_SCOPE),
            answer_value_from_answers(form_answers, QUICK_IMPACT_SCOPE),
        ),
    )
    set_answer(
        form_answers,
        BODY_IMPACT_SEVERITY,
        _pick_non_empty_text(
            payload.get("impact_severity"),
            answer_value_from_answers(form_answers, BODY_IMPACT_SEVERITY),
            answer_value_from_answers(form_answers, QUICK_IMPACT_SEVERITY),
        ),
    )
    set_answer(
        form_answers,
        BODY_BUSINESS_IMPACT,
        _pick_non_empty_text(
            "\n".join(split_lines(payload.get("business_impact"))),
            answer_value_from_answers(form_answers, BODY_BUSINESS_IMPACT),
        ),
    )
    set_answer(
        form_answers,
        BODY_TRIGGER,
        _pick_non_empty_text(
            payload.get("trigger"),
            answer_value_from_answers(form_answers, BODY_TRIGGER),
            payload.get("root_cause"),
            answer_value_from_answers(form_answers, QUICK_ROOT_CAUSE_GUESS),
        ),
    )
    set_answer(
        form_answers,
        BODY_ROOT_CAUSE,
        _pick_non_empty_text(
            payload.get("root_cause"),
            answer_value_from_answers(form_answers, BODY_ROOT_CAUSE),
            answer_value_from_answers(form_answers, QUICK_ROOT_CAUSE_GUESS),
        ),
    )
    set_answer(
        form_answers,
        BODY_FOLLOW_UP,
        _pick_non_empty_text(
            "\n".join(split_lines(payload.get("follow_up_actions"))),
            answer_value_from_answers(form_answers, BODY_FOLLOW_UP),
            answer_value_from_answers(form_answers, QUICK_FOLLOW_UP_ACTION),
        ),
    )

    if timeline:
        first_time = normalize_text(timeline[0].get("time"))
        existing_fault_date = answer_value_from_answers(form_answers, MANUAL_FAULT_DATE)
        if first_time and not normalize_text(existing_fault_date):
            matched = re.match(
                r"^(?P<date>\d{2}/\d{2}/\d{4})\s+(?P<time>\d{2}:\d{2})$", first_time
            )
            if matched:
                set_answer(form_answers, MANUAL_FAULT_DATE, matched.group("date"))
                set_answer(form_answers, MANUAL_FAULT_TIME, matched.group("time"))


def _apply_section_payload(
    *,
    form_answers: dict[str, IncidentFormAnswer],
    section_id: str,
    timeline_index: int | None,
    payload: dict[str, Any],
) -> None:
    section_key = section_id.strip().lower()
    if section_key == "description":
        set_answer_if_non_empty(form_answers, BODY_DESCRIPTION, payload.get("body_description"))
        return
    if section_key == "timeline":
        timeline = normalize_timeline_items(payload.get("body_timeline"))
        if timeline:
            set_answer(form_answers, BODY_TIMELINE, timeline)
        set_answer_if_non_empty(
            form_answers,
            BODY_AFFECTED_DATE,
            payload.get("body_affected_date_summary"),
        )
        return
    if section_key == "impact":
        set_answer_if_non_empty(form_answers, BODY_IMPACT_SCOPE, payload.get("body_impact_scope"))
        set_answer_if_non_empty(
            form_answers,
            BODY_IMPACT_SEVERITY,
            payload.get("body_impact_severity"),
        )
        set_answer_if_non_empty(
            form_answers,
            BODY_BUSINESS_IMPACT,
            payload.get("body_business_impact"),
        )
        return
    if section_key == "root_cause":
        set_answer_if_non_empty(form_answers, BODY_TRIGGER, payload.get("body_trigger"))
        set_answer_if_non_empty(form_answers, BODY_ROOT_CAUSE, payload.get("body_root_cause"))
        return
    if section_key == "follow_up":
        set_answer_if_non_empty(
            form_answers,
            BODY_FOLLOW_UP,
            payload.get("body_follow_up"),
        )
        return
    if section_key == "timeline_item":
        timeline = normalize_timeline_items(answer_value_from_answers(form_answers, BODY_TIMELINE))
        if timeline_index is None or timeline_index < 0 or timeline_index >= len(timeline):
            raise ValueError("Invalid timeline item index.")
        item = payload.get("item")
        if not isinstance(item, dict):
            raise ValueError("Invalid timeline_item format returned by model.")
        normalized_time = compose_datetime_text(normalize_text(item.get("time")))
        if not normalized_time:
            normalized_time = normalize_time_text(normalize_text(item.get("time")))
        timeline[timeline_index] = {
            "time": normalized_time,
            "event": normalize_text(item.get("event")),
            "resolution": normalize_text(item.get("resolution")),
            "evidence": normalize_text(item.get("evidence")),
        }
        set_answer(form_answers, BODY_TIMELINE, timeline)
        return
    raise ValueError("Unsupported section_id.")


async def _run_body_generation_with_trace(
    *,
    report_id: str,
    snapshot: IncidentFormSnapshot,
    model: str,
    reranker_model: str | None,
    section_id: str,
    timeline_index: int | None,
    prompt: str,
    context_json: str,
    apply_payload: Callable[[dict[str, IncidentFormAnswer], dict[str, Any]], None],
) -> IncidentBodyGenerateResponse:
    from uuid import uuid4

    if not settings.ollama_base_url:
        raise RuntimeError("OLLAMA_BASE_URL is not configured.")

    effective_reranker_model = (reranker_model or "").strip() or model
    trace_id = uuid4().hex
    recorder = AgentTraceRecorder(
        trace_id=trace_id,
        tenant_id="default",
        conversation_id=report_id,
        user_message_id=f"incident-body-{section_id}",
        model=model,
        reranker_model=effective_reranker_model,
    )
    recorder.add_event(
        event_type="body_generation_request",
        detail={
            "section_id": section_id,
            "timeline_index": timeline_index,
            "language_policy": "english_fixed",
            "system_skill_id": SYSTEM_DOCUMENT_SKILL_ID,
        },
    )
    await _flush_trace_safely(recorder)

    reference_context = "[fallback]\nReference documentation unavailable, generate from context."
    selected_reference_files: list[str] = []
    reference_selection_reason = "fallback:init"

    try:
        (
            reference_context,
            selected_reference_files,
            reference_selection_reason,
        ) = await resolve_generation_reference_context(
            model=model,
            section_id=section_id,
            timeline_index=timeline_index,
            prompt=prompt,
            context_json=context_json,
        )
        recorder.add_event(
            event_type="body_generation_reference_selection",
            detail={
                "section_id": section_id,
                "selected_reference_files": selected_reference_files,
                "selection_reason": reference_selection_reason,
            },
        )
        await _flush_trace_safely(recorder)

        response_text, done_reason = await _run_plain_chat_completion(
            model=model,
            messages=_build_body_generation_messages(
                prompt=prompt,
                context_json=context_json,
                reference_context=reference_context,
            ),
        )
    except httpx.HTTPError as exc:
        recorder.add_event(
            event_type="body_generation_error",
            detail={
                "ok": False,
                "error": summarize_exception(exc),
            },
        )
        recorder.set_final(done_reason="error", error=summarize_exception(exc))
        await recorder.flush()
        raise RuntimeError(f"Body generation failed: {summarize_exception(exc)}") from exc

    payload = parse_json_object(response_text)
    if payload is None:
        recorder.add_event(
            event_type="body_generation_error",
            detail={
                "ok": False,
                "error": "Model did not return valid JSON.",
                "raw_preview": response_text[:500],
            },
        )
        recorder.set_final(done_reason="error", error="Model did not return valid JSON.")
        await recorder.flush()
        raise RuntimeError("Model did not return valid JSON.")

    form_answers = deepcopy(snapshot.form_answers)
    apply_payload(form_answers, payload)

    next_snapshot = snapshot.model_copy(deep=True)
    next_snapshot.form_answers = form_answers
    next_snapshot.generated_trace_id = trace_id
    section_trace_ids = dict(next_snapshot.section_trace_ids)
    section_key = section_id
    if section_id == "timeline_item" and timeline_index is not None:
        section_key = f"timeline_item_{timeline_index}"
    section_trace_ids[section_key] = trace_id
    next_snapshot.section_trace_ids = section_trace_ids
    next_snapshot.polish_error = None

    form_data_for_db = {
        key: ans.model_dump()
        for key, ans in next_snapshot.form_answers.items()
    }
    await update_report_record(
        report_id,
        form_data=form_data_for_db,
        report_data=next_snapshot.report_data,
    )

    recorder.add_event(
        event_type="body_generation_response",
        detail={
            "ok": True,
            "done_reason": done_reason,
            "response_length": len(response_text),
            "section_id": section_id,
        },
    )
    recorder.set_final(done_reason=done_reason, error=None)
    await recorder.flush()
    return IncidentBodyGenerateResponse(
        report_id=report_id,
        form_answers=form_answers,
        trace_id=trace_id,
        section_id=section_id,
        timeline_index=timeline_index,
    )


def _build_snapshot_from_form_data(form_data: dict[str, Any]) -> IncidentFormSnapshot:
    form_answers: dict[str, IncidentFormAnswer] = {}
    raw_answers = form_data or {}
    for key, raw_value in raw_answers.items():
        if isinstance(raw_value, IncidentFormAnswer):
            form_answers[key] = raw_value
        elif isinstance(raw_value, dict) and ("value" in raw_value or "custom_value" in raw_value):
            form_answers[key] = IncidentFormAnswer(**raw_value)
        else:
            form_answers[key] = IncidentFormAnswer(value=raw_value, custom_value="")
    return IncidentFormSnapshot(form_answers=form_answers)


async def quick_generate_report_body(
    *,
    report_id: str,
    user_id: str | None = None,
    model: str | None = None,
    reranker_model: str | None = None,
) -> IncidentBodyGenerateResponse:
    from .role import has_permission

    record = await load_report_orm(report_id)
    if record is None:
        raise ValueError(f"Report {report_id} does not exist.")
    if user_id:
        can_edit = (
            (record.reporter_id == user_id and await has_permission(user_id, "report:edit_own"))
            or (record.assignee_id == user_id and await has_permission(user_id, "report:edit_assigned"))
            or await has_permission(user_id, "report:edit_all")
        )
        if not can_edit:
            raise PermissionDenied("无权对此报告进行生成操作")
    snapshot = _build_snapshot_from_form_data(record.form_data)
    effective_model = model or "gemma4:e4b"
    prompt, context_json = _build_quick_generation_request(snapshot)
    return await _run_body_generation_with_trace(
        report_id=report_id,
        snapshot=snapshot,
        model=effective_model,
        reranker_model=reranker_model,
        section_id="quick",
        timeline_index=None,
        prompt=prompt,
        context_json=context_json,
        apply_payload=lambda fa, p: _apply_quick_generation_payload(form_answers=fa, payload=p),
    )


async def generate_report_body_section(
    *,
    report_id: str,
    section_id: str,
    timeline_index: int | None = None,
    user_id: str | None = None,
    model: str | None = None,
    reranker_model: str | None = None,
) -> IncidentBodyGenerateResponse:
    from .role import has_permission

    record = await load_report_orm(report_id)
    if record is None:
        raise ValueError(f"Report {report_id} does not exist.")
    if user_id:
        can_edit = (
            (record.reporter_id == user_id and await has_permission(user_id, "report:edit_own"))
            or (record.assignee_id == user_id and await has_permission(user_id, "report:edit_assigned"))
            or await has_permission(user_id, "report:edit_all")
        )
        if not can_edit:
            raise PermissionDenied("无权对此报告进行生成操作")
    snapshot = _build_snapshot_from_form_data(record.form_data)
    effective_model = model or "gemma4:e4b"
    prompt, context_json = _build_section_generation_prompt(
        snapshot,
        section_id=section_id,
        timeline_index=timeline_index,
    )
    return await _run_body_generation_with_trace(
        report_id=report_id,
        snapshot=snapshot,
        model=effective_model,
        reranker_model=reranker_model,
        section_id=section_id,
        timeline_index=timeline_index,
        prompt=prompt,
        context_json=context_json,
        apply_payload=lambda fa, p: _apply_section_payload(
            form_answers=fa,
            section_id=section_id,
            timeline_index=timeline_index,
            payload=p,
        ),
    )
