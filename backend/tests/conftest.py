import pytest

import doc_process_studio.core.cache_client as _cache_module
from doc_process_studio.core.security import create_access_token


@pytest.fixture(autouse=True)
def _reset_cache_client():
    yield
    if _cache_module._redis_client is not None:
        _cache_module._redis_client = None
    if _cache_module._pool is not None:
        _cache_module._pool = None


@pytest.fixture(autouse=True)
def _dispose_async_engine():
    yield
    from doc_process_studio.core.database import engine

    try:
        import asyncio

        loop = asyncio.new_event_loop()
        loop.run_until_complete(engine.dispose())
        loop.close()
    except Exception:
        pass


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    yield
    from doc_process_studio.auth.router.auth import _auth_rate_windows, _RATE_LIMIT_WHITELIST

    _auth_rate_windows.clear()
    _RATE_LIMIT_WHITELIST.clear()


@pytest.fixture()
def auth_headers():
    token = create_access_token("usr_test_user", "testuser")
    return {"Authorization": f"Bearer {token}"}
