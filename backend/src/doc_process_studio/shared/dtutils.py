from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from typing import overload

UTC_PLUS_8 = timezone(timedelta(hours=8))


def utcnow() -> datetime:
    return datetime.now(UTC)


def utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


@overload
def to_utc8(dt: None) -> None: ...


@overload
def to_utc8(dt: datetime) -> datetime: ...


def to_utc8(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC_PLUS_8)
