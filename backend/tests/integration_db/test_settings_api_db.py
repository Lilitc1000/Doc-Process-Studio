"""设置接口 → 真实仓储 → PostgreSQL 的完整链路集成测试。

覆盖 mock 仓储**永远测不到**的行为：

- 密钥落库的**真实形态**（是不是密文、hint 对不对）
- 用户级偏好的**真实隔离**（按 user_id 落库，A 改不影响 B）
- ``users`` 删除后 ``user_settings`` 是否真被外键级联清掉
- 管理员门禁走**真实 users.role** 判定时的 200 / 403

每个用例跑在外层事务里，结束回滚，不留数据。
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Iterator

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from doc_process_studio.auth.domain.roles import ROLE_ADMIN, ROLE_MEMBER
from doc_process_studio.auth.infrastructure.persistence import User
from doc_process_studio.common.security.security import create_access_token
from doc_process_studio.settings.domain.values import (
    SECRET_RAGFLOW_API_KEY,
    SETTING_RAGFLOW_BASE_URL,
    SETTING_RAGFLOW_ENABLED,
)
from doc_process_studio.settings.infrastructure import dependencies as settings_deps
from doc_process_studio.settings.infrastructure.persistence.models import SystemSecret, SystemSetting, UserSettings
from doc_process_studio.settings.router.settings import router as settings_router

pytestmark = [pytest.mark.db, pytest.mark.asyncio(loop_scope="session")]

SAMPLE_API_KEY = "ragflow-testkey-0123456789abcdefghijklmnopqrstuvtkYQ"
MASK_PLACEHOLDER = "\u2022" * 8


@pytest.fixture(autouse=True)
def _reset_settings_singletons() -> Iterator[None]:
    """清掉 settings 模块的 lru_cache 单例。

    provider 内部带解析缓存与失效 epoch，跨用例复用会把上一个用例的配置带过来。
    """
    for factory in (
        settings_deps.get_settings_service,
        settings_deps.get_ragflow_config_provider,
        settings_deps.get_ragflow_connection_probe,
        settings_deps.get_system_secret_repository,
        settings_deps.get_system_setting_repository,
        settings_deps.get_user_settings_repository,
    ):
        factory.cache_clear()
    yield
    for factory in (
        settings_deps.get_settings_service,
        settings_deps.get_ragflow_config_provider,
        settings_deps.get_ragflow_connection_probe,
        settings_deps.get_system_secret_repository,
        settings_deps.get_system_setting_repository,
        settings_deps.get_user_settings_repository,
    ):
        factory.cache_clear()


@pytest.fixture()
def app() -> FastAPI:
    """只挂设置路由，不 override 任何依赖 —— 整条链路都是真实实现。"""
    application = FastAPI()
    application.include_router(settings_router)
    return application


@pytest.fixture()
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    from httpx import ASGITransport

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://integration-db") as http_client:
        yield http_client


async def _make_user(session: AsyncSession, role: str) -> User:
    user = User(
        user_id=f"usr_{uuid.uuid4().hex[:12]}",
        username=f"u_{uuid.uuid4().hex[:8]}",
        hashed_password="not-a-real-hash",
        avatar_color="#4f46e5",
        role=role,
    )
    session.add(user)
    await session.commit()
    return user


def _headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.user_id, user.username)}"}


# ------------------------------------------------------------------ 加解密落库形态


async def test_saved_api_key_is_ciphertext_in_database(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    admin = await _make_user(db_session, ROLE_ADMIN)

    response = await client.put(
        "/api/settings/ragflow",
        json={"base_url": "http://db-test-host:10108", "enabled": True},
        headers=_headers(admin),
    )
    assert response.status_code == 200

    secret_resp = await client.put(
        f"/api/settings/secrets/{SECRET_RAGFLOW_API_KEY}",
        json={"value": SAMPLE_API_KEY},
        headers=_headers(admin),
    )
    assert secret_resp.status_code == 200
    assert SAMPLE_API_KEY not in secret_resp.text

    row = (
        await db_session.execute(select(SystemSecret).where(SystemSecret.secret_key == SECRET_RAGFLOW_API_KEY))
    ).scalar_one()
    assert row.ciphertext.startswith("v1:")
    assert SAMPLE_API_KEY not in row.ciphertext
    assert row.key_id
    assert row.hint == SAMPLE_API_KEY[-4:]

    setting_keys = (await db_session.execute(select(SystemSetting.setting_key))).scalars().all()
    assert SETTING_RAGFLOW_BASE_URL in setting_keys
    assert SETTING_RAGFLOW_ENABLED in setting_keys


async def test_read_back_is_masked_and_reports_system_source(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    admin = await _make_user(db_session, ROLE_ADMIN)
    headers = _headers(admin)
    await client.put(
        "/api/settings/ragflow",
        json={"base_url": "http://db-test-host:10108", "enabled": True},
        headers=headers,
    )
    await client.put(
        f"/api/settings/secrets/{SECRET_RAGFLOW_API_KEY}",
        json={"value": SAMPLE_API_KEY},
        headers=headers,
    )

    body = (await client.get("/api/settings", headers=headers)).json()
    ragflow = body["ragflow"]
    assert ragflow["base_url"] == "http://db-test-host:10108"
    assert ragflow["base_url_source"] == "system"
    assert ragflow["enabled_source"] == "system"

    secrets_body = (await client.get("/api/settings/secrets", headers=headers)).json()
    secret = next(s for s in secrets_body["secrets"] if s["key"] == SECRET_RAGFLOW_API_KEY)
    assert secret["configured"] is True
    assert secret["masked_value"] == f"{MASK_PLACEHOLDER}{SAMPLE_API_KEY[-4:]}"
    assert secret["source"] == "system"


async def test_provider_resolves_saved_key_for_consumers(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """这是本次改造的核心承诺：写入后**同一进程内立即**能被消费方读到，无需重启。"""
    admin = await _make_user(db_session, ROLE_ADMIN)
    await client.put(
        f"/api/settings/secrets/{SECRET_RAGFLOW_API_KEY}",
        json={"value": SAMPLE_API_KEY},
        headers=_headers(admin),
    )
    await client.put(
        "/api/settings/ragflow",
        json={"enabled": True},
        headers=_headers(admin),
    )

    config = await settings_deps.get_ragflow_config_provider().resolve(scope="system")
    assert config.api_key == SAMPLE_API_KEY
    assert config.enabled is True
    assert config.source.value == "system"


async def test_clear_api_key_removes_database_row(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    admin = await _make_user(db_session, ROLE_ADMIN)
    headers = _headers(admin)
    await client.put(f"/api/settings/secrets/{SECRET_RAGFLOW_API_KEY}", json={"value": SAMPLE_API_KEY}, headers=headers)

    response = await client.delete(f"/api/settings/secrets/{SECRET_RAGFLOW_API_KEY}", headers=headers)
    assert response.status_code == 200
    assert response.json()["configured"] is False

    remaining = (
        await db_session.execute(select(SystemSecret).where(SystemSecret.secret_key == SECRET_RAGFLOW_API_KEY))
    ).scalar_one_or_none()
    assert remaining is None


# ------------------------------------------------------------------ 管理员门禁（真实 role）


async def test_member_is_rejected_by_real_role_check(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    member = await _make_user(db_session, ROLE_MEMBER)
    response = await client.put(
        "/api/settings/ragflow",
        json={"base_url": "http://db-member-reject:10108"},
        headers=_headers(member),
    )
    assert response.status_code == 403

    assert (
        await db_session.execute(select(SystemSecret).where(SystemSecret.secret_key == SECRET_RAGFLOW_API_KEY))
    ).scalar_one_or_none() is None


async def test_member_can_still_use_personal_settings(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    member = await _make_user(db_session, ROLE_MEMBER)
    response = await client.put(
        "/api/settings/preferences",
        json={"models": {"selected": "qwen3:8b"}},
        headers=_headers(member),
    )
    assert response.status_code == 200
    assert response.json()["models"]["selected"] == "qwen3:8b"


async def test_member_overview_omits_system_section(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """真实角色校验下：普通用户的 /api/settings 不含 ragflow 段，也不含密钥尾串。"""
    admin = await _make_user(db_session, ROLE_ADMIN)
    await client.put(
        "/api/settings/ragflow",
        json={"base_url": "http://db-member-test:10108", "enabled": True},
        headers=_headers(admin),
    )
    await client.put(
        f"/api/settings/secrets/{SECRET_RAGFLOW_API_KEY}",
        json={"value": SAMPLE_API_KEY},
        headers=_headers(admin),
    )

    member = await _make_user(db_session, ROLE_MEMBER)
    response = await client.get("/api/settings", headers=_headers(member))

    assert response.status_code == 200
    assert response.json()["ragflow"] is None
    assert response.json()["preferences"]["models"] == {"selected": None, "reranker": None}
    assert SAMPLE_API_KEY[-4:] not in response.text
    assert "db-member-test" not in response.text


# ------------------------------------------------------------------ 用户级隔离


async def test_preferences_are_isolated_per_user(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    user_a = await _make_user(db_session, ROLE_MEMBER)
    user_b = await _make_user(db_session, ROLE_MEMBER)

    await client.put(
        "/api/settings/preferences",
        json={"models": {"selected": "model-for-a", "reranker": "rr-a"}},
        headers=_headers(user_a),
    )
    await client.put(
        "/api/settings/preferences",
        json={"models": {"selected": "model-for-b"}},
        headers=_headers(user_b),
    )

    body_a = (await client.get("/api/settings", headers=_headers(user_a))).json()
    body_b = (await client.get("/api/settings", headers=_headers(user_b))).json()

    assert body_a["preferences"]["models"] == {"selected": "model-for-a", "reranker": "rr-a"}
    assert body_b["preferences"]["models"] == {"selected": "model-for-b", "reranker": None}

    rows = (await db_session.execute(select(UserSettings))).scalars().all()
    by_user = {row.user_id: row for row in rows}
    assert by_user[user_a.user_id].preferences["models"]["selected"] == "model-for-a"
    assert by_user[user_b.user_id].preferences["models"]["selected"] == "model-for-b"
    assert by_user[user_a.user_id].version >= 1


async def test_preferences_version_increments_on_write(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    user = await _make_user(db_session, ROLE_MEMBER)
    headers = _headers(user)
    for index in range(3):
        await client.put(
            "/api/settings/preferences",
            json={"models": {"selected": f"m{index}"}},
            headers=headers,
        )

    row = (await db_session.execute(select(UserSettings).where(UserSettings.user_id == user.user_id))).scalar_one()
    assert row.version == 3


async def test_deleting_user_cascades_settings(
    db_session: AsyncSession,
) -> None:
    """用户被删后偏好不该变成孤儿行。"""
    user = await _make_user(db_session, ROLE_MEMBER)
    db_session.add(UserSettings(user_id=user.user_id, preferences={"models": {"selected": "x"}}, version=1))
    await db_session.commit()
    assert (
        await db_session.execute(select(UserSettings).where(UserSettings.user_id == user.user_id))
    ).scalar_one_or_none() is not None

    await db_session.execute(delete(User).where(User.user_id == user.user_id))
    await db_session.commit()

    assert (
        await db_session.execute(select(UserSettings).where(UserSettings.user_id == user.user_id))
    ).scalar_one_or_none() is None


async def test_reading_settings_creates_no_rows(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """纯读不该产生副作用（否则每次登录都给库里插垃圾）。"""
    user = await _make_user(db_session, ROLE_MEMBER)
    await client.get("/api/settings", headers=_headers(user))

    assert (
        await db_session.execute(select(UserSettings).where(UserSettings.user_id == user.user_id))
    ).scalar_one_or_none() is None
