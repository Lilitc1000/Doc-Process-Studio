import json
from typing import Any

from .config import settings
from .cache_client import get_redis_client


def build_cache_key(*parts: str) -> str:
    normalized_parts = [part.strip() for part in parts if part.strip()]
    return ":".join([settings.redis_key_prefix, *normalized_parts])


async def get_json(key: str) -> dict[str, Any] | list[Any] | None:
    raw_value = await get_redis_client().get(key)
    if raw_value is None:
        return None
    return json.loads(raw_value)


async def set_json(
    key: str,
    payload: dict[str, Any] | list[Any],
    ttl_seconds: int | None = None,
) -> None:
    kwargs: dict[str, Any] = {}
    if ttl_seconds is not None:
        kwargs["ex"] = ttl_seconds
    await get_redis_client().set(
        key,
        json.dumps(payload, ensure_ascii=False),
        **kwargs,
    )


async def ping_redis() -> bool:
    return bool(await get_redis_client().ping())


async def delete_key(key: str) -> int:
    return int(await get_redis_client().delete(key))


async def get_ttl_seconds(key: str) -> int:
    return int(await get_redis_client().ttl(key))


async def refresh_ttl(key: str, ttl_seconds: int | None = None) -> bool:
    return bool(
        await get_redis_client().expire(
            key,
            ttl_seconds or settings.redis_ttl_seconds,
        )
    )

