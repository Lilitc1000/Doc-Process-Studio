"""设置接口的行为契约测试（鉴权 / 管理员门禁 / 响应形状）。

用 fake 仓储 + fake provider 装配**真实**的 SettingsService 与真实路由，
只把"最外层的数据来源"换掉，从而覆盖到路由 → 服务 → 加解密这一整段真实逻辑。

契约提醒：**后端 API 一律 snake_case**，camelCase 只存在于前端（axios 拦截器
用 humps 转换）。所以这里的请求体与断言都用下划线命名。

（真实数据库到 SQL 段的行为由 ``tests/integration_db/test_settings_api_db.py`` 覆盖。
这里刻意不跨文件共享 fake，与仓库既有测试"每个文件自包含"的风格保持一致。）
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from doc_process_studio.auth.domain.roles import ROLE_ADMIN, ROLE_MEMBER
from doc_process_studio.auth.infrastructure.dependencies import get_user_repository
from doc_process_studio.common.security.secret_cipher import SecretCipher
from doc_process_studio.common.security.security import create_access_token
from doc_process_studio.settings.application.ports import (
    RagflowConnectionProbe,
    RagflowDatasetCatalog,
    RagflowDatasetInfo,
    StoredSecret,
)
from doc_process_studio.settings.application.settings_service import SettingsService
from doc_process_studio.settings.domain.values import SECRET_RAGFLOW_API_KEY, RagflowConfig, SecretSource
from doc_process_studio.settings.infrastructure.dependencies import get_settings_service
from doc_process_studio.settings.router.settings import router as settings_router

SAMPLE_API_KEY = "ragflow-testkey-0123456789abcdefghijklmnopqrstuvtkYQ"
MASK_PLACEHOLDER = "\u2022" * 8
TEST_BASE_URL = "http://ragflow.test:10108"


class FakeSecretRepository:
    def __init__(self) -> None:
        self.rows: dict[str, StoredSecret] = {}

    async def get(self, secret_key: str) -> StoredSecret | None:
        return self.rows.get(secret_key)

    async def upsert(self, *, secret_key: str, ciphertext: str, key_id: str, hint: str | None) -> StoredSecret:
        row = StoredSecret(
            secret_key=secret_key,
            ciphertext=ciphertext,
            key_id=key_id,
            hint=hint,
            updated_at=datetime.now(UTC),
        )
        self.rows[secret_key] = row
        return row

    async def delete(self, secret_key: str) -> bool:
        return self.rows.pop(secret_key, None) is not None


class FakeSettingRepository:
    def __init__(self) -> None:
        self.values: dict[str, Any] = {}

    async def get(self, setting_key: str) -> Any | None:
        return self.values.get(setting_key)

    async def set(self, setting_key: str, value: Any) -> None:
        self.values[setting_key] = value

    async def delete(self, setting_key: str) -> bool:
        return self.values.pop(setting_key, None) is not None


class FakeUserSettingsRepository:
    def __init__(self) -> None:
        self.stored: dict[str, dict[str, Any]] = {}

    async def get_preferences(self, user_id: str) -> dict[str, Any]:
        return dict(self.stored.get(user_id, {}))

    async def merge_preferences(self, user_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        current = dict(self.stored.get(user_id, {}))
        for key, value in patch.items():
            if isinstance(value, dict) and isinstance(current.get(key), dict):
                current[key] = {**current[key], **value}
            else:
                current[key] = value
        self.stored[user_id] = current
        return current


class FakeProvider:
    def __init__(self, config: RagflowConfig) -> None:
        self.config = config
        self.invalidate_calls = 0
        # 记下来，便于断言"消费方确实是按 scope='system' 取的"
        self.resolved_scopes: list[str] = []
        self.invalidated_scopes: list[str | None] = []

    async def resolve(self, *, scope: str = "system") -> RagflowConfig:
        self.resolved_scopes.append(scope)
        return self.config

    def invalidate(self, *, scope: str | None = None) -> None:
        self.invalidate_calls += 1
        self.invalidated_scopes.append(scope)


class FakeProbe(RagflowConnectionProbe):
    def __init__(self, result: tuple[bool, str, int]) -> None:
        self.result = result
        self.probed_configs: list[RagflowConfig] = []

    async def probe(self, config: RagflowConfig) -> tuple[bool, str, int]:
        self.probed_configs.append(config)
        return self.result


class FakeCatalog(RagflowDatasetCatalog):
    """知识库列表桩。"""

    def __init__(self, datasets: list[RagflowDatasetInfo] | None = None) -> None:
        self.datasets = datasets if datasets is not None else []
        self.calls = 0
        self.received_configs: list[RagflowConfig] = []

    async def list_datasets(self, config: RagflowConfig) -> list[RagflowDatasetInfo]:
        self.calls += 1
        self.received_configs.append(config)
        return list(self.datasets)


class _FakeUserRepo:
    """只实现 require_admin 用到的那一个方法。"""

    def __init__(self, role: str) -> None:
        self.role = role

    async def get_role(self, _user_id: str) -> str:
        return self.role


def _usable_config() -> RagflowConfig:
    return RagflowConfig(
        base_url=TEST_BASE_URL,
        api_key=SAMPLE_API_KEY,
        enabled=True,
        source=SecretSource.SYSTEM,
    )


def _build_service(
    *,
    probe_result: tuple[bool, str, int] = (True, "连接成功，可访问 3 个知识库", 3),
    config: RagflowConfig | None = None,
    catalog: FakeCatalog | None = None,
) -> SettingsService:
    return SettingsService(
        secret_repo=FakeSecretRepository(),  # type: ignore[arg-type]
        setting_repo=FakeSettingRepository(),  # type: ignore[arg-type]
        user_settings_repo=FakeUserSettingsRepository(),  # type: ignore[arg-type]
        cipher=SecretCipher(keys={"k1": os.urandom(32)}, active_key_id="k1"),
        config_provider=FakeProvider(config or _usable_config()),  # type: ignore[arg-type]
        connection_probe=FakeProbe(probe_result),
        dataset_catalog=catalog or FakeCatalog(),
    )


def _app(role: str, service: SettingsService | None = None) -> FastAPI:
    app = FastAPI()
    app.include_router(settings_router)
    app.dependency_overrides[get_settings_service] = lambda: service or _build_service()
    app.dependency_overrides[get_user_repository] = lambda: _FakeUserRepo(role)
    return app


def _headers(user_id: str = "usr_api_test") -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id, 'tester')}"}


# ------------------------------------------------------------------ 鉴权


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/settings"),
        ("put", "/api/settings/preferences"),
        ("put", "/api/settings/ragflow"),
        ("post", "/api/settings/ragflow/test"),
    ],
)
def test_all_endpoints_require_authentication(method: str, path: str) -> None:
    client = TestClient(_app(ROLE_ADMIN))
    response = client.request(method.upper(), path, json={})
    assert response.status_code in (401, 403)


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("put", "/api/settings/ragflow"),
        ("post", "/api/settings/ragflow/test"),
        ("put", f"/api/settings/secrets/{SECRET_RAGFLOW_API_KEY}"),
        ("delete", f"/api/settings/secrets/{SECRET_RAGFLOW_API_KEY}"),
    ],
)
def test_system_endpoints_reject_non_admin(method: str, path: str) -> None:
    """系统级共享设置必须挡住普通用户 —— 改错一个 Base URL 就能让全系统检索失效。"""
    client = TestClient(_app(ROLE_MEMBER))
    response = client.request(method.upper(), path, json={}, headers=_headers())
    assert response.status_code == 403
    assert "管理员" in response.json()["detail"]


def test_personal_endpoints_allow_member() -> None:
    client = TestClient(_app(ROLE_MEMBER))
    assert client.get("/api/settings", headers=_headers()).status_code == 200
    assert client.put("/api/settings/preferences", json={}, headers=_headers()).status_code == 200


@pytest.mark.parametrize("role", ["", "viewer", "operator", "Admin ", "root"])
def test_unknown_role_fails_closed(role: str) -> None:
    """未知角色一律视为非管理员（fail closed），不给"猜个角色名就提权"的机会。"""
    client = TestClient(_app(role))
    assert client.put("/api/settings/ragflow", json={}, headers=_headers()).status_code == 403


# ------------------------------------------------------------------ 正常返回


def test_read_settings_shape() -> None:
    client = TestClient(_app(ROLE_ADMIN))
    body = client.get("/api/settings", headers=_headers()).json()

    assert set(body) == {"preferences", "ragflow"}
    assert body["preferences"]["models"] == {"selected": None, "reranker": None}

    ragflow = body["ragflow"]
    assert ragflow["base_url"] == TEST_BASE_URL
    assert ragflow["base_url_source"] == "default"
    assert ragflow["enabled"] is True
    assert ragflow["enabled_source"] == "default"
    assert ragflow["similarity_threshold"] > 0
    assert ragflow["top_k"] >= 1
    # 密钥状态不再挂在 ragflow 段上，改由 /api/settings/secrets 提供


def test_read_endpoint_never_returns_plaintext_even_if_configured() -> None:
    """服务端确实持有明文（provider 返回了它），但接口一个字符都不许吐出。"""
    client = TestClient(_app(ROLE_ADMIN))
    response = client.get("/api/settings", headers=_headers())
    assert response.status_code == 200
    assert SAMPLE_API_KEY not in response.text
    assert SAMPLE_API_KEY[:8] not in response.text


def test_member_overview_omits_system_section() -> None:
    """普通用户的 /api/settings 不含 ragflow 段。

    该段包含 Base URL、启用状态与密钥掩码/尾串 —— 系统级共享配置的元信息，
    没有理由给所有登录账号看。而普通用户**使用** RAGFlow 检索走的是服务端链路
    （对话工具、报告生成各自向 provider 现取），与本接口无关，所以剥掉不影响功能。
    """
    client = TestClient(_app(ROLE_MEMBER))
    response = client.get("/api/settings", headers=_headers())
    assert response.status_code == 200

    body = response.json()
    assert set(body) == {"preferences", "ragflow"}
    assert body["ragflow"] is None
    # 系统段的任何痕迹都不许漏出来
    assert "masked_api_key" not in response.text
    assert "base_url" not in response.text
    assert TEST_BASE_URL not in response.text


def test_member_overview_omits_system_section_even_when_configured() -> None:
    """即使系统级密钥已配好，普通用户也拿不到掩码与尾串。"""
    service = _build_service()
    admin_client = TestClient(_app(ROLE_ADMIN, service))
    admin_client.put(
        "/api/settings/ragflow",
        json={"base_url": TEST_BASE_URL, "enabled": True},
        headers=_headers(),
    )
    admin_client.put(
        f"/api/settings/secrets/{SECRET_RAGFLOW_API_KEY}",
        json={"value": SAMPLE_API_KEY},
        headers=_headers(),
    )

    response = TestClient(_app(ROLE_MEMBER, service)).get("/api/settings", headers=_headers())
    assert response.json()["ragflow"] is None
    assert SAMPLE_API_KEY[-4:] not in response.text


def test_save_secret_then_read_back_is_masked() -> None:
    service = _build_service()
    client = TestClient(_app(ROLE_ADMIN, service))

    saved = client.put(
        f"/api/settings/secrets/{SECRET_RAGFLOW_API_KEY}",
        json={"value": SAMPLE_API_KEY},
        headers=_headers(),
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["configured"] is True
    assert saved.json()["masked_value"] == f"{MASK_PLACEHOLDER}{SAMPLE_API_KEY[-4:]}"
    # 关键：整个响应体里不得出现明文
    assert SAMPLE_API_KEY not in saved.text

    reread = client.get("/api/settings/secrets", headers=_headers())
    secret = next(s for s in reread.json()["secrets"] if s["key"] == SECRET_RAGFLOW_API_KEY)
    assert secret["masked_value"].endswith(SAMPLE_API_KEY[-4:])
    assert SAMPLE_API_KEY not in reread.text


def test_saved_secret_is_stored_encrypted_not_plain() -> None:
    """直接看内部存储，确认落库的是密文而不是明文。"""
    secrets = FakeSecretRepository()
    service = SettingsService(
        secret_repo=secrets,  # type: ignore[arg-type]
        setting_repo=FakeSettingRepository(),  # type: ignore[arg-type]
        user_settings_repo=FakeUserSettingsRepository(),  # type: ignore[arg-type]
        cipher=SecretCipher(keys={"k1": os.urandom(32)}, active_key_id="k1"),
        config_provider=FakeProvider(_usable_config()),  # type: ignore[arg-type]
        connection_probe=FakeProbe((True, "ok", 0)),
        dataset_catalog=FakeCatalog(),
    )
    TestClient(_app(ROLE_ADMIN, service)).put(
        f"/api/settings/secrets/{SECRET_RAGFLOW_API_KEY}", json={"value": SAMPLE_API_KEY}, headers=_headers()
    )

    stored = secrets.rows[SECRET_RAGFLOW_API_KEY]
    assert stored.ciphertext.startswith("v1:k1:")
    assert SAMPLE_API_KEY not in stored.ciphertext
    assert stored.hint == SAMPLE_API_KEY[-4:]


def test_empty_secret_is_rejected_and_does_not_wipe_saved_key() -> None:
    service = _build_service()
    client = TestClient(_app(ROLE_ADMIN, service))
    client.put(f"/api/settings/secrets/{SECRET_RAGFLOW_API_KEY}", json={"value": SAMPLE_API_KEY}, headers=_headers())

    # 空串必须被拒绝（schema 层 min_length=1），且不能把已保存的密钥清掉
    response = client.put(f"/api/settings/secrets/{SECRET_RAGFLOW_API_KEY}", json={"value": ""}, headers=_headers())
    assert response.status_code == 422

    reread = client.get("/api/settings/secrets", headers=_headers())
    secret = next(s for s in reread.json()["secrets"] if s["key"] == SECRET_RAGFLOW_API_KEY)
    assert secret["configured"] is True


def test_clear_secret_endpoint() -> None:
    service = _build_service()
    client = TestClient(_app(ROLE_ADMIN, service))
    client.put(f"/api/settings/secrets/{SECRET_RAGFLOW_API_KEY}", json={"value": SAMPLE_API_KEY}, headers=_headers())

    response = client.delete(f"/api/settings/secrets/{SECRET_RAGFLOW_API_KEY}", headers=_headers())
    assert response.status_code == 200
    assert response.json()["configured"] is False


@pytest.mark.parametrize("bad_url", ["ftp://nope:21", "file:///etc/passwd", "not-a-url"])
def test_invalid_base_url_returns_400(bad_url: str) -> None:
    client = TestClient(_app(ROLE_ADMIN))
    response = client.put("/api/settings/ragflow", json={"base_url": bad_url}, headers=_headers())
    assert response.status_code == 400
    assert "http" in response.json()["detail"] or "主机" in response.json()["detail"]


def test_oversized_base_url_rejected_at_schema_level() -> None:
    """超长串由请求模型的 max_length 拦下（422），不会打到服务层。"""
    client = TestClient(_app(ROLE_ADMIN))
    response = client.put("/api/settings/ragflow", json={"base_url": "http://" + "a" * 600}, headers=_headers())
    assert response.status_code == 422


def test_connection_test_reflects_probe_result() -> None:
    ok_client = TestClient(_app(ROLE_ADMIN, _build_service()))
    ok_body = ok_client.post("/api/settings/ragflow/test", headers=_headers()).json()
    assert ok_body["ok"] is True
    assert ok_body["dataset_count"] == 3
    assert "连接成功" in ok_body["message"]

    bad_client = TestClient(
        _app(ROLE_ADMIN, _build_service(probe_result=(False, "RAGFlow 返回 code=109：unauthorized", 0)))
    )
    bad_body = bad_client.post("/api/settings/ragflow/test", headers=_headers()).json()
    assert bad_body["ok"] is False
    assert "code=109" in bad_body["message"]


def test_connection_test_skipped_when_disabled_or_unconfigured() -> None:
    disabled = _build_service(config=RagflowConfig(base_url="", api_key="", enabled=False, source=SecretSource.NONE))
    body = TestClient(_app(ROLE_ADMIN, disabled)).post("/api/settings/ragflow/test", headers=_headers()).json()
    assert body["ok"] is False
    assert "停用" in body["message"]

    unconfigured = _build_service(
        config=RagflowConfig(base_url=TEST_BASE_URL, api_key="", enabled=True, source=SecretSource.NONE)
    )
    body = TestClient(_app(ROLE_ADMIN, unconfigured)).post("/api/settings/ragflow/test", headers=_headers()).json()
    assert body["ok"] is False
    assert "尚未配置" in body["message"]


# ------------------------------------------------------------------ 用户偏好


def test_preferences_partial_update() -> None:
    service = _build_service()
    client = TestClient(_app(ROLE_ADMIN, service))
    headers = _headers()

    first = client.put(
        "/api/settings/preferences",
        json={"models": {"selected": "qwen3:8b", "reranker": "qwen3:32b"}},
        headers=headers,
    ).json()
    assert first["models"] == {"selected": "qwen3:8b", "reranker": "qwen3:32b"}

    second = client.put(
        "/api/settings/preferences",
        json={"models": {"selected": "qwen3-coder:30b"}},
        headers=headers,
    ).json()
    assert second["models"] == {"selected": "qwen3-coder:30b", "reranker": "qwen3:32b"}


def test_preferences_blank_clears_field() -> None:
    service = _build_service()
    client = TestClient(_app(ROLE_ADMIN, service))
    headers = _headers()
    client.put("/api/settings/preferences", json={"models": {"selected": "qwen3:8b"}}, headers=headers)

    body = client.put("/api/settings/preferences", json={"models": {"selected": ""}}, headers=headers).json()
    assert body["models"]["selected"] is None


def test_member_can_save_own_preferences_but_not_system_settings() -> None:
    """同一个人：个人偏好能改，系统设置不能改。"""
    service = _build_service()
    client = TestClient(_app(ROLE_MEMBER, service))
    headers = _headers()

    assert (
        client.put("/api/settings/preferences", json={"models": {"selected": "qwen3:8b"}}, headers=headers).status_code
        == 200
    )
    assert client.put("/api/settings/ragflow", json={"base_url": TEST_BASE_URL}, headers=headers).status_code == 403


# ------------------------------------------------------------------ 知识库列表


def test_admin_can_list_datasets_from_current_connection() -> None:
    """管理员能拿到当前连接下的知识库列表（设置页据此渲染选择项）。"""
    catalog = FakeCatalog(
        [
            RagflowDatasetInfo(
                id="f05e5a4aadac11f1b9211b18c23af0c8",
                name="DAS事故报告",
                document_count=11,
                chunk_count=27,
                language="English",
            )
        ]
    )
    client = TestClient(_app(ROLE_ADMIN, _build_service(catalog=catalog)))

    response = client.get("/api/settings/ragflow/datasets", headers=_headers())

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert catalog.calls == 1
    assert body["datasets"] == [
        {
            "id": "f05e5a4aadac11f1b9211b18c23af0c8",
            "name": "DAS事故报告",
            "document_count": 11,
            "chunk_count": 27,
        }
    ]


def test_dataset_list_requires_admin() -> None:
    """知识库列表会暴露连接的可用范围，非管理员一律拒绝。"""
    response = TestClient(_app(ROLE_MEMBER)).get("/api/settings/ragflow/datasets", headers=_headers())
    assert response.status_code == 403


# ------------------------------------------------------------------ 通用系统密钥


def test_list_system_secrets_endpoint_admin_only() -> None:
    """系统级密钥清单只能管理员看（含掩码尾串，普通用户不应拿到）。"""
    client = TestClient(_app(ROLE_MEMBER))
    assert client.get("/api/settings/secrets", headers=_headers()).status_code == 403
    admin_client = TestClient(_app(ROLE_ADMIN))
    resp = admin_client.get("/api/settings/secrets", headers=_headers())
    assert resp.status_code == 200
    keys = [s["key"] for s in resp.json()["secrets"]]
    assert SECRET_RAGFLOW_API_KEY in keys


def test_set_system_secret_endpoint_roundtrip() -> None:
    service = _build_service()
    client = TestClient(_app(ROLE_ADMIN, service))
    set_resp = client.put(
        f"/api/settings/secrets/{SECRET_RAGFLOW_API_KEY}",
        json={"value": SAMPLE_API_KEY},
        headers=_headers(),
    )
    assert set_resp.status_code == 200, set_resp.text
    body = set_resp.json()
    assert body["configured"] is True
    assert body["masked_value"].endswith(SAMPLE_API_KEY[-4:])
    # 全链路不得回显明文
    assert SAMPLE_API_KEY not in set_resp.text
    list_resp = client.get("/api/settings/secrets", headers=_headers())
    assert SAMPLE_API_KEY not in list_resp.text


def test_set_system_secret_unknown_key_400() -> None:
    client = TestClient(_app(ROLE_ADMIN))
    resp = client.put("/api/settings/secrets/does.not.exist", json={"value": "x"}, headers=_headers())
    assert resp.status_code == 400


def test_set_system_secret_rejects_non_admin() -> None:
    client = TestClient(_app(ROLE_MEMBER))
    resp = client.put(
        f"/api/settings/secrets/{SECRET_RAGFLOW_API_KEY}",
        json={"value": SAMPLE_API_KEY},
        headers=_headers(),
    )
    assert resp.status_code == 403


def test_clear_system_secret_endpoint() -> None:
    service = _build_service()
    client = TestClient(_app(ROLE_ADMIN, service))
    client.put(
        f"/api/settings/secrets/{SECRET_RAGFLOW_API_KEY}",
        json={"value": SAMPLE_API_KEY},
        headers=_headers(),
    )
    clear = client.delete(f"/api/settings/secrets/{SECRET_RAGFLOW_API_KEY}", headers=_headers())
    assert clear.status_code == 200
    assert clear.json()["configured"] is False
