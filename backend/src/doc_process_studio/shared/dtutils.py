from datetime import UTC, datetime


def utcnow() -> datetime:
    return datetime.now(UTC)


def utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()
