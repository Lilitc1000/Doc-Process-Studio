"""conftest 测试库自动创建护栏（AUTO_CREATE_HOSTS）的单元测试。

只测纯函数判定逻辑；真实的"连维护库建库"流程由本地真实数据库测试覆盖
（删掉 dps_test 后直接跑 pytest -m db 即可验证）。

conftest.py 不是可导入包的一部分，这里按路径用 importlib 加载。
"""

import importlib.util
from pathlib import Path
from typing import Any

import pytest

_TESTS_DIR = Path(__file__).resolve().parents[2]


def _load_conftest() -> Any:
    spec = importlib.util.spec_from_file_location("conftest_under_test", _TESTS_DIR / "conftest.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def conftest() -> Any:
    return _load_conftest()


def test_local_dev_hosts_are_allowed(conftest: Any) -> None:
    assert conftest._dsn_allows_auto_create("postgresql+asyncpg://admin:pw@db:5432/dps_test")
    assert conftest._dsn_allows_auto_create("postgresql://admin:pw@localhost:5432/dps_test")
    assert conftest._dsn_allows_auto_create("postgresql://admin:pw@127.0.0.1:5432/dps_test")
    assert conftest._dsn_allows_auto_create("postgresql://admin:pw@DB:5432/dps_test")  # 大小写不敏感


def test_remote_hosts_are_rejected(conftest: Any) -> None:
    assert not conftest._dsn_allows_auto_create("postgresql://admin:pw@10.10.20.150:5432/dps_test")
    assert not conftest._dsn_allows_auto_create("postgresql://admin:pw@prod.example.com:5432/dps_test")


def test_dsn_without_host_is_rejected(conftest: Any) -> None:
    assert not conftest._dsn_allows_auto_create("postgresql:///dps_test")


def test_strip_async_dialect(conftest: Any) -> None:
    assert (
        conftest._strip_async_dialect("postgresql+asyncpg://admin:pw@db:5432/dps_test")
        == "postgresql://admin:pw@db:5432/dps_test"
    )
