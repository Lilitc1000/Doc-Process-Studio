import pytest

import doc_process_studio.core.db as _db_module


@pytest.fixture(autouse=True)
def _reset_redis_global():
    yield
    if _db_module._redis_client is not None:
        _db_module._redis_client = None
    if _db_module._pool is not None:
        _db_module._pool = None
