import re
from datetime import UTC, datetime
from html import unescape
from typing import Any

from ...shared.text_utils import parse_json_object
from .constants import (
    STATUS_OPTION_FAULT_CLEARED,
    STATUS_OPTION_FOLLOW_UP_ACTION_REQUIRED,
    STATUS_OPTION_TEMPORARILY_FIXED,
    SEVERITY_OPTION_MAJOR,
    SEVERITY_OPTION_MINOR,
    SEVERITY_OPTION_NOT_APPLICABLE,
)


def normalize_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if value is None:
        return ""
    return str(value).strip()


def split_lines(value: Any) -> list[str]:
    if isinstance(value, list):
        rows = []
        for item in value:
            text = normalize_text(item)
            if text:
                rows.append(text)
        return rows
    text = normalize_text(value)
    if not text:
        return []
    if "\n" in text:
        rows = [line.strip("- ").strip() for line in text.splitlines()]
        return [row for row in rows if row]
    if ";" in text:
        rows = [line.strip() for line in text.split(";")]
        return [row for row in rows if row]
    return [text]


def parse_date_time(value: str) -> datetime | None:
    normalized = normalize_text(value)
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


def format_datetime_text(value: str) -> str:
    normalized = normalize_text(value)
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


def format_date_text(value: str) -> str:
    normalized = normalize_text(value)
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


def normalize_time_text(value: str) -> str:
    normalized = normalize_text(value)
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


def extract_date_text(value: str) -> str:
    normalized = normalize_text(value)
    if not normalized:
        return ""
    matched = re.search(r"(?P<year>\d{4})[./-](?P<month>\d{1,2})[./-](?P<day>\d{1,2})", normalized)
    if matched:
        return f"{int(matched.group('day')):02d}/{int(matched.group('month')):02d}/{matched.group('year')}"
    matched = re.search(r"(?P<day>\d{1,2})[./-](?P<month>\d{1,2})[./-](?P<year>\d{4})", normalized)
    if matched:
        return f"{int(matched.group('day')):02d}/{int(matched.group('month')):02d}/{matched.group('year')}"
    formatted = format_date_text(normalized)
    if re.match(r"^\d{2}/\d{2}/\d{4}$", formatted):
        return formatted
    return ""


def compose_datetime_text(value: str, *, fallback_date: str | None = None) -> str:
    normalized = normalize_text(value)
    if not normalized:
        return ""
    formatted = format_datetime_text(normalized)
    if re.match(r"^\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}$", formatted):
        return formatted
    date_text = extract_date_text(normalized)
    time_text = normalize_time_text(normalized)
    if date_text and time_text:
        return f"{date_text} {time_text}"
    if time_text and fallback_date:
        normalized_date = format_date_text(fallback_date)
        if normalized_date:
            return f"{normalized_date} {time_text}"
    if date_text:
        return date_text
    return time_text or normalized


def split_affected_date_summary(value: str) -> tuple[str, str, str]:
    normalized = normalize_text(value)
    if not normalized:
        return "", "", ""
    date_text = extract_date_text(normalized)
    time_matches = list(
        re.finditer(
            r"(?<!\d)(?P<time>\d{1,2}\s*(?:[:：]\s*\d{1,2}(?:\s*(?:分|m|M))?|(?:点|时|h|H)\s*(?:\d{1,2}\s*(?:分)?|半)?)(?:\s*(?:am|pm))?)(?!\d)",
            normalized,
            flags=re.IGNORECASE,
        )
    )
    times = [normalize_time_text(match.group("time")) for match in time_matches]
    times = [item for item in times if item]
    if len(times) >= 2:
        return date_text, times[0], times[1]
    if len(times) == 1:
        return date_text, times[0], times[0]
    return date_text, "", ""


def safe_json_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        parsed = parse_json_object(value)
        if isinstance(parsed, dict):
            items = parsed.get("items")
            if isinstance(items, list):
                return items
        import json
        try:
            loaded = json.loads(value)
        except json.JSONDecodeError:
            return []
        return loaded if isinstance(loaded, list) else []
    return []


