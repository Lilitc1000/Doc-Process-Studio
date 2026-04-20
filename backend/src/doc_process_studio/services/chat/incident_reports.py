import asyncio
import json
import io
import importlib.util
import base64
import hashlib
import re
import shutil
import subprocess
import tempfile
from collections import OrderedDict
from copy import deepcopy
from datetime import UTC, datetime
from html import unescape
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx

try:  # pragma: no cover - 依赖由运行环境保证
    import mammoth
except ImportError:  # pragma: no cover - 便于在缺依赖时给出明确报错
    mammoth = None

try:  # pragma: no cover - 依赖由运行环境保证
    from deep_translator import GoogleTranslator
except ImportError:  # pragma: no cover - 便于在缺依赖时给出明确报错
    GoogleTranslator = None

from ...models.conversation.incident_report import (
    IncidentBodyGenerateResponse,
    IncidentFormAnswer,
    IncidentGeneratedVersion,
    IncidentReportFormSchemaResponse,
    IncidentReportPreviewResponse,
    IncidentReportSessionDetail,
    IncidentReportSessionListResponse,
    IncidentReportSessionSnapshot,
    IncidentReportSessionSummary,
    build_empty_incident_snapshot,
)
from ...services.agent.error_detail import summarize_exception
from ...services.agent.trace_store import (
    AgentTraceRecorder,
    delete_agent_traces_for_conversation,
)
from ...services.infra.dtutils import utcnow
from ...services.infra.text_utils import parse_json_object
from ...settings import settings
from ..infra.ollama_client import stream_chat_completion
from ..skill.conversation_store import clear_conversation_state
from .attachments import (
    delete_attachments_for_conversation,
    resolve_attachment_path,
    save_generated_attachment,
)
from .incident_session_store import (
    delete_incident_session_records,
    list_incident_session_ids,
    load_incident_session_snapshot,
    load_incident_session_summary,
    save_incident_session_snapshot,
    save_incident_session_summary,
    touch_incident_session_index,
)
from .streaming import extract_delta_text, extract_done_reason

INCIDENT_REPORT_SKILL_ID = "incident-report"
INCIDENT_REPORT_DOCX_MIME_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)
INCIDENT_REPORT_SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "skills"
    / "incident-report"
    / "scripts"
    / "generate_incident_report.py"
)

# 手工首页字段
MANUAL_REFERENCE_NO = "manual_reference_no"
MANUAL_FAULT_DATE = "manual_fault_date"
MANUAL_FAULT_TIME = "manual_fault_time"
MANUAL_REPORTING_PERSON = "manual_reporting_person"
MANUAL_VERIFIED_BY = "manual_verified_by"
MANUAL_SITE_ID = "manual_site_id"
MANUAL_SYSTEM = "manual_system"
MANUAL_LOCATION = "manual_location"
MANUAL_FAULT_SYMPTOM = "manual_fault_symptom"
MANUAL_ARRIVAL_DATETIME = "manual_arrival_datetime"
MANUAL_CLEARANCE_DATETIME = "manual_clearance_datetime"
MANUAL_SERVICE_PERSON = "manual_service_person"
MANUAL_FAULT_CAUSE = "manual_fault_cause"
MANUAL_MATERIALS_USED = "manual_materials_used"
MANUAL_REPAIR_DETAILS = "manual_repair_details"
MANUAL_CONTRACTOR_STAFF = "manual_contractor_staff"
MANUAL_CONTRACTOR_DATE = "manual_contractor_date"
MANUAL_STATUS = "manual_status"
MANUAL_SEVERITY = "manual_severity"
MANUAL_COMMENTS = "manual_comments"
MANUAL_EMPLOYER_REP = "manual_employer_rep"
MANUAL_CLOSEOUT_DATE = "manual_closeout_date"

# 快填字段
QUICK_NARRATIVE = "quick_narrative"
QUICK_TIMELINE = "quick_timeline"
QUICK_IMPACT_SCOPE = "quick_impact_scope"
QUICK_IMPACT_SEVERITY = "quick_impact_severity"
QUICK_ROOT_CAUSE_GUESS = "quick_root_cause_guess"
QUICK_FOLLOW_UP_ACTION = "quick_follow_up_action"

# 正文字段（完整模式）
BODY_DESCRIPTION = "body_description"
BODY_AFFECTED_DATE = "body_affected_date_summary"
BODY_TIMELINE = "body_timeline"
BODY_IMPACT_SCOPE = "body_impact_scope"
BODY_IMPACT_SEVERITY = "body_impact_severity"
BODY_BUSINESS_IMPACT = "body_business_impact"
BODY_TRIGGER = "body_trigger"
BODY_ROOT_CAUSE = "body_root_cause"
BODY_FOLLOW_UP = "body_follow_up_actions"

# 附录字段
APPENDIX_NOTES = "appendix_notes"
APPENDIX_IMAGES = "appendix_images"

INCIDENT_REPORT_SCHEMA_INTRO = (
    "欢迎使用事故报告专区。支持快填生成正文、完整分段润色、附录富文本编辑与多版本附件历史。"
)


def _is_docx_attachment(attachment: Any) -> bool:
    attachment_name = str(getattr(attachment, "name", "")).strip().lower()
    attachment_mime = str(getattr(attachment, "mime_type", "")).strip().lower()
    return attachment_name.endswith(".docx") and (
        attachment_mime == INCIDENT_REPORT_DOCX_MIME_TYPE
    )


def _build_default_title(now: datetime | None = None) -> str:
    current = now or utcnow()
    return f"事故报告-{current.strftime('%Y/%m/%d %H:%M')}"


def _build_summary_from_detail(
    detail: IncidentReportSessionDetail,
    *,
    status: str | None = None,
    title: str | None = None,
    updated_at: datetime | None = None,
) -> IncidentReportSessionSummary:
    payload = detail.model_dump(exclude={"snapshot"})
    if status is not None:
        payload["status"] = status
    if title is not None:
        payload["title"] = title
    if updated_at is not None:
        payload["updated_at"] = updated_at
    return IncidentReportSessionSummary.model_validate(payload)


def _normalize_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if value is None:
        return ""
    return str(value).strip()


