import re
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from ..models.incident_report import (
    IncidentFormAnswer,
    IncidentReportSessionSnapshot,
)
from .constants import (
    APPENDIX_IMAGES,
    APPENDIX_NOTES,
    BODY_AFFECTED_DATE,
    BODY_BUSINESS_IMPACT,
    BODY_DESCRIPTION,
    BODY_FOLLOW_UP,
    BODY_IMPACT_SCOPE,
    BODY_IMPACT_SEVERITY,
    BODY_ROOT_CAUSE,
    BODY_TIMELINE,
    BODY_TRIGGER,
    MANUAL_ARRIVAL_DATETIME,
    MANUAL_CLEARANCE_DATETIME,
    MANUAL_CLOSEOUT_DATE,
    MANUAL_COMMENTS,
    MANUAL_CONTRACTOR_DATE,
    MANUAL_CONTRACTOR_SIGNATURE,
    MANUAL_CONTRACTOR_STAFF,
    MANUAL_EMPLOYER_REP,
    MANUAL_EMPLOYER_SIGNATURE,
    MANUAL_FAULT_CAUSE,
    MANUAL_FAULT_DATE,
    MANUAL_FAULT_SYMPTOM,
    MANUAL_FAULT_TIME,
    MANUAL_LOCATION,
    MANUAL_MATERIALS_USED,
    MANUAL_REFERENCE_NO,
    MANUAL_REPAIR_DETAILS,
    MANUAL_REPORTING_PERSON,
    MANUAL_SERVICE_PERSON,
    MANUAL_SEVERITY,
    MANUAL_SITE_ID,
    MANUAL_STATUS,
    MANUAL_STATUS_REF_NO,
    MANUAL_SYSTEM,
    MANUAL_VERIFIED_BY,
    QUICK_FOLLOW_UP_ACTION,
    QUICK_IMPACT_SCOPE,
    QUICK_IMPACT_SEVERITY,
    QUICK_NARRATIVE,
    QUICK_ROOT_CAUSE_GUESS,
    QUICK_TIMELINE,
)
from .normalization import (
    compose_datetime_text,
    contains_html_tag,
    extract_appendix_from_rich_text,
    format_date_text,
    format_datetime_text,
    merge_appendix_images,
    normalize_severity_option,
    normalize_status_option,
    normalize_text,
    normalize_timeline_items,
    normalize_time_text,
    parse_date_time,
    safe_json_list,
    severity_option_to_text,
    split_affected_date_summary,
    split_lines,
    status_option_to_text,
)


def answer_value(snapshot: IncidentReportSessionSnapshot, key: str) -> Any:
    answer = snapshot.form_answers.get(key)
    if answer is None:
        return None
    return answer.value


def answer_text(snapshot: IncidentReportSessionSnapshot, key: str) -> str:
    return normalize_text(answer_value(snapshot, key))


def answer_value_from_answers(form_answers: dict[str, IncidentFormAnswer], key: str) -> Any:
    answer = form_answers.get(key)
    if answer is None:
        return None
    return answer.value


def set_answer(
    form_answers: dict[str, IncidentFormAnswer],
    key: str,
    value: Any,
) -> None:
    form_answers[key] = IncidentFormAnswer(value=value, custom_value="")


def set_answer_if_non_empty(
    form_answers: dict[str, IncidentFormAnswer],
    key: str,
    value: Any,
) -> None:
    text = normalize_text(value)
    if text:
        set_answer(form_answers, key, text)


def build_reference_no() -> str:
    return f"DAS-{datetime.now().strftime('%Y%m%d')}-001"


