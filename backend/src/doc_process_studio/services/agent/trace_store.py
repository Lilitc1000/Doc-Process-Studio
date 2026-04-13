from datetime import UTC, datetime
from typing import Any

from ...settings import settings
from ..infra.redis_store import build_cache_key, get_json, set_json


def _utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


def build_agent_trace_key(*, tenant_id: str, trace_id: str) -> str:
    return build_cache_key("agent-trace", tenant_id.strip() or "default", trace_id.strip())


async def save_agent_trace(
    *,
    tenant_id: str,
    trace_id: str,
    payload: dict[str, Any],
) -> None:
    if not settings.agent_trace_store_enabled:
        return
    ttl_seconds = settings.agent_trace_ttl_seconds if settings.agent_trace_ttl_seconds > 0 else None
    await set_json(
        build_agent_trace_key(tenant_id=tenant_id, trace_id=trace_id),
        payload,
        ttl_seconds=ttl_seconds,
    )


async def load_agent_trace(
    *,
    tenant_id: str,
    trace_id: str,
) -> dict[str, Any] | None:
    payload = await get_json(build_agent_trace_key(tenant_id=tenant_id, trace_id=trace_id))
    if isinstance(payload, dict):
        return payload
    return None


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
        self.payload: dict[str, Any] = {
            "trace_id": trace_id,
            "tenant_id": tenant_id,
            "conversation_id": conversation_id,
            "user_message_id": user_message_id,
            "model": model,
            "reranker_model": reranker_model,
            "started_at": _utcnow_iso(),
            "planner": None,
            "events": [],
            "rounds": [],
            "final": {},
        }

    def add_event(self, *, event_type: str, detail: dict[str, Any]) -> None:
        self.payload["events"].append(
            {
                "type": event_type,
                "at": _utcnow_iso(),
                "detail": detail,
            }
        )

    def set_planner(self, planner_payload: dict[str, Any]) -> None:
        self.payload["planner"] = planner_payload

    def add_round(self, *, round_index: int, detail: dict[str, Any]) -> None:
        self.payload["rounds"].append(
            {
                "round": round_index,
                "at": _utcnow_iso(),
                **detail,
            }
        )

    def set_final(self, *, done_reason: str | None, error: str | None) -> None:
        self.payload["final"] = {
            "done_reason": done_reason,
            "error": error,
            "finished_at": _utcnow_iso(),
        }

    async def flush(self) -> None:
        await save_agent_trace(
            tenant_id=self.tenant_id,
            trace_id=self.trace_id,
            payload=self.payload,
        )