def _split_lines(value: Any) -> list[str]:
    if isinstance(value, list):
        rows = []
        for item in value:
            text = _normalize_text(item)
            if text:
                rows.append(text)
        return rows
    text = _normalize_text(value)
    if not text:
        return []
    if "\n" in text:
        rows = [line.strip("- ").strip() for line in text.splitlines()]
        return [row for row in rows if row]
    if ";" in text:
        rows = [line.strip() for line in text.split(";")]
        return [row for row in rows if row]
    return [text]


def _parse_date_time(value: str) -> datetime | None:
    normalized = _normalize_text(value)
    if not normalized:
        return None
    patterns = (
        "%d/%m/%Y %H:%M",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M",
        "%Y/%m/%d %H:%M",
    )
    for pattern in patterns:
        try:
            return datetime.strptime(normalized, pattern).replace(tzinfo=UTC)
        except ValueError:
            continue
    return None


def _format_datetime_text(value: str) -> str:
    normalized = _normalize_text(value)
    if not normalized:
        return ""
    iso_matched = re.match(
        r"^(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})[T\s](?P<hour>\d{1,2}):(?P<minute>\d{1,2})",
        normalized,
    )
    if iso_matched:
        year = iso_matched.group("year")
        month = str(int(iso_matched.group("month"))).zfill(2)
        day = str(int(iso_matched.group("day"))).zfill(2)
        hour = str(int(iso_matched.group("hour"))).zfill(2)
        minute = str(int(iso_matched.group("minute"))).zfill(2)
        return f"{day}/{month}/{year} {hour}:{minute}"
    return normalized


def _format_date_text(value: str) -> str:
    normalized = _normalize_text(value)
    if not normalized:
        return ""
    for pattern in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y", "%Y.%m.%d"):
        try:
            parsed = datetime.strptime(normalized, pattern)
            return parsed.strftime("%d/%m/%Y")
        except ValueError:
            continue
    matched = re.match(r"^(?P<day>\d{1,2})[./-](?P<month>\d{1,2})[./-](?P<year>\d{4})$", normalized)
    if matched:
        day = str(int(matched.group("day"))).zfill(2)
        month = str(int(matched.group("month"))).zfill(2)
        year = matched.group("year")
        return f"{day}/{month}/{year}"
    iso_matched = re.match(r"^(?P<year>\d{4})[./-](?P<month>\d{1,2})[./-](?P<day>\d{1,2})$", normalized)
    if iso_matched:
        day = str(int(iso_matched.group("day"))).zfill(2)
        month = str(int(iso_matched.group("month"))).zfill(2)
        year = iso_matched.group("year")
        return f"{day}/{month}/{year}"
    return normalized


def _normalize_time_text(value: str) -> str:
    normalized = _normalize_text(value)
    if not normalized:
        return ""

    def _apply_ampm(hour_value: int, ampm_value: str) -> int:
        ampm = ampm_value.lower()
        hour = hour_value
        if ampm == "pm" and 1 <= hour <= 11:
            hour += 12
        elif ampm == "am" and hour == 12:
            hour = 0
        return hour

    matched = re.search(
        r"(?P<hour>\d{1,2})\s*(?:[:：时hH点])\s*(?P<minute>\d{1,2})(?:\s*(?:分|m|M))?\s*(?P<ampm>am|pm)?",
        normalized,
        flags=re.IGNORECASE,
    )
    if matched:
        hour = int(matched.group("hour"))
        minute = int(matched.group("minute"))
        hour = _apply_ampm(hour, matched.group("ampm") or "")
        if minute < 0 or minute > 59:
            return ""
        if hour < 0 or hour > 23:
            return ""
        return f"{hour:02d}:{minute:02d}"

    half_matched = re.search(
        r"(?<!\d)(?P<hour>\d{1,2})\s*(?:点|时|h|H)\s*半\s*(?P<ampm>am|pm)?(?!\d)",
        normalized,
        flags=re.IGNORECASE,
    )
    if half_matched:
        hour = _apply_ampm(int(half_matched.group("hour")), half_matched.group("ampm") or "")
        if 0 <= hour <= 23:
            return f"{hour:02d}:30"
        return ""

    hour_only_matched = re.search(
        r"(?<!\d)(?P<hour>\d{1,2})\s*(?:点|时|h|H)\s*(?P<ampm>am|pm)?(?!\d)",
        normalized,
        flags=re.IGNORECASE,
    )
    if hour_only_matched:
        hour = _apply_ampm(int(hour_only_matched.group("hour")), hour_only_matched.group("ampm") or "")
        if 0 <= hour <= 23:
            return f"{hour:02d}:00"
    return ""


def _extract_date_text(value: str) -> str:
    normalized = _normalize_text(value)
    if not normalized:
        return ""
    matched = re.search(r"(?P<year>\d{4})[./-](?P<month>\d{1,2})[./-](?P<day>\d{1,2})", normalized)
    if matched:
        return f"{int(matched.group('day')):02d}/{int(matched.group('month')):02d}/{matched.group('year')}"
    matched = re.search(r"(?P<day>\d{1,2})[./-](?P<month>\d{1,2})[./-](?P<year>\d{4})", normalized)
    if matched:
        return f"{int(matched.group('day')):02d}/{int(matched.group('month')):02d}/{matched.group('year')}"
    formatted = _format_date_text(normalized)
    if re.match(r"^\d{2}/\d{2}/\d{4}$", formatted):
        return formatted
    return ""


def _compose_datetime_text(value: str, *, fallback_date: str | None = None) -> str:
    normalized = _normalize_text(value)
    if not normalized:
        return ""
    formatted = _format_datetime_text(normalized)
    if re.match(r"^\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}$", formatted):
        return formatted
    date_text = _extract_date_text(normalized)
    time_text = _normalize_time_text(normalized)
    if date_text and time_text:
        return f"{date_text} {time_text}"
    if time_text and fallback_date:
        normalized_date = _format_date_text(fallback_date)
        if normalized_date:
            return f"{normalized_date} {time_text}"
    if date_text:
        return date_text
    return time_text or normalized


