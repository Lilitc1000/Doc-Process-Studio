"""Redis 令牌黑名单实现。

实现 TokenBlacklist 端口，将 refresh_token 的 jti 写入 Redis 实现登出失效。
"""

from ...common.infrastructure.cache import get_redis_client
from ..application.ports import TokenBlacklist


def _build_token_blacklist_key(jti: str) -> str:
    return f"dps:token-blacklist:{jti}"


class RedisTokenBlacklist(TokenBlacklist):
    """基于 Redis 的令牌黑名单。"""

    async def is_blacklisted(self, jti: str) -> bool:
        redis_client = get_redis_client()
        return await redis_client.get(_build_token_blacklist_key(jti)) is not None

    async def add(self, jti: str, expire_seconds: int) -> None:
        redis_client = get_redis_client()
        await redis_client.set(
            _build_token_blacklist_key(jti),
            "1",
            ex=expire_seconds,
        )
