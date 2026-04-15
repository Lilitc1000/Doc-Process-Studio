import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from redis.asyncio import ConnectionPool, Redis

from ...settings import settings

_pool: ConnectionPool | None = None


def _build_connection_pool() -> ConnectionPool:
    if not settings.redis_url:
        raise RuntimeError("未配置 REDIS_URL，无法使用 Redis skill 缓存。")

    return ConnectionPool.from_url(
        settings.redis_url,
        password=settings.redis_password,
        decode_responses=True,
        max_connections=16,
        retry_on_timeout=True,
        socket_connect_timeout=5,
        socket_timeout=5,
        health_check_interval=30,
    )


def _get_pool() -> ConnectionPool:
    global _pool

    if _pool is None:
        _pool = _build_connection_pool()
    return _pool


_redis_client: Redis | None = None


def get_redis_client() -> Redis:
    global _redis_client

    if _redis_client is None:
        _redis_client = Redis(connection_pool=_get_pool())
    return _redis_client


def build_cache_key(*parts: str) -> str:
    normalized_parts = [part.strip() for part in parts if part.strip()]
    return ":".join([settings.redis_key_prefix, *normalized_parts])


async def get_json(key: str) -> dict | list | None:
    raw_value = await get_redis_client().get(key)
    if raw_value is None:
        return None
    return json.loads(raw_value)


async def set_json(
    key: str,
    payload: dict | list,
    ttl_seconds: int | None = None,
) -> None:
    if ttl_seconds is None:
        await get_redis_client().set(
            key,
            json.dumps(payload, ensure_ascii=False),
        )
        return

    await get_redis_client().set(
        key,
        json.dumps(payload, ensure_ascii=False),
        ex=ttl_seconds,
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


@asynccontextmanager
async def redis_client_context() -> AsyncIterator[Redis]:
    client = get_redis_client()
    try:
        yield client
    finally:
        pass