def _split_affected_date_summary(value: str) -> tuple[str, str, str]:
    normalized = _normalize_text(value)
    if not normalized:
        return "", "", ""
    date_text = _extract_date_text(normalized)
    time_matches = list(
        re.finditer(
            r"(?<!\d)(?P<time>\d{1,2}\s*(?:[:：]\s*\d{1,2}(?:\s*(?:分|m|M))?|(?:点|时|h|H)\s*(?:\d{1,2}\s*(?:分)?|半)?)(?:\s*(?:am|pm))?)(?!\d)",
            normalized,
            flags=re.IGNORECASE,
        )
    )
    times = [_normalize_time_text(match.group("time")) for match in time_matches]
    times = [item for item in times if item]
    if len(times) >= 2:
        return date_text, times[0], times[1]
    if len(times) == 1:
        return date_text, times[0], times[0]
    return date_text, "", ""


def _build_reference_no() -> str:
    return f"DAS-{datetime.now().strftime('%Y%m%d')}-001"


def _safe_json_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        parsed = parse_json_object(value)
        if isinstance(parsed, dict):
            items = parsed.get("items")
            if isinstance(items, list):
                return items
        try:
            loaded = json.loads(value)
        except json.JSONDecodeError:
            return []
        return loaded if isinstance(loaded, list) else []
    return []


def _extract_appendix_from_rich_text(value: Any) -> tuple[str, list[dict[str, str]]]:
    raw = _normalize_text(value)
    if not raw:
        return "", []
    if "<" not in raw or ">" not in raw:
        return raw, []

    images: list[dict[str, str]] = []
    for index, match in enumerate(
        re.finditer(r"<img[^>]*src=['\"](?P<src>[^'\"]+)['\"][^>]*>", raw, flags=re.IGNORECASE)
    ):
        data_url = _normalize_text(match.group("src"))
        if not data_url.startswith("data:image"):
            continue
        alt_match = re.search(
            r"alt=['\"](?P<alt>[^'\"]*)['\"]",
            match.group(0),
            flags=re.IGNORECASE,
        )
        image_name = (
            _normalize_text(alt_match.group("alt")) if alt_match is not None else ""
        ) or f"appendix-image-{index + 1}.png"
        images.append(
            {
                "name": image_name,
                "data_url": data_url,
            }
        )

    text_value = re.sub(r"(?i)<img[^>]*>", "", raw)
    text_value = re.sub(r"(?i)<br\s*/?>", "\n", text_value)
    text_value = re.sub(r"(?i)</p\s*>", "\n", text_value)
    text_value = re.sub(r"(?i)</div\s*>", "\n", text_value)
    text_value = re.sub(r"<[^>]+>", "", text_value)
    text_value = re.sub(r"data:image/[^;]+;base64,[A-Za-z0-9+/=]+", "", text_value)
    normalized_lines = [
        unescape(line).strip()
        for line in text_value.splitlines()
        if unescape(line).strip()
    ]
    return "\n".join(normalized_lines), images


def _merge_appendix_images(*image_groups: list[Any]) -> list[dict[str, str]]:
    merged: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    for images in image_groups:
        for item in images:
            if not isinstance(item, dict):
                continue
            data_url = _normalize_text(item.get("data_url"))
            if not data_url or not data_url.startswith("data:image"):
                continue
            if data_url in seen_urls:
                continue
            seen_urls.add(data_url)
            name = _normalize_text(item.get("name")) or f"appendix-image-{len(merged) + 1}.png"
            merged.append(
                {
                    "name": name,
                    "data_url": data_url,
                }
            )
    return merged


def _normalize_timeline_items(value: Any) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    if isinstance(value, dict):
        candidate_items = value.get("items") or value.get("timeline") or value.get("events")
        if isinstance(candidate_items, list):
            value = candidate_items
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                normalized.append(
                    {
                        "time": _compose_datetime_text(
                            _normalize_text(
                                item.get("time")
                                or item.get("at")
                                or item.get("timestamp")
                                or item.get("time_point")
                            )
                        ),
                        "event": _normalize_text(
                            item.get("event")
                            or item.get("description")
                            or item.get("detail")
                            or item.get("what")
                        ),
                        "resolution": _normalize_text(
                            item.get("resolution")
                            or item.get("action")
                            or item.get("solution")
                            or item.get("mitigation")
                        ),
                        "evidence": _normalize_text(item.get("evidence")),
                    }
                )
            else:
                line = _normalize_text(item)
                if line:
                    normalized.append(
                        {
                            "time": "",
                            "event": line,
                            "resolution": "",
                            "evidence": "",
                        }
                    )
    elif isinstance(value, str):
        for line in _split_lines(value):
            matched = re.match(r"^(?P<time>[^-]+)-(?P<event>.+)$", line)
            if matched:
                normalized.append(
                    {
                        "time": _compose_datetime_text(matched.group("time").strip()),
                        "event": matched.group("event").strip(),
                        "resolution": "",
                        "evidence": "",
                    }
                )
            else:
                normalized.append(
                    {
                        "time": "",
                        "event": line,
                        "resolution": "",
                        "evidence": "",
                    }
                )

    sanitized = []
    for item in normalized:
        if not any(item.values()):
            continue
        sanitized.append(item)
    return sanitized


def _to_business_impact_lines(value: Any) -> list[str]:
    rows = _split_lines(value)
    return rows


def _answer_value(snapshot: IncidentReportSessionSnapshot, key: str) -> Any:
    answer = snapshot.form_answers.get(key)
    if answer is None:
        return None
    return answer.value


def _answer_text(snapshot: IncidentReportSessionSnapshot, key: str) -> str:
    return _normalize_text(_answer_value(snapshot, key))


def _set_answer(
    form_answers: dict[str, IncidentFormAnswer],
    key: str,
    value: Any,
) -> None:
    form_answers[key] = IncidentFormAnswer(value=value, custom_value="")


