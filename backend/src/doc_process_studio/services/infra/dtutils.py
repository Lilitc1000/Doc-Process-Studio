import json
import re
from datetime import UTC, datetime
from typing import Any

from ..agent.error_detail import build_exception_detail


def utcnow() -> datetime:
    return datetime.now(UTC)


def utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


def normalize_tenant_id(tenant_id: str) -> str:
    normalized = tenant_id.strip()
    return normalized or "default"


def parse_json_object(value: str) -> dict[str, Any] | None:
    normalized = value.strip()
    if not normalized:
        return None

    try:
        parsed = json.loads(normalized)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict):
        return parsed

    if normalized.startswith("```"):
        normalized = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", normalized)
        normalized = re.sub(r"\s*```$", "", normalized).strip()
        try:
            parsed = json.loads(normalized)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            return parsed

    matched = re.search(r"\{[\s\S]*\}", normalized)
    if matched is None:
        return None
    try:
        parsed = json.loads(matched.group(0))
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, dict):
        return parsed
    return None


async def build_error_event_detail(
    *,
    message: str,
    exc: BaseException | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    detail: dict[str, Any] = {"message": message}
    if exc is not None:
        detail["error_detail"] = await build_exception_detail(exc)
    if extra:
        detail.update(extra)
    return detail
