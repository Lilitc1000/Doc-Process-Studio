import json
from typing import Any

from ...core.config import settings
from ...shared.dtutils import utcnow_iso
from ...core.request_guard import normalize_tenant_id
from ...core.cache import build_cache_key, get_json, get_redis_client, set_json


def build_agent_trace_key(*, tenant_id: str, trace_id: str) -> str:
    return build_cache_key("agent-trace", normalize_tenant_id(tenant_id), trace_id.strip())


def build_agent_trace_conversation_index_key(*, conversation_id: str) -> str:
    return build_cache_key("agent-trace", "conversation", conversation_id.strip())


def _encode_trace_index_member(*, tenant_id: str, trace_id: str) -> str:
    return json.dumps([normalize_tenant_id(tenant_id), trace_id.strip()], ensure_ascii=False)


def _decode_trace_index_member(member: str) -> tuple[str, str] | None:
    try:
        payload = json.loads(member)
    except json.JSONDecodeError:
        payload = None

    if isinstance(payload, list) and len(payload) == 2:
        tenant_id = str(payload[0]).strip() or "default"
        trace_id = str(payload[1]).strip()
        if trace_id:
            return tenant_id, trace_id
    return None


async def save_agent_trace(
    *,
    tenant_id: str,
    trace_id: str,
    conversation_id: str,
    payload: dict[str, Any],
) -> None:
    if not settings.agent_trace_store_enabled:
        return
    normalized_tenant_id = normalize_tenant_id(tenant_id)
    normalized_trace_id = trace_id.strip()
    normalized_conversation_id = conversation_id.strip()
    if not normalized_trace_id or not normalized_conversation_id:
        return

    ttl_seconds = settings.agent_trace_ttl_seconds if settings.agent_trace_ttl_seconds > 0 else None
    trace_key = build_agent_trace_key(
        tenant_id=normalized_tenant_id,
        trace_id=normalized_trace_id,
    )
    await set_json(
        trace_key,
        payload,
        ttl_seconds=ttl_seconds,
    )
    index_key = build_agent_trace_conversation_index_key(
        conversation_id=normalized_conversation_id
    )
    redis_client = get_redis_client()
    await redis_client.sadd(
        index_key,
        _encode_trace_index_member(
            tenant_id=normalized_tenant_id,
            trace_id=normalized_trace_id,
        ),
    )
    if ttl_seconds is not None:
        await redis_client.expire(index_key, ttl_seconds)


async def load_agent_trace(
    *,
    tenant_id: str,
    trace_id: str,
) -> dict[str, Any] | None:
    payload = await get_json(build_agent_trace_key(tenant_id=tenant_id, trace_id=trace_id))
    if isinstance(payload, dict):
        return payload
    return None


async def delete_agent_traces_for_conversation(
    *,
    conversation_id: str,
) -> int:
    normalized_conversation_id = conversation_id.strip()
    if not normalized_conversation_id:
        return 0

    redis_client = get_redis_client()
    index_key = build_agent_trace_conversation_index_key(
        conversation_id=normalized_conversation_id
    )
    indexed_members = await redis_client.smembers(index_key)
    trace_keys_to_delete: set[str] = set()

    for member in indexed_members:
        decoded = _decode_trace_index_member(member)
        if decoded is None:
            continue
        tenant_id, trace_id = decoded
        trace_keys_to_delete.add(
            build_agent_trace_key(tenant_id=tenant_id, trace_id=trace_id)
        )

    deleted_trace_count = 0
    if trace_keys_to_delete:
        deleted_trace_count = int(await redis_client.delete(*trace_keys_to_delete))

    await redis_client.delete(index_key)
    return deleted_trace_count


class AgentTraceRecorder:
    """按请求收集 agent 决策轨迹，用于回放与审计。"""

    def __init__(
        self,
        *,
        trace_id: str,
        tenant_id: str,
        conversation_id: str,
        user_message_id: str,
        model: str,
        reranker_model: str,
    ) -> None:
        self.trace_id = trace_id
        self.tenant_id = tenant_id
        self.conversation_id = conversation_id
        self.payload: dict[str, Any] = {
            "trace_id": trace_id,
            "tenant_id": tenant_id,
            "conversation_id": conversation_id,
            "user_message_id": user_message_id,
            "model": model,
            "reranker_model": reranker_model,
            "started_at": utcnow_iso(),
            "planner": None,
            "events": [],
            "rounds": [],
            "final": {},
        }

    def add_event(self, *, event_type: str, detail: dict[str, Any]) -> None:
        self.payload["events"].append(
            {
                "type": event_type,
                "at": utcnow_iso(),
                "detail": detail,
            }
        )

    def set_planner(self, planner_payload: dict[str, Any]) -> None:
        self.payload["planner"] = planner_payload

    def add_round(self, *, round_index: int, detail: dict[str, Any]) -> None:
        self.payload["rounds"].append(
            {
                "round": round_index,
                "at": utcnow_iso(),
                **detail,
            }
        )

    def set_final(self, *, done_reason: str | None, error: str | None) -> None:
        self.payload["final"] = {
            "done_reason": done_reason,
            "error": error,
            "finished_at": utcnow_iso(),
        }

    async def flush(self) -> None:
        await save_agent_trace(
            tenant_id=self.tenant_id,
            trace_id=self.trace_id,
            conversation_id=self.conversation_id,
            payload=self.payload,
        )
