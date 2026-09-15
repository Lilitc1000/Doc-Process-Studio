"""真实数据库集成测试的共享夹具（只对 tests/integration_db 生效）。

与 tests/persistence 的区别：

* ``tests/persistence`` 直接调用仓储，验证 ORM 映射与约束。
* ``tests/integration_db`` 走**完整链路**：HTTP → application service → 真实仓储 → PostgreSQL，
  验证的是「SQL 行为 + 业务流转」的一致性，例如列表过滤是否真的落到 WHERE、
  评论是否真被外键级联删除、状态流转是否真的写库写审计。

关于事件循环（关键）：
    这里**不使用** ``fastapi.testclient.TestClient``。TestClient 会在独立线程里再起一个
    事件循环执行路由，而数据库会话绑定在 pytest-asyncio 的 session loop 上，
    asyncpg 连接跨 loop 使用会直接报错。改用 ``httpx.AsyncClient(ASGITransport)``
    在当前 loop 内 await 请求，保证整条链路与事务会话同处一个 loop。
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Callable, Coroutine
from typing import Any

import pytest
import pytest_asyncio
from conftest import LOOP_SCOPE, bind_repositories_to_session
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from doc_process_studio.auth.infrastructure.persistence import User
from doc_process_studio.common.security.security import create_access_token
from doc_process_studio.incident_report.infrastructure.repositories.role_repository import (
    SqlRoleRepository,
)
from doc_process_studio.incident_report.router.reports import router as reports_router


@pytest.fixture(autouse=True)
def _bind_repositories_to_test_session(
    monkeypatch: pytest.MonkeyPatch,
    db_session: AsyncSession,
) -> None:
    """把所有仓储的 session 工厂指向当前用例的会话（自动生效）。"""
    bind_repositories_to_session(monkeypatch, db_session)


@pytest_asyncio.fixture(loop_scope=LOOP_SCOPE)
async def role_repository(db_session: AsyncSession) -> SqlRoleRepository:
    """灌入 RBAC 默认角色与权限（与生产启动时的 seed 行为一致）。"""
    del db_session
    repository = SqlRoleRepository()
    await repository.seed_rbac_data()
    return repository


@pytest_asyncio.fixture(loop_scope=LOOP_SCOPE)
async def app() -> FastAPI:
    """只挂报告路由，不 override 任何依赖——整条链路都是真实实现。"""
    application = FastAPI()
    application.include_router(reports_router)
    return application


@pytest_asyncio.fixture(loop_scope=LOOP_SCOPE)
async def api_client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    """与 app 处于同一事件循环的异步 HTTP 客户端。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://integration-db") as client:
        yield client


@pytest_asyncio.fixture(loop_scope=LOOP_SCOPE)
async def register_user(
    db_session: AsyncSession,
    role_repository: SqlRoleRepository,
) -> Callable[..., Coroutine[Any, Any, User]]:
    """创建用户并赋予角色（外键与权限检查都依赖真实的 users / RBAC 数据）。"""

    async def _make(username: str | None = None, role: str = "reporter") -> User:
        name = username or f"u_{uuid.uuid4().hex[:10]}"
        user = User(
            user_id=f"uid_{uuid.uuid4().hex[:10]}",
            username=name,
            hashed_password="not-a-real-password-hash",
            avatar_color="#4f46e5",
        )
        db_session.add(user)
        await db_session.commit()
        await role_repository.assign_role(
            user_id=user.user_id,
            role=role,
            assigned_by=user.user_id,
        )
        return user

    return _make


def auth_headers_for(user: User) -> dict[str, str]:
    """按真实登录流程换取 Bearer token。"""
    return {"Authorization": f"Bearer {create_access_token(user.user_id, user.username)}"}


async def count_rows(session: AsyncSession, model: type[Any], **filters: Any) -> int:
    """绕开业务代码直接数行，验证「真的写进表里了」。"""
    statement = select(func.count()).select_from(model).filter_by(**filters)
    result = await session.execute(statement)
    return int(result.scalar_one())


@pytest.fixture()
def token_headers() -> Callable[[User], dict[str, str]]:
    """把 auth_headers_for 暴露成夹具，避免测试文件跨模块导入 conftest。"""
    return auth_headers_for


@pytest.fixture()
def count_rows_helper() -> Callable[..., Coroutine[Any, Any, int]]:
    """把 count_rows 暴露成夹具。"""
    return count_rows
