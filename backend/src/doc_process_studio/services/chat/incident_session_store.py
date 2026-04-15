from ...models.conversation.incident_report import (
    IncidentReportSessionSnapshot,
    IncidentReportSessionSummary,
)
from ..infra.redis_store import (
    build_cache_key,
    delete_key,
    get_json,
    get_redis_client,
    set_json,
)

INCIDENT_SESSION_INDEX_KEY = build_cache_key("incident-report-sessions", "index")


def build_incident_session_meta_key(session_id: str) -> str:
    return build_cache_key("incident-report-session", session_id, "meta")


def build_incident_session_snapshot_key(session_id: str) -> str:
    return build_cache_key("incident-report-session", session_id, "snapshot")


async def list_incident_session_ids() -> list[str]:
    return await get_redis_client().zrevrange(INCIDENT_SESSION_INDEX_KEY, 0, -1)


async def load_incident_session_summary(
    session_id: str,
) -> IncidentReportSessionSummary | None:
    payload = await get_json(build_incident_session_meta_key(session_id))
    if not isinstance(payload, dict):
        return None
    return IncidentReportSessionSummary.model_validate(payload)


async def load_incident_session_snapshot(
    session_id: str,
) -> IncidentReportSessionSnapshot | None:
    payload = await get_json(build_incident_session_snapshot_key(session_id))
    if not isinstance(payload, dict):
        return None
    return IncidentReportSessionSnapshot.model_validate(payload)


async def save_incident_session_summary(summary: IncidentReportSessionSummary) -> None:
    await set_json(
        build_incident_session_meta_key(summary.id),
        summary.model_dump(mode="json"),
        ttl_seconds=None,
    )


async def save_incident_session_snapshot(
    session_id: str,
    snapshot: IncidentReportSessionSnapshot,
) -> None:
    await set_json(
        build_incident_session_snapshot_key(session_id),
        snapshot.model_dump(mode="json"),
        ttl_seconds=None,
    )


async def touch_incident_session_index(
    session_id: str,
    score: float,
) -> None:
    await get_redis_client().zadd(INCIDENT_SESSION_INDEX_KEY, {session_id: score})


async def delete_incident_session_records(session_id: str) -> bool:
    deleted_meta = await delete_key(build_incident_session_meta_key(session_id))
    deleted_snapshot = await delete_key(build_incident_session_snapshot_key(session_id))
    await get_redis_client().zrem(INCIDENT_SESSION_INDEX_KEY, session_id)
    return bool(deleted_meta or deleted_snapshot)
