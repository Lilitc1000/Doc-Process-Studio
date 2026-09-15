"""真实数据库持久化测试的共享夹具（只对 tests/persistence 生效）。

三重隔离，保证开发库与测试库都不会残留任何测试数据：

1. **独立库**：只连测试库（默认 ``dps_test``），与开发库 ``master`` 物理隔离。
   DSN 依次从 ``--db-dsn``、环境变量 ``DPS_TEST_DATABASE_URL``、``settings.test_database_url``
   解析；前两者缺失时走默认约定，连不上则整组 skip，普通 ``uv run pytest`` 在无数据库
   环境下依旧全绿（显式配置却连不上会 fail，避免"静默没跑到"）。
2. **建表一次**：session 级 engine，会话开始 ``create_all``、会话结束 ``drop_all``，
   不在每个用例里重复建表/删表。
3. **事务回滚**：每个用例跑在一个外层事务里，仓储内部的 ``commit()`` 只释放
   savepoint，用例结束一律 ``rollback``。因此任何情况下都不会有行真正落库，
   也不需要 truncate / 手工清理。

数据库夹具（``db_engine`` / ``db_session``）定义在 ``tests/conftest.py``；
仓储无侵入：项目内仓储直接引用模块级 ``async_session_factory``，
这里用 monkeypatch 把它换成「复用同一连接」的会话包装器，生产代码零改动。
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Coroutine
from typing import Any

import pytest
from conftest import bind_repositories_to_session
from sqlalchemy.ext.asyncio import AsyncSession

from doc_process_studio.auth.infrastructure.persistence import User
from doc_process_studio.incident_report.infrastructure.repositories import (
    SequentialRefNoGenerator,
    SqlAlchemyReportRepository,
    SqlUserDirectory,
)


@pytest.fixture(autouse=True)
def _bind_repositories_to_test_session(
    monkeypatch: pytest.MonkeyPatch,
    db_session: AsyncSession,
) -> None:
    """把所有仓储的 session 工厂指向当前用例的会话（自动生效）。"""
    bind_repositories_to_session(monkeypatch, db_session)


@pytest.fixture()
def user_factory(db_session: AsyncSession) -> Callable[..., Coroutine[Any, Any, User]]:
    """创建用户（报告外键依赖 users.user_id）。"""

    async def _make(username: str | None = None) -> User:
        name = username or f"u_{uuid.uuid4().hex[:10]}"
        user = User(
            user_id=f"uid_{uuid.uuid4().hex[:10]}",
            username=name,
            hashed_password="not-a-real-password-hash",
            avatar_color="#4f46e5",
        )
        db_session.add(user)
        await db_session.commit()
        return user

    return _make


@pytest.fixture()
def report_repository() -> SqlAlchemyReportRepository:
    """真实报告仓储（session 工厂已被 _bind_repositories_to_test_session 替换）。"""
    return SqlAlchemyReportRepository(
        user_dir=SqlUserDirectory(),
        ref_no_gen=SequentialRefNoGenerator(),
    )
