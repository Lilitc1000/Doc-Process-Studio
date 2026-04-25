from redis.asyncio import ConnectionPool, Redis

from .config import settings

_pool: ConnectionPool | None = None


def _build_connection_pool() -> ConnectionPool:
    if not settings.redis_url:
        raise RuntimeError("未配置 REDIS_URL，无法使用 Redis 缓存。")

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