def build_report_data_from_snapshot(
    snapshot: IncidentReportSessionSnapshot,
    *,
    strict_required: bool = True,
) -> tuple[dict[str, Any] | None, list[str]]:
    manual_fault_date = format_date_text(answer_text(snapshot, MANUAL_FAULT_DATE))
    manual_fault_time = normalize_text(answer_value(snapshot, MANUAL_FAULT_TIME))
    manual_reporting_person = answer_text(snapshot, MANUAL_REPORTING_PERSON)
    manual_site_id = answer_text(snapshot, MANUAL_SITE_ID)
    manual_system = answer_text(snapshot, MANUAL_SYSTEM)
    manual_location = answer_text(snapshot, MANUAL_LOCATION)
    manual_fault_symptom = answer_text(snapshot, MANUAL_FAULT_SYMPTOM)

    body_description = answer_text(snapshot, BODY_DESCRIPTION) or answer_text(
        snapshot, QUICK_NARRATIVE
    )
    body_timeline = normalize_timeline_items(answer_value(snapshot, BODY_TIMELINE))
    if not body_timeline:
        body_timeline = normalize_timeline_items(answer_value(snapshot, QUICK_TIMELINE))
    body_impact_scope = answer_text(snapshot, BODY_IMPACT_SCOPE) or answer_text(
        snapshot, QUICK_IMPACT_SCOPE
    )
    body_impact_severity = answer_text(snapshot, BODY_IMPACT_SEVERITY) or answer_text(
        snapshot, QUICK_IMPACT_SEVERITY
    )
    body_root_cause = answer_text(snapshot, BODY_ROOT_CAUSE) or answer_text(
        snapshot, QUICK_ROOT_CAUSE_GUESS
    )
    body_follow_up = answer_text(snapshot, BODY_FOLLOW_UP) or answer_text(
        snapshot, QUICK_FOLLOW_UP_ACTION
    )
    body_trigger = answer_text(snapshot, BODY_TRIGGER)
    body_affected_date = answer_text(snapshot, BODY_AFFECTED_DATE)

    missing_fields: list[str] = []
    required_items = [
        ("手工首页-故障日期", manual_fault_date),
        ("手工首页-故障时间", manual_fault_time),
        ("手工首页-报告人", manual_reporting_person),
        ("手工首页-Site ID", manual_site_id),
        ("手工首页-System", manual_system),
        ("手工首页-故障位置", manual_location),
        ("手工首页-故障现象", manual_fault_symptom),
        ("AI正文-事故简述", body_description),
        ("AI正文-影响范围", body_impact_scope),
        ("AI正文-严重级别", body_impact_severity),
        ("AI正文-根因分析", body_root_cause),
        ("AI正文-后续动作", body_follow_up),
    ]
    for label, value in required_items:
        if not normalize_text(value):
            missing_fields.append(label)
    if not body_timeline:
        missing_fields.append("AI正文-时间线")
    if strict_required and missing_fields:
        return None, missing_fields

    affected_date, affected_from, affected_to = split_affected_date_summary(body_affected_date)
    incident_date = affected_date or format_date_text(manual_fault_date)
    timeline_times = [
        normalize_text(item.get("time"))
        for item in body_timeline
        if normalize_text(item.get("time"))
    ]

    start_time_raw = timeline_times[0] if timeline_times else ""
    if not start_time_raw:
        start_time_raw = affected_from or f"{manual_fault_date} {manual_fault_time}".strip()

    detection_time_raw = (
        timeline_times[1]
        if len(timeline_times) > 1
        else start_time_raw
    )
    if not detection_time_raw:
        detection_time_raw = start_time_raw

    resolution_time_raw = timeline_times[-1] if timeline_times else ""
    if not resolution_time_raw:
        resolution_time_raw = affected_to or detection_time_raw

    start_time = compose_datetime_text(start_time_raw, fallback_date=incident_date) or start_time_raw
    detection_time = (
        compose_datetime_text(detection_time_raw, fallback_date=incident_date)
        or detection_time_raw
        or start_time
    )
    resolution_time = (
        compose_datetime_text(resolution_time_raw, fallback_date=incident_date)
        or resolution_time_raw
        or detection_time
    )

    total_duration = "N/A"
    start_dt = parse_date_time(start_time)
    end_dt = parse_date_time(resolution_time)
    if start_dt is not None and end_dt is not None and end_dt >= start_dt:
        minutes = int((end_dt - start_dt).total_seconds() // 60)
        if minutes < 60:
            total_duration = f"{minutes} minutes"
        else:
            hours = minutes // 60
            remain = minutes % 60
            total_duration = f"{hours}h {remain}m" if remain else f"{hours} hours"

    event_sequence: list[dict[str, str]] = []
    for timeline_item in body_timeline:
        event_text = normalize_text(timeline_item.get("event"))
        resolution_text = normalize_text(timeline_item.get("resolution"))
        if resolution_text:
            event_text = f"{event_text} (Resolution: {resolution_text})".strip()
        event_time = compose_datetime_text(
            normalize_text(timeline_item.get("time")),
            fallback_date=incident_date,
        )
        event_sequence.append(
            {
                "time": event_time or normalize_time_text(normalize_text(timeline_item.get("time"))),
                "event": event_text,
                "evidence": normalize_text(timeline_item.get("evidence")),
            }
        )

    follow_up_lines = split_lines(body_follow_up)
    immediate_actions = []
    if body_timeline:
        for item in body_timeline:
            resolution = normalize_text(item.get("resolution"))
            if not resolution:
                continue
            immediate_actions.append(
                {
                    "action": resolution,
                }
            )
    preventive_actions = [
        {
            "action": line,
        }
        for line in follow_up_lines
    ]

    appendix_raw_value = answer_value(snapshot, APPENDIX_NOTES)
    appendix_notes, rich_text_images = extract_appendix_from_rich_text(
        appendix_raw_value
    )
    if not appendix_notes and not contains_html_tag(appendix_raw_value):
        appendix_notes = normalize_text(appendix_raw_value)
    appendix_images = merge_appendix_images(
        rich_text_images,
        safe_json_list(answer_value(snapshot, APPENDIX_IMAGES)),
    )

    status_option = normalize_status_option(answer_text(snapshot, MANUAL_STATUS))
    status_ref_no = answer_text(snapshot, MANUAL_STATUS_REF_NO)
    severity_raw = answer_text(snapshot, MANUAL_SEVERITY) or body_impact_severity
    severity_option = normalize_severity_option(severity_raw)

    report_data = {
        "reference_no": answer_text(snapshot, MANUAL_REFERENCE_NO) or build_reference_no(),
        "fault_date": manual_fault_date,
        "fault_time": manual_fault_time,
        "reporting_person": manual_reporting_person,
        "verified_by": answer_text(snapshot, MANUAL_VERIFIED_BY) or "N/A",
        "site_id": manual_site_id,
        "system": manual_system,
        "location": manual_location,
        "fault_details": manual_fault_symptom,
        "arrival_datetime": format_datetime_text(answer_text(snapshot, MANUAL_ARRIVAL_DATETIME))
        or start_time,
        "clearance_datetime": format_datetime_text(
            answer_text(snapshot, MANUAL_CLEARANCE_DATETIME)
        )
        or resolution_time,
        "service_person": answer_text(snapshot, MANUAL_SERVICE_PERSON),
        "fault_cause": answer_text(snapshot, MANUAL_FAULT_CAUSE),
        "materials_used": answer_text(snapshot, MANUAL_MATERIALS_USED),
        "repair_details": answer_text(snapshot, MANUAL_REPAIR_DETAILS),
        "contractor_staff": answer_text(snapshot, MANUAL_CONTRACTOR_STAFF),
        "contractor_signature": answer_text(snapshot, MANUAL_CONTRACTOR_SIGNATURE),
        "contractor_date": format_date_text(answer_text(snapshot, MANUAL_CONTRACTOR_DATE))
        or manual_fault_date,
        "status_option": status_option,
        "status_ref_no": status_ref_no,
        "status": status_option_to_text(status_option),
        "severity_option": severity_option,
        "severity": severity_option_to_text(severity_option) or body_impact_severity,
        "comments": answer_text(snapshot, MANUAL_COMMENTS),
        "employer_rep": answer_text(snapshot, MANUAL_EMPLOYER_REP),
        "employer_signature": answer_text(snapshot, MANUAL_EMPLOYER_SIGNATURE),
        "closeout_date": format_date_text(answer_text(snapshot, MANUAL_CLOSEOUT_DATE))
        or manual_fault_date,
        "detailed_description": body_description,
        "affected_date_summary": body_affected_date
        or f"{start_time} - {resolution_time}",
        "start_time": start_time,
        "detection_time": detection_time,
        "resolution_time": resolution_time,
        "total_duration": total_duration,
        "event_sequence": event_sequence,
        "impact": {
            "systems": body_impact_scope,
            "users": "",
            "region": manual_site_id,
            "severity": body_impact_severity,
            "business_impact": split_lines(
                answer_value(snapshot, BODY_BUSINESS_IMPACT)
            ),
        },
        "trigger": body_trigger or body_root_cause,
        "root_cause": body_root_cause,
        "root_cause_evidence": "",
        "immediate_actions": immediate_actions,
        "preventive_actions": preventive_actions,
        "appendix": {
            "notes": appendix_notes,
            "images": appendix_images,
        },
        "report_body": {
            "description": body_description,
            "affected_date_summary": body_affected_date or f"{start_time} - {resolution_time}",
            "timeline": body_timeline,
            "impact_scope": body_impact_scope,
            "impact_severity": body_impact_severity,
            "root_cause": body_root_cause,
            "follow_up_actions": follow_up_lines,
            "business_impact": split_lines(answer_value(snapshot, BODY_BUSINESS_IMPACT)),
            "trigger": body_trigger or body_root_cause,
        },
    }
    return report_data, []
