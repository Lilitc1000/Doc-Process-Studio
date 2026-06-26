"""报告正文生成 — 纯技术函数。

本模块仅包含无状态、纯函数式的技术工具，不包含任何业务逻辑（如权限检查、
报告加载、持久化、跨域调用等）。业务逻辑由 application/generation_service.py 编排。

公共函数命名约定：
  _build_*  → 构建提示词 / 上下文 / 消息列表
  _apply_*  → 将 LLM 返回的 payload 回填到 form_answers
"""

import json
import logging
import re
from typing import Any

from ...application.dtos import (
    IncidentFormAnswer,
    IncidentFormSnapshot,
)
from ...domain.values.constants import (
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
    normalize_time_text,
    normalize_timeline_items,
    split_lines,
)
from .report_data import answer_text, answer_value, answer_value_from_answers, set_answer, set_answer_if_non_empty

logger = logging.getLogger(__name__)


def _build_snapshot_from_form_data(form_data: dict[str, Any]) -> IncidentFormSnapshot:
    """从数据库 form_data 构建领域快照。纯数据转换，无业务逻辑。"""
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


def _build_quick_generation_context(
    snapshot: IncidentFormSnapshot,
) -> dict[str, Any]:
    """构建快填 → 全填的上下文 JSON 结构。纯数据组装，无业务逻辑。"""
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
    """构建快填生成的提示词和上下文。纯文本组装，无业务逻辑。"""
    prompt = (
        "You will perform a quick-fill to full-mode generation. "
        "Expand the quick-fill inputs into complete mode fields according to the reference documentation. "
        "Do not fabricate facts not present in the context; "
        "use conservative but actionable expressions when information is insufficient. "
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
    """构建分段生成的提示词和上下文。纯文本组装，无业务逻辑。"""
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
            "Generate the incident description section only. "
            'Output JSON: {"body_description":"..."}. Do not modify other sections.',
            json.dumps(body_context, ensure_ascii=False),
        )
    if section_key == "timeline":
        return (
            "Generate the timeline section only. "
            'Output JSON: {"body_timeline":[{"time":"","event":"","resolution":"","evidence":""}],'
            '"body_affected_date_summary":"..."}. Do not modify other sections.',
            json.dumps(body_context, ensure_ascii=False),
        )
    if section_key == "impact":
        return (
            "Generate impact scope, severity, and business impact only. "
            'Output JSON: {"body_impact_scope":"...",'
            '"body_impact_severity":"...","body_business_impact":"separated by newlines"}. '
            "Do not modify other sections.",
            json.dumps(body_context, ensure_ascii=False),
        )
    if section_key == "root_cause":
        return (
            "Generate trigger and root cause only. "
            'Output JSON: {"body_trigger":"...","body_root_cause":"..."}. '
            "Do not modify other sections.",
            json.dumps(body_context, ensure_ascii=False),
        )
    if section_key == "follow_up":
        return (
            "Generate follow-up actions only. "
            'Output JSON: {"body_follow_up":"separated by newlines"}. Do not modify other sections.',
            json.dumps(body_context, ensure_ascii=False),
        )
    if section_key == "timeline_item":
        timeline = body_context["timeline"]
        if timeline_index is None or timeline_index < 0 or timeline_index >= len(timeline):
            raise ValueError("Invalid timeline item index.")
        return (
            "Generate the specified timeline item only. "
            'Output JSON: {"item":{"time":"","event":"","resolution":"","evidence":""}}. '
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
    document_assistant_prompt: str = "",
) -> list[dict[str, Any]]:
    """构建 LLM 调用的消息列表。纯数据组装，无业务逻辑。"""
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
            "content": (f"{prompt}\nReference documentation:\n{reference_context}\nCurrent context:\n{context_json}"),
        },
    ]


def _apply_quick_generation_payload(
    *,
    form_answers: dict[str, IncidentFormAnswer],
    payload: dict[str, Any],
) -> None:
    """将快填 LLM 返回的 payload 回填到 form_answers。纯数据操作，无业务逻辑。"""

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
        timeline = normalize_timeline_items(answer_value_from_answers(form_answers, BODY_TIMELINE))
    if not timeline:
        timeline = normalize_timeline_items(answer_value_from_answers(form_answers, QUICK_TIMELINE))
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
            matched = re.match(r"^(?P<date>\d{2}/\d{2}/\d{4})\s+(?P<time>\d{2}:\d{2})$", first_time)
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
    """将分段 LLM 返回的 payload 回填到 form_answers。纯数据操作，无业务逻辑。"""
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
