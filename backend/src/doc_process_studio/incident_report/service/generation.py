import json
import re
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable

import httpx

from ..models.incident_report import (
    IncidentFormAnswer,
    IncidentReportSessionSummary,
)
from ..schemas.response import (
    IncidentBodyGenerateResponse,
    IncidentReportSessionDetail,
)
from ...system.service.error_detail import summarize_exception
from ...system.service.trace_store import AgentTraceRecorder
from ...shared.dtutils import utcnow
from ...shared.text_utils import parse_json_object
from ...core.config import settings
from ...core.language_policy import (
    LANGUAGE_ZH,
    describe_language,
    detect_language_with_model,
    verify_text_language_with_model,
)
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
from .session_store import (
    save_incident_session_snapshot,
    save_incident_session_summary,
    touch_incident_session_index,
)


def _build_default_title(now: Any = None) -> str:
    current = now or utcnow()
    return f"事故报告-{current.strftime('%Y/%m/%d %H:%M')}"


def _build_summary_from_detail(
    detail: IncidentReportSessionDetail,
    *,
    status: str | None = None,
    title: str | None = None,
    updated_at: Any = None,
) -> IncidentReportSessionSummary:
    payload = detail.model_dump(exclude={"snapshot"})
    if status is not None:
        payload["status"] = status
    if title is not None:
        payload["title"] = title
    if updated_at is not None:
        payload["updated_at"] = updated_at
    return IncidentReportSessionSummary.model_validate(payload)


def _resolve_document_assistant_prompt() -> str:
    from ...skill.service.registry import get_skill_interface
    try:
        return normalize_text(get_skill_interface(SYSTEM_DOCUMENT_SKILL_ID).default_prompt)
    except Exception:
        return ""


def _build_language_policy_instruction() -> str:
    return (
        "请你自行判断当前用户在本次上下文里主要使用的语言，并使用同一种语言输出正文字段。"
        "如果用户主要使用英文，就输出英文；如果主要使用中文，就输出中文；"
        "若出现中英文混合，以用户最近一轮明确输入的主语言为准。"
    )


def _build_language_detection_context(
    *,
    section_id: str,
    timeline_index: int | None,
    prompt: str,
    context_json: str,
) -> str:
    return json.dumps(
        {
            "workspace": "incident-report",
            "section_id": section_id,
            "timeline_index": timeline_index,
            "prompt": prompt,
            "context": parse_json_object(context_json) or context_json,
        },
        ensure_ascii=False,
    )


def _build_enforced_language_instruction(language: str) -> str:
    normalized = language.strip().lower()
    if normalized == "en":
        return f"本次输出语言已确定为{describe_language(normalized)}，所有正文内容必须使用该语言。"
    return f"本次输出语言已确定为{describe_language(LANGUAGE_ZH)}，所有正文内容必须使用该语言。"


async def _detect_generation_language_with_model(
    *,
    model: str,
    section_id: str,
    timeline_index: int | None,
    prompt: str,
    context_json: str,
) -> tuple[str | None, str]:
    detection_context = _build_language_detection_context(
        section_id=section_id,
        timeline_index=timeline_index,
        prompt=prompt,
        context_json=context_json,
    )
    language, reason = await detect_language_with_model(
        model=model,
        context_text=detection_context,
        task_name="incident-report-body-generation",
    )
    return language, reason


async def _verify_generation_language_with_model(
    *,
    model: str,
    expected_language: str,
    generated_text: str,
    section_id: str,
) -> tuple[bool | None, str | None, str]:
    return await verify_text_language_with_model(
        model=model,
        expected_language=expected_language,
        text=generated_text,
        task_name=f"incident-report-{section_id}",
    )


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
        return


def _build_quick_generation_context(
    snapshot: Any,
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
    snapshot: Any,
) -> tuple[str, str]:
    prompt = (
        "你将执行「快填模式 -> 完整模式」生成。"
        "请根据参考文档规范，把快填输入扩展为完整模式字段。"
        "禁止编造上下文不存在的事实；若信息不足可使用保守但可执行的表达。"
        "只输出 JSON，不要输出解释。"
        "JSON 键必须是：description, affected_date_summary, timeline, impact_scope, impact_severity, "
        "business_impact, trigger, root_cause, follow_up_actions。"
        "timeline 是数组，每项必须包含 time,event,resolution,evidence。"
    )
    return prompt, json.dumps(_build_quick_generation_context(snapshot), ensure_ascii=False)


