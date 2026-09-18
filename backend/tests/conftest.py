"""全局测试夹具。

包含两类内容：

1. 通用的清理型 autouse 夹具（Redis 客户端、异步引擎、限流窗口）。
2. **数据库夹具**（``db_engine`` / ``db_session``）：供 ``tests/persistence`` 与
   ``tests/integration_db`` 共用。这里只定义夹具本身，不做 autouse 绑定，
   以免其余几百个纯 mock 用例被强制连数据库。

   隔离策略见 ``tests/DEVELOPMENT.md``：独立测试库 + session 级建表 +
   用例级事务回滚，保证零残留。
"""

from __future__ import annotations

import contextlib
import importlib
import os
import sys
from collections.abc import AsyncIterator, Generator
from types import ModuleType
from typing import Literal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

import doc_process_studio.common.infrastructure.cache_client as _cache_module
from doc_process_studio.common.infrastructure.config import settings
from doc_process_studio.common.infrastructure.database import Base
from doc_process_studio.common.security.security import create_access_token

TEST_DSN_ENV = "DPS_TEST_DATABASE_URL"

# 会话级 loop：所有 DB 夹具与用例必须共用同一个事件循环，
# 否则 asyncpg 连接会跨 loop 报错。用例侧用 pytestmark 声明相同 loop_scope。
LOOP_SCOPE: Literal["session"] = "session"

# create_all 依赖这些模块完成 ORM 元数据注册，缺一个就会漏建表
_ORM_MODULE_NAMES = (
    "doc_process_studio.auth.infrastructure.persistence",
    "doc_process_studio.chat.infrastructure.persistence",
    "doc_process_studio.incident_report.infrastructure.persistence",
    # settings 模块：system_settings / system_secrets / user_settings 三张表
    "doc_process_studio.settings.infrastructure.persistence",
)


def pytest_addoption(parser: pytest.Parser) -> None:
    """持久化测试的测试库 DSN：优先命令行，其次 DPS_TEST_DATABASE_URL。"""
    parser.addoption(
        "--db-dsn",
        action="store",
        default=None,
        help="真实数据库持久化测试的 DSN（等价于 DPS_TEST_DATABASE_URL）",
    )


def register_orm_metadata() -> None:
    """导入全部 ORM 模块，保证 Base.metadata 覆盖所有表。"""
    for name in _ORM_MODULE_NAMES:
        importlib.import_module(name)


def resolve_db_dsn(config: pytest.Config) -> tuple[str, bool]:
    """按 --db-dsn > 环境变量 > settings 的顺序解析测试库 DSN。

    返回 ``(dsn, explicit)``：前两种属于显式配置，连不上必须 fail；
    settings 兜底属于默认约定，连不上应当 skip，保证无数据库环境仍能全绿。
    """
    from_cli = str(config.getoption("--db-dsn") or "").strip()
    if from_cli:
        return from_cli, True

    from_env = os.getenv(TEST_DSN_ENV, "").strip()
    if from_env:
        return from_env, True

    return settings.test_database_url.strip(), False


class ReusedSession:
    """把既有 AsyncSession 包装成 ``async_session_factory()`` 的返回值。

    仓储代码写作 ``async with async_session_factory() as session``，
    这里复用同一个会话：进入时返回共享会话，退出时既不提交也不关闭，
    异常时回滚到 savepoint，保证后续语句仍可用。
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def __aenter__(self) -> AsyncSession:
        return self._session

    async def __aexit__(self, *exc_info: object) -> bool:
        if exc_info[1] is not None:
            await self._session.rollback()
        return False


def session_factory_modules() -> list[ModuleType]:
    """收集所有持有 async_session_factory 的模块（仓储直接引用了它）。"""
    return [
        module
        for module in list(sys.modules.values())
        if getattr(module, "__name__", "").startswith("doc_process_studio") and hasattr(module, "async_session_factory")
    ]


def bind_repositories_to_session(
    monkeypatch: pytest.MonkeyPatch,
    session: AsyncSession,
) -> None:
    """把所有仓储的 session 工厂指向给定会话。"""
    for module in session_factory_modules():
        monkeypatch.setattr(module, "async_session_factory", lambda: ReusedSession(session))


@pytest_asyncio.fixture(scope="session", loop_scope=LOOP_SCOPE)
async def db_engine(request: pytest.FixtureRequest) -> AsyncIterator[AsyncEngine]:
    """会话级引擎：建表一次，结束删表。"""
    dsn, explicit = resolve_db_dsn(request.config)
    if not dsn:
        pytest.skip(f"未设置 {TEST_DSN_ENV}（或 --db-dsn），跳过数据库测试")

    register_orm_metadata()
    engine = create_async_engine(dsn, poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
    except Exception as exc:  # noqa: BLE001
        await engine.dispose()
        # 显式配了 DSN 却连不上属于配置错误，必须显式暴露；
        # 走默认约定时则静默跳过，保证无数据库环境下 pytest 依旧全绿。
        if explicit:
            pytest.fail(f"测试数据库不可用（{dsn}）：{exc}", pytrace=False)
        pytest.skip(f"默认测试库不可用（{dsn}），跳过数据库测试：{exc}")

    try:
        yield engine
    finally:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
        await engine.dispose()


@pytest_asyncio.fixture(loop_scope=LOOP_SCOPE)
async def db_session(db_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """用例级会话：外层事务 + savepoint，结束必回滚。"""
    async with db_engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(
            bind=connection,
            join_transaction_mode="create_savepoint",
            expire_on_commit=False,
        )
        try:
            yield session
        finally:
            await session.close()
            if transaction.is_active:
                await transaction.rollback()


@pytest.fixture(autouse=True)
def _reset_cache_client() -> Generator[None]:
    yield
    if _cache_module._redis_client is not None:
        _cache_module._redis_client = None
    if _cache_module._pool is not None:
        _cache_module._pool = None


@pytest.fixture(autouse=True)
async def _dispose_async_engine() -> AsyncIterator[None]:
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
