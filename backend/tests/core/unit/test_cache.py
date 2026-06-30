from typing import Any

import pytest

import doc_process_studio.common.infrastructure.cache as cache_module
from doc_process_studio.common.infrastructure.cache import (
    build_cache_key,
    delete_key,
    get_json,
    get_ttl_seconds,
    ping_redis,
    refresh_ttl,
    set_json,
)


class _FakeRedis:
    def __init__(self) -> None:
        self._store: dict[str, Any] = {}

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def set(self, key: str, value: str, **_kwargs: Any) -> None:
        self._store[key] = value

    async def ping(self) -> bool:
        return True

    async def delete(self, *keys: str) -> int:
        count = 0
        for k in keys:
            if k in self._store:
                del self._store[k]
                count += 1
        return count

    async def ttl(self, _key: Any) -> Any:
        return -1

    async def expire(self, _key: Any, _seconds: Any) -> bool:
        return True


def test_build_cache_key_joins_parts() -> None:
    result = build_cache_key("agent-trace", "tenant-1", "trace-abc")
    assert "agent-trace" in result
    assert "tenant-1" in result
    assert "trace-abc" in result


def test_build_cache_key_strips_empty_parts() -> None:
    result = build_cache_key("a", "  ", "b")
    assert result.count(":") == 2


async def test_get_json_returns_none_for_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeRedis()
    monkeypatch.setattr(cache_module, "get_redis_client", lambda: fake)
    result = await get_json("missing")
    assert result is None


async def test_get_json_parses_stored_json(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeRedis()
    fake._store["key1"] = '{"name": "test"}'
    monkeypatch.setattr(cache_module, "get_redis_client", lambda: fake)
    result = await get_json("key1")
    assert result == {"name": "test"}


async def test_set_json_stores_serialized(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeRedis()
    monkeypatch.setattr(cache_module, "get_redis_client", lambda: fake)
    await set_json("key1", {"a": 1})
    assert fake._store["key1"] == '{"a": 1}'


async def test_set_json_with_ttl(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeRedis()
    monkeypatch.setattr(cache_module, "get_redis_client", lambda: fake)
    await set_json("key1", {"a": 1}, ttl_seconds=60)
    assert "key1" in fake._store


async def test_ping_redis(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeRedis()
    monkeypatch.setattr(cache_module, "get_redis_client", lambda: fake)
    result = await ping_redis()
    assert result is True


async def test_delete_key(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeRedis()
    fake._store["key1"] = "val"
    monkeypatch.setattr(cache_module, "get_redis_client", lambda: fake)
    result = await delete_key("key1")
    assert result == 1


async def test_get_ttl_seconds(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeRedis()
    monkeypatch.setattr(cache_module, "get_redis_client", lambda: fake)
    result = await get_ttl_seconds("key1")
    assert isinstance(result, int)


async def test_refresh_ttl(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeRedis()
    monkeypatch.setattr(cache_module, "get_redis_client", lambda: fake)
    result = await refresh_ttl("key1")
    assert result is True


async def test_refresh_ttl_with_custom_seconds(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeRedis()
    monkeypatch.setattr(cache_module, "get_redis_client", lambda: fake)
    result = await refresh_ttl("key1", ttl_seconds=120)
    assert result is True
