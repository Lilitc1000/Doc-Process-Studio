import json
import logging
from collections.abc import Awaitable
from typing import Any, cast

from .cache_client import get_redis_client
from .config import settings

logger = logging.getLogger(__name__)


def build_cache_key(*parts: str) -> str:
    normalized_parts = [part.strip() for part in parts if part.strip()]
    return ":".join([settings.redis_key_prefix, *normalized_parts])


async def get_json(key: str) -> dict[str, Any] | list[Any] | None:
    try:
        raw_value: str | None = await get_redis_client().get(key)
    except Exception as exc:  # noqa: BLE001 - Redis 不可用时降级为未命中，不阻断业务
        logger.debug("cache get failed (key=%s): %s", key, exc)
        return None
    if raw_value is None:
        return None
    loaded: dict[str, Any] | list[Any] = json.loads(raw_value)
    return loaded


async def set_json(
    key: str,
    payload: dict[str, Any] | list[Any],
    ttl_seconds: int | None = None,
) -> None:
    kwargs: dict[str, Any] = {}
    if ttl_seconds is not None:
        kwargs["ex"] = ttl_seconds
    try:
        await get_redis_client().set(
            key,
            json.dumps(payload, ensure_ascii=False),
            **kwargs,
        )
    except Exception as exc:  # noqa: BLE001 - 写缓存失败不应影响主流程
        logger.debug("cache set failed (key=%s): %s", key, exc)


async def ping_redis() -> bool:
    return bool(await cast(Awaitable[bool], get_redis_client().ping()))


async def delete_key(key: str) -> int:
    try:
        return int(await cast(Awaitable[int], get_redis_client().delete(key)))
    except Exception as exc:  # noqa: BLE001 - 缓存失效失败只降级不影响一致性
        logger.debug("cache delete failed (key=%s): %s", key, exc)
        return 0


async def get_ttl_seconds(key: str) -> int:
    return int(await cast(Awaitable[int], get_redis_client().ttl(key)))


async def refresh_ttl(key: str, ttl_seconds: int | None = None) -> bool:
    return bool(
        await cast(
            Awaitable[bool],
            get_redis_client().expire(
                key,
                ttl_seconds or settings.redis_ttl_seconds,
            ),
        ),
    )