def _build_section_generation_prompt(
    snapshot: Any,
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
            "仅生成事故简述段。只输出 JSON：{\"body_description\":\"...\"}。不要修改其它章节。",
            json.dumps(body_context, ensure_ascii=False),
        )
    if section_key == "timeline":
        return (
            "仅生成时间线段。只输出 JSON：{\"body_timeline\":[{\"time\":\"\",\"event\":\"\",\"resolution\":\"\",\"evidence\":\"\"}],"
            "\"body_affected_date_summary\":\"...\"}。不要修改其它章节。",
            json.dumps(body_context, ensure_ascii=False),
        )
    if section_key == "impact":
        return (
            "仅生成影响范围/严重级别/业务影响。只输出 JSON：{\"body_impact_scope\":\"...\","
            "\"body_impact_severity\":\"...\",\"body_business_impact\":\"按换行分隔\"}。不要修改其它章节。",
            json.dumps(body_context, ensure_ascii=False),
        )
    if section_key == "root_cause":
        return (
            "仅生成触发原因与根因。只输出 JSON：{\"body_trigger\":\"...\",\"body_root_cause\":\"...\"}。不要修改其它章节。",
            json.dumps(body_context, ensure_ascii=False),
        )
    if section_key == "follow_up":
        return (
            "仅生成后续动作段。只输出 JSON：{\"body_follow_up_actions\":\"按换行分隔\"}。不要修改其它章节。",
            json.dumps(body_context, ensure_ascii=False),
        )
    if section_key == "timeline_item":
        timeline = body_context["timeline"]
        if timeline_index is None or timeline_index < 0 or timeline_index >= len(timeline):
            raise ValueError("无效的时间线条目索引。")
        return (
            "仅生成指定时间线条目。只输出 JSON：{\"item\":{\"time\":\"\",\"event\":\"\",\"resolution\":\"\",\"evidence\":\"\"}}。"
            "禁止改写其它时间线条目。",
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
    raise ValueError("不支持的 section_id。")


def _build_body_generation_messages(
    *,
    prompt: str,
    context_json: str,
    reference_context: str,
    enforced_language: str | None,
    strict_retry: bool = False,
) -> list[dict[str, Any]]:
    language_policy = _build_language_policy_instruction()
    enforcement_instruction = (
        _build_enforced_language_instruction(enforced_language)
        if enforced_language
        else language_policy
    )
    retry_instruction = (
        "注意：上一次输出语言不符合要求。本次必须严格遵守语言要求，否则视为失败。"
        if strict_retry
        else ""
    )
    document_assistant_prompt = _resolve_document_assistant_prompt()
    system_prompt_prefix = (
        f"系统级技能提示（{SYSTEM_DOCUMENT_SKILL_ID}）：{document_assistant_prompt}\n"
        if document_assistant_prompt
        else ""
    )
    return [
        {
            "role": "system",
            "content": (
                f"{system_prompt_prefix}"
                "你是事故报告正文助手。"
                "先遵循参考文档，再结合当前上下文生成内容。"
                "只输出 JSON，不要输出代码块，不要编造事实。"
                f"{enforcement_instruction}"
                f"{retry_instruction}"
            ),
        },
        {
            "role": "user",
            "content": (
                f"{prompt}\n"
                f"语言策略：{enforcement_instruction}\n"
                f"{retry_instruction}\n"
                f"参考文档：\n{reference_context}\n"
                f"当前上下文：{context_json}"
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
            payload.get("body_follow_up_actions"),
        )
        return
    if section_key == "timeline_item":
        timeline = normalize_timeline_items(answer_value_from_answers(form_answers, BODY_TIMELINE))
        if timeline_index is None or timeline_index < 0 or timeline_index >= len(timeline):
            raise ValueError("无效的时间线条目索引。")
        item = payload.get("item")
        if not isinstance(item, dict):
            raise ValueError("模型返回的 timeline_item 格式不正确。")
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
    raise ValueError("不支持的 section_id。")


async def _run_body_generation_with_trace(
    *,
    detail: IncidentReportSessionDetail,
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
        raise RuntimeError("未配置 OLLAMA_BASE_URL。")

    effective_reranker_model = (reranker_model or "").strip() or model
    detected_language, language_detection_reason = await _detect_generation_language_with_model(
        model=model,
        section_id=section_id,
        timeline_index=timeline_index,
        prompt=prompt,
        context_json=context_json,
    )
    trace_id = uuid4().hex
    recorder = AgentTraceRecorder(
        trace_id=trace_id,
        tenant_id="default",
        conversation_id=detail.id,
        user_message_id=f"incident-body-{section_id}",
        model=model,
        reranker_model=effective_reranker_model,
    )
    recorder.add_event(
        event_type="body_generation_request",
        detail={
            "section_id": section_id,
            "timeline_index": timeline_index,
            "language_policy": "model_detect_then_enforce",
            "system_skill_id": SYSTEM_DOCUMENT_SKILL_ID,
            "detected_language": detected_language,
            "language_detection_reason": language_detection_reason,
        },
    )
    await _flush_trace_safely(recorder)
    recorder.add_event(
        event_type="body_generation_language_detection",
        detail={
            "section_id": section_id,
            "detected_language": detected_language,
            "reason": language_detection_reason,
        },
    )
    await _flush_trace_safely(recorder)

    reference_context = "[fallback]\n参考文档不可用，按上下文生成。"
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
                enforced_language=detected_language,
            ),
        )

        verification_match: bool | None = None
        detected_output_language: str | None = None
        verification_reason = "verification_skipped_no_detected_language"
        if detected_language:
            (
                verification_match,
                detected_output_language,
                verification_reason,
            ) = await _verify_generation_language_with_model(
                model=model,
                expected_language=detected_language,
                generated_text=response_text,
                section_id=section_id,
            )
            recorder.add_event(
                event_type="body_generation_language_verification",
                detail={
                    "section_id": section_id,
                    "attempt": 1,
                    "expected_language": detected_language,
                    "detected_output_language": detected_output_language,
                    "match": verification_match,
                    "reason": verification_reason,
                },
            )
            await _flush_trace_safely(recorder)

            if verification_match is False:
                recorder.add_event(
                    event_type="body_generation_language_retry",
                    detail={
                        "section_id": section_id,
                        "expected_language": detected_language,
                        "reason": verification_reason,
                    },
                )
                await _flush_trace_safely(recorder)
                response_text, done_reason = await _run_plain_chat_completion(
                    model=model,
                    messages=_build_body_generation_messages(
                        prompt=prompt,
                        context_json=context_json,
                        reference_context=reference_context,
                        enforced_language=detected_language,
                        strict_retry=True,
                    ),
                )
                (
                    verification_match,
                    detected_output_language,
                    verification_reason,
                ) = await _verify_generation_language_with_model(
                    model=model,
                    expected_language=detected_language,
                    generated_text=response_text,
                    section_id=section_id,
                )
                recorder.add_event(
                    event_type="body_generation_language_verification",
                    detail={
                        "section_id": section_id,
                        "attempt": 2,
                        "expected_language": detected_language,
                        "detected_output_language": detected_output_language,
                        "match": verification_match,
                        "reason": verification_reason,
                    },
                )
                await _flush_trace_safely(recorder)
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
        raise RuntimeError(f"正文生成失败：{summarize_exception(exc)}") from exc

    payload = parse_json_object(response_text)
    if payload is None:
        recorder.add_event(
            event_type="body_generation_error",
            detail={
                "ok": False,
                "error": "模型未返回合法 JSON。",
                "raw_preview": response_text[:500],
            },
        )
        recorder.set_final(done_reason="error", error="模型未返回合法 JSON。")
        await recorder.flush()
        raise RuntimeError("模型未返回合法 JSON。")

    form_answers = deepcopy(detail.snapshot.form_answers)
    apply_payload(form_answers, payload)

    now = utcnow()
    next_summary = _build_summary_from_detail(
        detail,
        status="draft",
        updated_at=now,
    )
    next_snapshot = detail.snapshot.model_copy(deep=True)
    next_snapshot.form_answers = form_answers
    next_snapshot.generated_trace_id = trace_id
    section_trace_ids = dict(next_snapshot.section_trace_ids)
    section_key = section_id
    if section_id == "timeline_item" and timeline_index is not None:
        section_key = f"timeline_item_{timeline_index}"
    section_trace_ids[section_key] = trace_id
    next_snapshot.section_trace_ids = section_trace_ids
    next_snapshot.polish_error = None

    await save_incident_session_summary(next_summary)
    await save_incident_session_snapshot(detail.id, next_snapshot)
    await touch_incident_session_index(detail.id, now.timestamp())

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
        session=next_summary,
        snapshot=next_snapshot,
        trace_id=trace_id,
        section_id=section_id,
        timeline_index=timeline_index,
    )