def extract_appendix_from_rich_text(value: Any) -> tuple[str, list[dict[str, str]]]:
    raw = normalize_text(value)
    if not raw:
        return "", []
    if "<" not in raw or ">" not in raw:
        return raw, []

    images: list[dict[str, str]] = []
    for index, match in enumerate(
        re.finditer(r"<img[^>]*src=['\"](?P<src>[^'\"]+)['\"][^>]*>", raw, flags=re.IGNORECASE)
    ):
        data_url = normalize_text(match.group("src"))
        if not data_url.startswith("data:image"):
            continue
        alt_match = re.search(
            r"alt=['\"](?P<alt>[^'\"]*)['\"]",
            match.group(0),
            flags=re.IGNORECASE,
        )
        image_name = (
            normalize_text(alt_match.group("alt")) if alt_match is not None else ""
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


def contains_html_tag(value: Any) -> bool:
    text = normalize_text(value)
    if not text:
        return False
    return re.search(r"</?[A-Za-z][^>]*>", text) is not None


def merge_appendix_images(*image_groups: list[Any]) -> list[dict[str, str]]:
    merged: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    for images in image_groups:
        for item in images:
            if not isinstance(item, dict):
                continue
            data_url = normalize_text(item.get("data_url"))
            if not data_url or not data_url.startswith("data:image"):
                continue
            if data_url in seen_urls:
                continue
            seen_urls.add(data_url)
            name = normalize_text(item.get("name")) or f"appendix-image-{len(merged) + 1}.png"
            merged.append(
                {
                    "name": name,
                    "data_url": data_url,
                }
            )
    return merged


def normalize_timeline_items(value: Any) -> list[dict[str, str]]:
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
                        "time": compose_datetime_text(
                            normalize_text(
                                item.get("time")
                                or item.get("at")
                                or item.get("timestamp")
                                or item.get("time_point")
                            )
                        ),
                        "event": normalize_text(
                            item.get("event")
                            or item.get("description")
                            or item.get("detail")
                            or item.get("what")
                        ),
                        "resolution": normalize_text(
                            item.get("resolution")
                            or item.get("action")
                            or item.get("solution")
                            or item.get("mitigation")
                        ),
                        "evidence": normalize_text(item.get("evidence")),
                    }
                )
            else:
                line = normalize_text(item)
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
        for line in split_lines(value):
            matched = re.match(r"^(?P<time>[^-]+)-(?P<event>.+)$", line)
            if matched:
                normalized.append(
                    {
                        "time": compose_datetime_text(matched.group("time").strip()),
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


def normalize_status_option(value: str) -> str:
    normalized = normalize_text(value).lower()
    if not normalized:
        return STATUS_OPTION_FAULT_CLEARED
    if normalized in {
        STATUS_OPTION_FAULT_CLEARED,
        STATUS_OPTION_TEMPORARILY_FIXED,
        STATUS_OPTION_FOLLOW_UP_ACTION_REQUIRED,
    }:
        return normalized
    if "follow" in normalized or "跟进" in normalized or "后续" in normalized:
        return STATUS_OPTION_FOLLOW_UP_ACTION_REQUIRED
    if "temporar" in normalized or "临时" in normalized:
        return STATUS_OPTION_TEMPORARILY_FIXED
    if "clear" in normalized or "cleared" in normalized or "已清除" in normalized:
        return STATUS_OPTION_FAULT_CLEARED
    return STATUS_OPTION_FAULT_CLEARED


def status_option_to_text(option: str) -> str:
    if option == STATUS_OPTION_TEMPORARILY_FIXED:
        return "Temporarily fixed"
    if option == STATUS_OPTION_FOLLOW_UP_ACTION_REQUIRED:
        return "Follow up action required"
    return "Fault has been Cleared"


def normalize_severity_option(value: str) -> str:
    normalized = normalize_text(value).lower()
    if not normalized:
        return SEVERITY_OPTION_NOT_APPLICABLE
    if normalized in {
        SEVERITY_OPTION_NOT_APPLICABLE,
        SEVERITY_OPTION_MINOR,
        SEVERITY_OPTION_MAJOR,
    }:
        return normalized
    if (
        "major" in normalized
        or "high" in normalized
        or "critical" in normalized
        or "严重" in normalized
        or "重大" in normalized
    ):
        return SEVERITY_OPTION_MAJOR
    if "minor" in normalized or "low" in normalized or "轻微" in normalized:
        return SEVERITY_OPTION_MINOR
    if "not applicable" in normalized or normalized in {"n/a", "na", "不适用"}:
        return SEVERITY_OPTION_NOT_APPLICABLE
    return SEVERITY_OPTION_NOT_APPLICABLE


def severity_option_to_text(option: str) -> str:
    if option == SEVERITY_OPTION_MAJOR:
        return "Major"
    if option == SEVERITY_OPTION_MINOR:
        return "Minor"
    return "Not Applicable"
