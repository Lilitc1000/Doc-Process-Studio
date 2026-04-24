import json
import re
from typing import Any


def _try_parse_dict(value: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def parse_json_object(value: str) -> dict[str, Any] | None:
    normalized = value.strip()
    if not normalized:
        return None

    result = _try_parse_dict(normalized)
    if result is not None:
        return result

    if normalized.startswith("```"):
        normalized = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", normalized)
        normalized = re.sub(r"\s*```$", "", normalized).strip()
        result = _try_parse_dict(normalized)
        if result is not None:
            return result

    matched = re.search(r"\{[\s\S]*\}", normalized)
    if matched is None:
        return None
    return _try_parse_dict(matched.group(0))
