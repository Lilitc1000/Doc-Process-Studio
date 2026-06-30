from __future__ import annotations

import contextlib
from collections.abc import AsyncGenerator, Generator

import pytest

import doc_process_studio.common.infrastructure.cache_client as _cache_module
from doc_process_studio.common.security.security import create_access_token


@pytest.fixture(autouse=True)
def _reset_cache_client() -> Generator[None]:
    yield
    if _cache_module._redis_client is not None:
        _cache_module._redis_client = None
    if _cache_module._pool is not None:
        _cache_module._pool = None


@pytest.fixture(autouse=True)
async def _dispose_async_engine() -> AsyncGenerator[None]:
    yield
    from doc_process_studio.common.infrastructure.database import engine

    with contextlib.suppress(Exception):
        await engine.dispose()


@pytest.fixture(autouse=True)
def _reset_rate_limiter() -> Generator[None]:
    yield
    from doc_process_studio.auth.router.auth import _RATE_LIMIT_WHITELIST, _auth_rate_windows

    _auth_rate_windows.clear()
    _RATE_LIMIT_WHITELIST.clear()


@pytest.fixture()
def auth_headers() -> dict[str, str]:
    token = create_access_token("usr_test_user", "testuser")
    return {"Authorization": f"Bearer {token}"}
