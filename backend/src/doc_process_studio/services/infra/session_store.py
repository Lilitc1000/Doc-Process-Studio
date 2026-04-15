from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from ..infra.redis_store import (
    build_cache_key,
    delete_key,
    get_json,
    get_redis_client,
    set_json,
)

TSummary = TypeVar("TSummary", bound=BaseModel)
TSnapshot = TypeVar("TSnapshot", bound=BaseModel)


class RedisSessionStore(Generic[TSummary, TSnapshot]):
    def __init__(
        self,
        *,
        namespace: str,
        summary_model: type[TSummary],
        snapshot_model: type[TSnapshot],
    ) -> None:
        self._namespace = namespace
        self._summary_model = summary_model
        self._snapshot_model = snapshot_model
        self._index_key = build_cache_key(f"{namespace}-sessions", "index")

    def _build_meta_key(self, session_id: str) -> str:
        return build_cache_key(f"{self._namespace}-session", session_id, "meta")

    def _build_snapshot_key(self, session_id: str) -> str:
        return build_cache_key(f"{self._namespace}-session", session_id, "snapshot")

    async def list_session_ids(self) -> list[str]:
        return await get_redis_client().zrevrange(self._index_key, 0, -1)

    async def load_summary(self, session_id: str) -> TSummary | None:
        payload = await get_json(self._build_meta_key(session_id))
        if not isinstance(payload, dict):
            return None
        return self._summary_model.model_validate(payload)

    async def load_snapshot(self, session_id: str) -> TSnapshot | None:
        payload = await get_json(self._build_snapshot_key(session_id))
        if not isinstance(payload, dict):
            return None
        return self._snapshot_model.model_validate(payload)

    async def save_summary(self, summary: TSummary) -> None:
        summary_id = getattr(summary, "id", None)
        if not isinstance(summary_id, str):
            raise ValueError("Summary model must have an 'id' field")
        await set_json(
            self._build_meta_key(summary_id),
            summary.model_dump(mode="json"),
            ttl_seconds=None,
        )

    async def save_snapshot(self, session_id: str, snapshot: TSnapshot) -> None:
        await set_json(
            self._build_snapshot_key(session_id),
            snapshot.model_dump(mode="json"),
            ttl_seconds=None,
        )

    async def touch_index(self, session_id: str, score: float) -> None:
        await get_redis_client().zadd(self._index_key, {session_id: score})

    async def delete_session(self, session_id: str) -> bool:
        deleted_meta = await delete_key(self._build_meta_key(session_id))
        deleted_snapshot = await delete_key(self._build_snapshot_key(session_id))
        await get_redis_client().zrem(self._index_key, session_id)
        return bool(deleted_meta or deleted_snapshot)
