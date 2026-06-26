import contextlib

import pytest

import doc_process_studio.common.infrastructure.cache_client as _cache_module
from doc_process_studio.common.security.security import create_access_token


@pytest.fixture(autouse=True)
def _reset_cache_client():
    yield
    if _cache_module._redis_client is not None:
        _cache_module._redis_client = None
    if _cache_module._pool is not None:
        _cache_module._pool = None


@pytest.fixture(autouse=True)
async def _dispose_async_engine():
    yield
    from doc_process_studio.common.infrastructure.database import engine

    with contextlib.suppress(Exception):
        await engine.dispose()


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    yield
    from doc_process_studio.auth.router.auth import _RATE_LIMIT_WHITELIST, _auth_rate_windows

    _auth_rate_windows.clear()
    _RATE_LIMIT_WHITELIST.clear()


@pytest.fixture()
def auth_headers():
    token = create_access_token("usr_test_user", "testuser")
    return {"Authorization": f"Bearer {token}"}