def _build_report_data_from_snapshot(
    snapshot: IncidentReportSessionSnapshot,
    *,
    strict_required: bool = True,
) -> tuple[dict[str, Any] | None, list[str]]:
    manual_fault_date = _format_date_text(_answer_text(snapshot, MANUAL_FAULT_DATE))
    manual_fault_time = _normalize_text(_answer_value(snapshot, MANUAL_FAULT_TIME))
    manual_reporting_person = _answer_text(snapshot, MANUAL_REPORTING_PERSON)
    manual_site_id = _answer_text(snapshot, MANUAL_SITE_ID)
    manual_system = _answer_text(snapshot, MANUAL_SYSTEM)
    manual_location = _answer_text(snapshot, MANUAL_LOCATION)
    manual_fault_symptom = _answer_text(snapshot, MANUAL_FAULT_SYMPTOM)

    body_description = _answer_text(snapshot, BODY_DESCRIPTION) or _answer_text(
        snapshot, QUICK_NARRATIVE
    )
    body_timeline = _normalize_timeline_items(_answer_value(snapshot, BODY_TIMELINE))
    if not body_timeline:
        body_timeline = _normalize_timeline_items(_answer_value(snapshot, QUICK_TIMELINE))
    body_impact_scope = _answer_text(snapshot, BODY_IMPACT_SCOPE) or _answer_text(
        snapshot, QUICK_IMPACT_SCOPE
    )
    body_impact_severity = _answer_text(snapshot, BODY_IMPACT_SEVERITY) or _answer_text(
        snapshot, QUICK_IMPACT_SEVERITY
    )
    body_root_cause = _answer_text(snapshot, BODY_ROOT_CAUSE) or _answer_text(
        snapshot, QUICK_ROOT_CAUSE_GUESS
    )
    body_follow_up = _answer_text(snapshot, BODY_FOLLOW_UP) or _answer_text(
        snapshot, QUICK_FOLLOW_UP_ACTION
    )
    body_trigger = _answer_text(snapshot, BODY_TRIGGER)
    body_affected_date = _answer_text(snapshot, BODY_AFFECTED_DATE)

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
        if not _normalize_text(value):
            missing_fields.append(label)
    if not body_timeline:
        missing_fields.append("AI正文-时间线")
    if strict_required and missing_fields:
        return None, missing_fields

    affected_date, affected_from, affected_to = _split_affected_date_summary(body_affected_date)
    incident_date = affected_date or _format_date_text(manual_fault_date)
    timeline_times = [
        _normalize_text(item.get("time"))
        for item in body_timeline
        if _normalize_text(item.get("time"))
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

    start_time = _compose_datetime_text(start_time_raw, fallback_date=incident_date) or start_time_raw
    detection_time = (
        _compose_datetime_text(detection_time_raw, fallback_date=incident_date)
        or detection_time_raw
        or start_time
    )
    resolution_time = (
        _compose_datetime_text(resolution_time_raw, fallback_date=incident_date)
        or resolution_time_raw
        or detection_time
    )

    total_duration = "N/A"
    start_dt = _parse_date_time(start_time)
    end_dt = _parse_date_time(resolution_time)
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
        event_text = _normalize_text(timeline_item.get("event"))
        resolution_text = _normalize_text(timeline_item.get("resolution"))
        if resolution_text:
            event_text = f"{event_text} (Resolution: {resolution_text})".strip()
        event_time = _compose_datetime_text(
            _normalize_text(timeline_item.get("time")),
            fallback_date=incident_date,
        )
        event_sequence.append(
            {
                "time": event_time or _normalize_time_text(_normalize_text(timeline_item.get("time"))),
                "event": event_text,
                "evidence": _normalize_text(timeline_item.get("evidence")),
            }
        )

    follow_up_lines = _split_lines(body_follow_up)
    immediate_actions = []
    if body_timeline:
        for item in body_timeline:
            resolution = _normalize_text(item.get("resolution"))
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

    appendix_notes, rich_text_images = _extract_appendix_from_rich_text(
        _answer_value(snapshot, APPENDIX_NOTES)
    )
    if not appendix_notes:
        appendix_notes = _answer_text(snapshot, APPENDIX_NOTES)
    appendix_images = _merge_appendix_images(
        rich_text_images,
        _safe_json_list(_answer_value(snapshot, APPENDIX_IMAGES)),
    )

    report_data = {
        "reference_no": _answer_text(snapshot, MANUAL_REFERENCE_NO) or _build_reference_no(),
        "fault_date": manual_fault_date,
        "fault_time": manual_fault_time,
        "reporting_person": manual_reporting_person,
        "verified_by": _answer_text(snapshot, MANUAL_VERIFIED_BY) or "N/A",
        "site_id": manual_site_id,
        "system": manual_system,
        "location": manual_location,
        "fault_details": manual_fault_symptom,
        "arrival_datetime": _format_datetime_text(_answer_text(snapshot, MANUAL_ARRIVAL_DATETIME))
        or start_time,
        "clearance_datetime": _format_datetime_text(
            _answer_text(snapshot, MANUAL_CLEARANCE_DATETIME)
        )
        or resolution_time,
        "service_person": _answer_text(snapshot, MANUAL_SERVICE_PERSON),
        "fault_cause": _answer_text(snapshot, MANUAL_FAULT_CAUSE) or body_root_cause,
        "materials_used": _answer_text(snapshot, MANUAL_MATERIALS_USED),
        "repair_details": _answer_text(snapshot, MANUAL_REPAIR_DETAILS),
        "contractor_staff": _answer_text(snapshot, MANUAL_CONTRACTOR_STAFF),
        "contractor_date": _format_date_text(_answer_text(snapshot, MANUAL_CONTRACTOR_DATE))
        or manual_fault_date,
        "status": _answer_text(snapshot, MANUAL_STATUS),
        "severity": _answer_text(snapshot, MANUAL_SEVERITY) or body_impact_severity,
        "comments": _answer_text(snapshot, MANUAL_COMMENTS),
        "employer_rep": _answer_text(snapshot, MANUAL_EMPLOYER_REP),
        "closeout_date": _format_date_text(_answer_text(snapshot, MANUAL_CLOSEOUT_DATE))
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
            "business_impact": _to_business_impact_lines(
                _answer_value(snapshot, BODY_BUSINESS_IMPACT)
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
            "business_impact": _to_business_impact_lines(_answer_value(snapshot, BODY_BUSINESS_IMPACT)),
            "trigger": body_trigger or body_root_cause,
        },
    }
    return report_data, []


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


def _build_initial_output_name(*, session_title: str, session_id: str) -> str:
    normalized_title = session_title.strip().replace(" ", "-").replace("/", "-")
    if not normalized_title:
        normalized_title = f"incident-report-{session_id[:8]}"
    return f"{normalized_title}-V1.docx"


def _build_preview_output_name(*, session_title: str, session_id: str) -> str:
    normalized_title = session_title.strip().replace(" ", "-").replace("/", "-")
    if not normalized_title:
        normalized_title = f"incident-report-{session_id[:8]}"
    return f"{normalized_title}-preview.docx"


_incident_generator_module: Any | None = None


def _load_incident_generator_module() -> Any:
    global _incident_generator_module
    if _incident_generator_module is not None:
        return _incident_generator_module
    if not INCIDENT_REPORT_SCRIPT_PATH.is_file():
        raise RuntimeError("未找到事故报告脚本，无法生成预览。")
    spec = importlib.util.spec_from_file_location(
        "incident_report_generator_module",
        INCIDENT_REPORT_SCRIPT_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("加载事故报告脚本失败。")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _incident_generator_module = module
    return module


def _render_docx_bytes_from_report_data(report_data: dict[str, Any]) -> bytes:
    module = _load_incident_generator_module()
    normalized = module.normalize_incident_data(report_data)
    generator = module.FaultLogFormGenerator()
    document = generator.generate_form(normalized)
    output = io.BytesIO()
    document.save(output)
    return output.getvalue()


def _save_docx_bytes_as_generated_attachment(
    *,
    docx_bytes: bytes,
    conversation_id: str,
    output_name: str,
) -> Any:
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as temp_file:
        temp_file.write(docx_bytes)
        temp_path = Path(temp_file.name)
    try:
        return save_generated_attachment(
            source_path=temp_path,
            conversation_id=conversation_id,
            skill_id=INCIDENT_REPORT_SKILL_ID,
            output_name=output_name,
            mime_type=INCIDENT_REPORT_DOCX_MIME_TYPE,
        )
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except Exception:
            pass


def _convert_docx_bytes_to_pdf_bytes(docx_bytes: bytes) -> bytes:
    libreoffice_bin = shutil.which("libreoffice") or shutil.which("soffice")
    if not libreoffice_bin:
        raise RuntimeError("未检测到 LibreOffice，无法生成 PDF 预览。")

    with tempfile.TemporaryDirectory(prefix="incident-preview-") as temp_dir:
        temp_path = Path(temp_dir)
        docx_path = temp_path / "incident-preview.docx"
        pdf_path = temp_path / "incident-preview.pdf"
        docx_path.write_bytes(docx_bytes)

        command = [
            libreoffice_bin,
            "--headless",
            "--convert-to",
            "pdf:writer_pdf_Export",
            "--outdir",
            str(temp_path),
            str(docx_path),
        ]
        process = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=60,
        )
        if process.returncode != 0 or not pdf_path.is_file():
            stderr_text = process.stderr.decode("utf-8", errors="ignore").strip()
            stdout_text = process.stdout.decode("utf-8", errors="ignore").strip()
            detail = stderr_text or stdout_text or "unknown error"
            raise RuntimeError(f"DOCX 转 PDF 失败：{detail}")
        return pdf_path.read_bytes()


def _convert_docx_bytes_to_preview_html(docx_bytes: bytes) -> tuple[str, list[str]]:
    if mammoth is None:
        raise RuntimeError("缺少 mammoth 依赖，无法进行 Word 预览。")
    result = mammoth.convert_to_html(io.BytesIO(docx_bytes))
    warnings = [
        _normalize_text(getattr(message, "message", ""))
        for message in result.messages
        if _normalize_text(getattr(message, "message", ""))
    ]
    return result.value, warnings


def _load_docx_bytes_from_attachment(attachment_id: str) -> bytes:
    metadata, attachment_path, is_expired = resolve_attachment_path(attachment_id)
    if is_expired:
        raise RuntimeError("预览附件已过期，请重新生成。")
    if metadata is None or attachment_path is None:
        raise RuntimeError("未找到可预览的附件。")
    if not _is_docx_attachment(metadata):
        raise RuntimeError("仅支持预览 DOCX 附件。")
    return attachment_path.read_bytes()


def _build_preview_payload_from_docx_bytes(
    docx_bytes: bytes,
) -> tuple[str, str | None, list[str]]:
    warnings: list[str] = []
    html = ""
    pdf_base64: str | None = None

    try:
        pdf_bytes = _convert_docx_bytes_to_pdf_bytes(docx_bytes)
        pdf_base64 = base64.b64encode(pdf_bytes).decode("ascii")
    except Exception as exc:
        warnings.append(f"PDF 预览生成失败，已回退为 HTML：{_normalize_text(exc)}")

    try:
        html, html_warnings = _convert_docx_bytes_to_preview_html(docx_bytes)
        warnings.extend(html_warnings)
    except Exception as exc:
        if pdf_base64 is None:
            raise RuntimeError(f"文档预览失败：{_normalize_text(exc)}") from exc
        warnings.append(f"HTML 预览生成失败：{_normalize_text(exc)}")

    return html, pdf_base64, warnings


_TRANSLATION_SKIP_KEYS = {
    "reference_no",
    "fault_date",
    "fault_time",
    "arrival_datetime",
    "clearance_datetime",
    "contractor_date",
    "closeout_date",
    "start_time",
    "detection_time",
    "resolution_time",
    "total_duration",
    "time",
    "date",
    "data_url",
    "download_url",
    "attachment_id",
    "mime_type",
    "size_label",
    "version",
    "generated_at",
}

_TRANSLATION_CACHE_MAX_ENTRIES = 4096
_TRANSLATION_CACHE: OrderedDict[str, str] = OrderedDict()

_PREVIEW_RESULT_CACHE_MAX_ENTRIES = 12
_PREVIEW_RESULT_CACHE: OrderedDict[str, IncidentReportPreviewResponse] = OrderedDict()
_TRANSLATION_ENGINE_NAME = "python-google-translator"


def _stable_payload_hash(payload: Any) -> str:
    try:
        normalized = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except Exception:
        normalized = repr(payload)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _translation_cache_key(*, model_name: str, source_text: str) -> str:
    source_hash = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    return f"{model_name}:{source_hash}"


def _translation_cache_get(key: str) -> str | None:
    cached = _TRANSLATION_CACHE.get(key)
    if cached is None:
        return None
    _TRANSLATION_CACHE.move_to_end(key)
    return cached


def _translation_cache_set(*, key: str, value: str) -> None:
    _TRANSLATION_CACHE[key] = value
    _TRANSLATION_CACHE.move_to_end(key)
    while len(_TRANSLATION_CACHE) > _TRANSLATION_CACHE_MAX_ENTRIES:
        _TRANSLATION_CACHE.popitem(last=False)


def _preview_cache_get(cache_key: str) -> IncidentReportPreviewResponse | None:
    cached = _PREVIEW_RESULT_CACHE.get(cache_key)
    if cached is None:
        return None
    _PREVIEW_RESULT_CACHE.move_to_end(cache_key)
    return cached.model_copy(deep=True)


def _preview_cache_set(
    *, cache_key: str, payload: IncidentReportPreviewResponse
) -> None:
    _PREVIEW_RESULT_CACHE[cache_key] = payload.model_copy(deep=True)
    _PREVIEW_RESULT_CACHE.move_to_end(cache_key)
    while len(_PREVIEW_RESULT_CACHE) > _PREVIEW_RESULT_CACHE_MAX_ENTRIES:
        _PREVIEW_RESULT_CACHE.popitem(last=False)


def _preview_template_token() -> str:
    try:
        return str(INCIDENT_REPORT_SCRIPT_PATH.stat().st_mtime_ns)
    except Exception:
        return "unknown"


def _should_skip_translation(path: list[str], value: str) -> bool:
    if not path:
        return False
    key = path[-1]
    if key in _TRANSLATION_SKIP_KEYS:
        return True
    lowered = value.lower()
    if lowered.startswith("data:image"):
        return True
    return False


def _collect_translation_targets(
    payload: Any,
    *,
    path: list[str],
    targets: dict[str, str],
) -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            _collect_translation_targets(value, path=[*path, key], targets=targets)
        return
    if isinstance(payload, list):
        for index, value in enumerate(payload):
            _collect_translation_targets(value, path=[*path, str(index)], targets=targets)
        return
    if not isinstance(payload, str):
        return

    normalized = _normalize_text(payload)
    if not normalized:
        return
    if _should_skip_translation(path, normalized):
        return
    targets[".".join(path)] = normalized


def _set_nested_string_value(payload: Any, path_key: str, value: str) -> bool:
    path = [part for part in path_key.split(".") if part]
    if not path:
        return False

    current = payload
    for index, part in enumerate(path):
        is_last = index == len(path) - 1
        if isinstance(current, list):
            if not part.isdigit():
                return False
            item_index = int(part)
            if item_index < 0 or item_index >= len(current):
                return False
            if is_last:
                current[item_index] = value
                return True
            current = current[item_index]
            continue
        if isinstance(current, dict):
            if part not in current:
                return False
            if is_last:
                current[part] = value
                return True
            current = current[part]
            continue
        return False
    return False


async def _translate_report_data_to_english(
    *,
    report_data: dict[str, Any],
    model: str | None,
) -> dict[str, Any]:
    _ = model
    if GoogleTranslator is None:
        return report_data

    targets: dict[str, str] = {}
    _collect_translation_targets(report_data, path=[], targets=targets)
    if not targets:
        return report_data

    translations: dict[str, str] = {}
    pending_targets: dict[str, str] = {}
    for path_key, source_text in targets.items():
        cache_key = _translation_cache_key(
            model_name=_TRANSLATION_ENGINE_NAME,
            source_text=source_text,
        )
        cached_text = _translation_cache_get(cache_key)
        if cached_text:
            translations[path_key] = cached_text
        else:
            pending_targets[path_key] = source_text

    if pending_targets:
        pending_items = list(pending_targets.items())
        chunk_size = 48
        for start in range(0, len(pending_items), chunk_size):
            chunk_items = pending_items[start : start + chunk_size]
            source_texts = [source_text for _, source_text in chunk_items]
            translated_texts: list[str] = []

            try:
                translator = GoogleTranslator(source="auto", target="en")
                translated_batch = await asyncio.to_thread(
                    translator.translate_batch,
                    source_texts,
                )
                if isinstance(translated_batch, list):
                    translated_texts = [
                        _normalize_text(item) if isinstance(item, str) else ""
                        for item in translated_batch
                    ]
            except Exception:
                translated_texts = []

            if len(translated_texts) != len(source_texts):
                translated_texts = []
                for source_text in source_texts:
                    translated_value = ""
                    try:
                        translator = GoogleTranslator(source="auto", target="en")
                        translated_value = _normalize_text(
                            await asyncio.to_thread(translator.translate, source_text)
                        )
                    except Exception:
                        translated_value = ""
                    translated_texts.append(translated_value)

            for (path_key, source_text), translated_text in zip(
                chunk_items,
                translated_texts,
                strict=False,
            ):
                if not translated_text:
                    continue
                translations[path_key] = translated_text
                _translation_cache_set(
                    key=_translation_cache_key(
                        model_name=_TRANSLATION_ENGINE_NAME,
                        source_text=source_text,
                    ),
                    value=translated_text,
                )

    if not translations:
        return report_data

    translated = deepcopy(report_data)
    for path_key, original in targets.items():
        translated_text = _normalize_text(translations.get(path_key))
        if not translated_text:
            continue
        if translated_text == original:
            continue
        _set_nested_string_value(translated, path_key, translated_text)
    return translated


def _apply_quick_generation_payload(
    *,
    form_answers: dict[str, IncidentFormAnswer],
    payload: dict[str, Any],
) -> None:
    _set_answer(form_answers, BODY_DESCRIPTION, _normalize_text(payload.get("description")))
    _set_answer(
        form_answers,
        BODY_AFFECTED_DATE,
        _normalize_text(payload.get("affected_date_summary")),
    )
    timeline = _normalize_timeline_items(payload.get("timeline"))
    if timeline:
        _set_answer(form_answers, BODY_TIMELINE, timeline)
        _set_answer(form_answers, QUICK_TIMELINE, timeline)
    _set_answer(form_answers, BODY_IMPACT_SCOPE, _normalize_text(payload.get("impact_scope")))
    _set_answer(
        form_answers,
        BODY_IMPACT_SEVERITY,
        _normalize_text(payload.get("impact_severity")),
    )
    _set_answer(
        form_answers,
        BODY_BUSINESS_IMPACT,
        "\n".join(_split_lines(payload.get("business_impact"))),
    )
    _set_answer(form_answers, BODY_TRIGGER, _normalize_text(payload.get("trigger")))
    _set_answer(form_answers, BODY_ROOT_CAUSE, _normalize_text(payload.get("root_cause")))
    _set_answer(
        form_answers,
        BODY_FOLLOW_UP,
        "\n".join(_split_lines(payload.get("follow_up_actions"))),
    )

    if timeline:
        first_time = _normalize_text(timeline[0].get("time"))
        existing_fault_date = _answer_value_from_answers(form_answers, MANUAL_FAULT_DATE)
        if first_time and not _normalize_text(existing_fault_date):
            matched = re.match(
                r"^(?P<date>\d{2}/\d{2}/\d{4})\s+(?P<time>\d{2}:\d{2})$", first_time
            )
            if matched:
                _set_answer(form_answers, MANUAL_FAULT_DATE, matched.group("date"))
                _set_answer(form_answers, MANUAL_FAULT_TIME, matched.group("time"))


def _build_quick_generation_prompt(snapshot: IncidentReportSessionSnapshot) -> str:
    narrative = _answer_text(snapshot, QUICK_NARRATIVE)
    timeline = _normalize_timeline_items(_answer_value(snapshot, QUICK_TIMELINE))
    impact_scope = _answer_text(snapshot, QUICK_IMPACT_SCOPE)
    severity = _answer_text(snapshot, QUICK_IMPACT_SEVERITY)
    root_cause_guess = _answer_text(snapshot, QUICK_ROOT_CAUSE_GUESS)
    follow_up = _answer_text(snapshot, QUICK_FOLLOW_UP_ACTION)
    return (
        "你是事故报告正文生成助手。基于给定输入提炼并润色正文，禁止编造事实。"
        "请仅输出 JSON 对象，不要输出额外说明。"
        "JSON 键必须为：description, affected_date_summary, timeline, impact_scope, impact_severity, "
        "business_impact, trigger, root_cause, follow_up_actions。"
        "timeline 为数组，每项包含 time,event,resolution,evidence。\n"
        f"事故简述：{narrative or 'N/A'}\n"
        f"时间线输入：{json.dumps(timeline, ensure_ascii=False)}\n"
        f"影响范围：{impact_scope or 'N/A'}\n"
        f"严重级别：{severity or 'N/A'}\n"
        f"根因猜测：{root_cause_guess or 'N/A'}\n"
        f"后续动作：{follow_up or 'N/A'}"
    )


def _build_section_generation_prompt(
    snapshot: IncidentReportSessionSnapshot,
    *,
    section_id: str,
    timeline_index: int | None,
) -> tuple[str, str]:
    section_key = section_id.strip().lower()
    body_context = {
        "description": _answer_text(snapshot, BODY_DESCRIPTION),
        "affected_date_summary": _answer_text(snapshot, BODY_AFFECTED_DATE),
        "timeline": _normalize_timeline_items(_answer_value(snapshot, BODY_TIMELINE)),
        "impact_scope": _answer_text(snapshot, BODY_IMPACT_SCOPE),
        "impact_severity": _answer_text(snapshot, BODY_IMPACT_SEVERITY),
        "business_impact": _answer_text(snapshot, BODY_BUSINESS_IMPACT),
        "trigger": _answer_text(snapshot, BODY_TRIGGER),
        "root_cause": _answer_text(snapshot, BODY_ROOT_CAUSE),
        "follow_up_actions": _answer_text(snapshot, BODY_FOLLOW_UP),
        "quick_narrative": _answer_text(snapshot, QUICK_NARRATIVE),
    }

    if section_key == "description":
        return (
            "仅润色事故简述。返回 JSON：{\"body_description\":\"...\"}。",
            json.dumps(body_context, ensure_ascii=False),
        )
    if section_key == "timeline":
        return (
            "仅润色时间线。返回 JSON：{\"body_timeline\":[{\"time\":\"\",\"event\":\"\",\"resolution\":\"\",\"evidence\":\"\"}],"
            "\"body_affected_date_summary\":\"...\"}。",
            json.dumps(body_context, ensure_ascii=False),
        )
    if section_key == "impact":
        return (
            "仅润色影响范围和严重级别。返回 JSON：{\"body_impact_scope\":\"...\",\"body_impact_severity\":\"...\","
            "\"body_business_impact\":\"按换行分隔\"}。",
            json.dumps(body_context, ensure_ascii=False),
        )
    if section_key == "root_cause":
        return (
            "仅润色根因段。返回 JSON：{\"body_trigger\":\"...\",\"body_root_cause\":\"...\"}。",
            json.dumps(body_context, ensure_ascii=False),
        )
    if section_key == "follow_up":
        return (
            "仅润色后续动作段。返回 JSON：{\"body_follow_up_actions\":\"按换行分隔\"}。",
            json.dumps(body_context, ensure_ascii=False),
        )
    if section_key == "timeline_item":
        timeline = body_context["timeline"]
        if timeline_index is None or timeline_index < 0 or timeline_index >= len(timeline):
            raise ValueError("无效的时间线条目索引。")
        return (
            "仅润色指定时间线条目。返回 JSON：{\"item\":{\"time\":\"\",\"event\":\"\",\"resolution\":\"\",\"evidence\":\"\"}}。",
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


def _apply_section_payload(
    *,
    form_answers: dict[str, IncidentFormAnswer],
    section_id: str,
    timeline_index: int | None,
    payload: dict[str, Any],
) -> None:
    section_key = section_id.strip().lower()
    if section_key == "description":
        _set_answer(form_answers, BODY_DESCRIPTION, _normalize_text(payload.get("body_description")))
        return
    if section_key == "timeline":
        timeline = _normalize_timeline_items(payload.get("body_timeline"))
        if timeline:
            _set_answer(form_answers, BODY_TIMELINE, timeline)
        _set_answer(
            form_answers,
            BODY_AFFECTED_DATE,
            _normalize_text(payload.get("body_affected_date_summary")),
        )
        return
    if section_key == "impact":
        _set_answer(form_answers, BODY_IMPACT_SCOPE, _normalize_text(payload.get("body_impact_scope")))
        _set_answer(
            form_answers,
            BODY_IMPACT_SEVERITY,
            _normalize_text(payload.get("body_impact_severity")),
        )
        _set_answer(
            form_answers,
            BODY_BUSINESS_IMPACT,
            _normalize_text(payload.get("body_business_impact")),
        )
        return
    if section_key == "root_cause":
        _set_answer(form_answers, BODY_TRIGGER, _normalize_text(payload.get("body_trigger")))
        _set_answer(form_answers, BODY_ROOT_CAUSE, _normalize_text(payload.get("body_root_cause")))
        return
    if section_key == "follow_up":
        _set_answer(
            form_answers,
            BODY_FOLLOW_UP,
            _normalize_text(payload.get("body_follow_up_actions")),
        )
        return
    if section_key == "timeline_item":
        timeline = _normalize_timeline_items(_answer_value_from_answers(form_answers, BODY_TIMELINE))
        if timeline_index is None or timeline_index < 0 or timeline_index >= len(timeline):
            raise ValueError("无效的时间线条目索引。")
        item = payload.get("item")
        if not isinstance(item, dict):
            raise ValueError("模型返回的 timeline_item 格式不正确。")
        normalized_time = _compose_datetime_text(_normalize_text(item.get("time")))
        if not normalized_time:
            normalized_time = _normalize_time_text(_normalize_text(item.get("time")))
        timeline[timeline_index] = {
            "time": normalized_time,
            "event": _normalize_text(item.get("event")),
            "resolution": _normalize_text(item.get("resolution")),
            "evidence": _normalize_text(item.get("evidence")),
        }
        _set_answer(form_answers, BODY_TIMELINE, timeline)
        return
    raise ValueError("不支持的 section_id。")


def _answer_value_from_answers(form_answers: dict[str, IncidentFormAnswer], key: str) -> Any:
    answer = form_answers.get(key)
    if answer is None:
        return None
    return answer.value


def _build_body_generation_messages(prompt: str, context_json: str) -> list[dict[str, Any]]:
    return [
        {
            "role": "system",
            "content": "你是事故报告正文助手。只输出 JSON，不要输出代码块，不要编造事实。",
        },
        {
            "role": "user",
            "content": f"{prompt}\n当前上下文：{context_json}",
        },
    ]


async def _run_body_generation_with_trace(
    *,
    detail: IncidentReportSessionDetail,
    model: str,
    reranker_model: str | None,
    section_id: str,
    timeline_index: int | None,
    prompt: str,
    context_json: str,
    apply_payload: Any,
) -> IncidentBodyGenerateResponse:
    if not settings.ollama_base_url:
        raise RuntimeError("未配置 OLLAMA_BASE_URL。")

    effective_reranker_model = (reranker_model or "").strip() or model
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
        },
    )
    await _flush_trace_safely(recorder)

    try:
        response_text, done_reason = await _run_plain_chat_completion(
            model=model,
            messages=_build_body_generation_messages(prompt, context_json),
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
    next_snapshot.is_locked = False

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
        base_report_data, _ = _build_report_data_from_snapshot(
            snapshot,
            strict_required=False,
        )
        if base_report_data is not None:
            english_base_report_data = await _translate_report_data_to_english(
                report_data=base_report_data,
                model=None,
            )
            base_docx_bytes = _render_docx_bytes_from_report_data(
                english_base_report_data
            )
            base_attachment = _save_docx_bytes_as_generated_attachment(
                docx_bytes=base_docx_bytes,
                conversation_id=session_id,
                output_name=_build_initial_output_name(
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
        # 初始化 V1 失败时不阻断会话创建，后续仍可通过实时预览链路导出文档。
        pass
    await save_incident_session_summary(summary)
    await save_incident_session_snapshot(session_id, snapshot)
    await touch_incident_session_index(session_id, now.timestamp())
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
    next_snapshot.is_locked = False
    next_snapshot.polish_error = None

    await save_incident_session_summary(next_summary)
    await save_incident_session_snapshot(session_id, next_snapshot)
    await touch_incident_session_index(session_id, now.timestamp())
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
    await touch_incident_session_index(session_id, now.timestamp())
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
    if not _answer_text(detail.snapshot, QUICK_NARRATIVE):
        raise ValueError("请先填写快填模式的事故简述。")

    prompt = _build_quick_generation_prompt(detail.snapshot)

    def _apply(form_answers: dict[str, IncidentFormAnswer], payload: dict[str, Any]) -> None:
        _apply_quick_generation_payload(form_answers=form_answers, payload=payload)

    return await _run_body_generation_with_trace(
        detail=detail,
        model=model,
        reranker_model=reranker_model,
        section_id="quick",
        timeline_index=None,
        prompt="请将快填输入扩展为完整正文字段。",
        context_json=prompt,
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

    template_token = _preview_template_token()

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
        cached_version_preview = _preview_cache_get(version_cache_key)
        if cached_version_preview is not None:
            return cached_version_preview
        docx_bytes = _load_docx_bytes_from_attachment(
            target_version.attachment.attachment_id
        )
        html, pdf_base64, warnings = _build_preview_payload_from_docx_bytes(
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
        _preview_cache_set(cache_key=version_cache_key, payload=version_payload)
        return version_payload

    draft_report_data, _ = _build_report_data_from_snapshot(
        detail.snapshot,
        strict_required=False,
    )
    if draft_report_data is None:
        raise RuntimeError("当前草稿无法生成预览。")
    preview_model = _normalize_text(model) or _normalize_text(reranker_model)
    draft_hash = _stable_payload_hash(draft_report_data)
    draft_cache_key = (
        f"draft:{session_id}:{preview_model}:{template_token}:{draft_hash}"
    )
    cached_draft_preview = _preview_cache_get(draft_cache_key)
    if cached_draft_preview is not None:
        return cached_draft_preview
    translated_report_data = await _translate_report_data_to_english(
        report_data=draft_report_data,
        model=preview_model or None,
    )
    draft_docx_bytes = _render_docx_bytes_from_report_data(translated_report_data)
    html, pdf_base64, warnings = _build_preview_payload_from_docx_bytes(
        draft_docx_bytes
    )
    draft_payload = IncidentReportPreviewResponse(
        source="draft",
        version=None,
        label="Realtime Draft Preview",
        html=html,
        docx_base64=base64.b64encode(draft_docx_bytes).decode("ascii"),
        docx_file_name=_build_preview_output_name(
            session_title=detail.title,
            session_id=detail.id,
        ),
        pdf_base64=pdf_base64,
        warnings=warnings,
    )
    _preview_cache_set(cache_key=draft_cache_key, payload=draft_payload)
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
