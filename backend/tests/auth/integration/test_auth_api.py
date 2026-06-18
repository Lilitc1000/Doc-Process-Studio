from typing import Any

import pytest
from fastapi.testclient import TestClient

import doc_process_studio.main as main_module
from doc_process_studio.auth.domain.errors import (
    IncorrectPasswordError,
    InvalidCredentialsError,
    InvalidTokenError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from doc_process_studio.auth.infrastructure.dependencies import get_auth_service
from doc_process_studio.auth.schemas.response import (
    RegisterResponse,
    TokenResponse,
    UserInfoResponse,
)


class FakeAuthService:
    """测试用 AuthService 替身。"""

    def __init__(self) -> None:
        self.responses: dict[str, Any] = {}
        self.errors: dict[str, Exception] = {}
        self.calls: dict[str, list[Any]] = {}

    def _record(self, name: str, *args: Any) -> None:
        self.calls.setdefault(name, []).append(args)

    async def register(self, *, username: str, password: str) -> RegisterResponse:
        self._record("register", username, password)
        if exc := self.errors.get("register"):
            raise exc
        return self.responses["register"]

    async def authenticate(self, *, username: str, password: str) -> TokenResponse:
        self._record("authenticate", username, password)
        if exc := self.errors.get("authenticate"):
            raise exc
        return self.responses["authenticate"]

    async def refresh_token(self, refresh_token: str) -> TokenResponse:
        self._record("refresh_token", refresh_token)
        if exc := self.errors.get("refresh_token"):
            raise exc
        return self.responses["refresh_token"]

    async def get_current_user_info(self, user_id: str) -> UserInfoResponse:
        self._record("get_current_user_info", user_id)
        if exc := self.errors.get("get_current_user_info"):
            raise exc
        return self.responses["get_current_user_info"]

    async def update_profile(self, user_id: str, *, username: str | None = None, avatar_color: str | None = None):
        self._record("update_profile", user_id, username, avatar_color)
        if exc := self.errors.get("update_profile"):
            raise exc
        return self.responses["update_profile"]

    async def change_password(self, user_id: str, *, current_password: str, new_password: str) -> None:
        self._record("change_password", user_id, current_password, new_password)
        if exc := self.errors.get("change_password"):
            raise exc

    async def logout(self, *, refresh_token: str) -> None:
        self._record("logout", refresh_token)

    async def delete_user(self, user_id: str) -> bool:
        self._record("delete_user", user_id)
        if exc := self.errors.get("delete_user"):
            raise exc
        return self.responses.get("delete_user", True)

    async def delete_users_by_prefix(self, prefix: str) -> int:
        self._record("delete_users_by_prefix", prefix)
        return self.responses.get("delete_users_by_prefix", 0)

    async def ensure_admin_user(self, *, admin_username: str, admin_password: str) -> None:
        self._record("ensure_admin_user", admin_username, admin_password)


@pytest.fixture()
def fake_auth_service():
    service = FakeAuthService()
    main_module.app.dependency_overrides[get_auth_service] = lambda: service
    yield service
    main_module.app.dependency_overrides.pop(get_auth_service, None)


def test_api_auth_register_success(fake_auth_service: FakeAuthService) -> None:
    fake_auth_service.responses["register"] = RegisterResponse(
        user_id="usr_test123",
        username="newuser",
        created_at="2026-01-01T00:00:00Z",
    )

    client = TestClient(main_module.app)
    response = client.post(
        "/api/auth/register",
        json={"username": "newuser", "password": "password123"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == "usr_test123"
    assert data["username"] == "newuser"


def test_api_auth_register_duplicate_username(fake_auth_service: FakeAuthService) -> None:
    fake_auth_service.errors["register"] = UserAlreadyExistsError("Username already exists")

    client = TestClient(main_module.app)
    response = client.post(
        "/api/auth/register",
        json={"username": "duplicate", "password": "password123"},
    )

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_api_auth_login_success(fake_auth_service: FakeAuthService) -> None:
    fake_auth_service.responses["authenticate"] = TokenResponse(
        access_token="fake_access_token",
        refresh_token="fake_refresh_token",
        token_type="bearer",
    )

    client = TestClient(main_module.app)
    response = client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "admin123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["access_token"] == "fake_access_token"
    assert data["refresh_token"] == "fake_refresh_token"
    assert data["token_type"] == "bearer"


def test_api_auth_login_wrong_password(fake_auth_service: FakeAuthService) -> None:
    fake_auth_service.errors["authenticate"] = InvalidCredentialsError("Incorrect username or password")

    client = TestClient(main_module.app)
    response = client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "wrong"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == 401


def test_api_auth_refresh_success(fake_auth_service: FakeAuthService) -> None:
    fake_auth_service.responses["refresh_token"] = TokenResponse(
        access_token="new_access_token",
        refresh_token="new_refresh_token",
        token_type="bearer",
    )

    client = TestClient(main_module.app)
    response = client.post(
        "/api/auth/refresh",
        json={"refresh_token": "old_refresh_token"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["access_token"] == "new_access_token"


def test_api_auth_refresh_invalid_token(fake_auth_service: FakeAuthService) -> None:
    fake_auth_service.errors["refresh_token"] = InvalidTokenError("Invalid or expired refresh token")

    client = TestClient(main_module.app)
    response = client.post(
        "/api/auth/refresh",
        json={"refresh_token": "invalid_token"},
    )

    assert response.status_code == 401


def test_api_auth_me_with_valid_token(fake_auth_service: FakeAuthService, auth_headers) -> None:
    fake_auth_service.responses["get_current_user_info"] = UserInfoResponse(
        user_id="usr_test_user",
        username="testuser",
        avatar_color="#4f46e5",
        created_at="2026-01-01T00:00:00Z",
    )

    client = TestClient(main_module.app)
    response = client.get("/api/auth/me", headers=auth_headers)

    assert response.status_code == 200
    assert fake_auth_service.calls.get("get_current_user_info") == [("usr_test_user",)]


def test_api_auth_me_without_token() -> None:
    client = TestClient(main_module.app)
    response = client.get("/api/auth/me")

    assert response.status_code == 401


def test_api_protected_endpoint_without_token() -> None:
    client = TestClient(main_module.app)
    response = client.get("/api/models")

    assert response.status_code == 401


def test_api_auth_rate_limit(fake_auth_service: FakeAuthService) -> None:
    call_count = 0

    def make_response(username: str) -> RegisterResponse:
        nonlocal call_count
        call_count += 1
        return RegisterResponse(
            user_id=f"usr_{call_count}",
            username=username,
            created_at="2026-01-01T00:00:00Z",
        )

    fake_auth_service.responses["register"] = None

    async def fake_register(*, username: str, password: str) -> RegisterResponse:
        return make_response(username)

    fake_auth_service.register = fake_register  # type: ignore[method-assign]

    client = TestClient(main_module.app)

    for i in range(5):
        response = client.post(
            "/api/auth/register",
            json={"username": f"user_{i}", "password": "password123"},
        )
        assert response.status_code == 201

    response = client.post(
        "/api/auth/register",
        json={"username": "user_6", "password": "password123"},
    )
    assert response.status_code == 429


def test_api_auth_delete_own_account(fake_auth_service: FakeAuthService, auth_headers) -> None:
    fake_auth_service.responses["delete_user"] = True

    client = TestClient(main_module.app)
    response = client.delete("/api/auth/users/usr_test_user", headers=auth_headers)

    assert response.status_code == 200
    assert fake_auth_service.calls.get("delete_user") == [("usr_test_user",)]


def test_api_auth_delete_other_account_forbidden(auth_headers) -> None:
    client = TestClient(main_module.app)
    response = client.delete("/api/auth/users/usr_other_user", headers=auth_headers)

    assert response.status_code == 403


def test_api_auth_delete_user_not_found(fake_auth_service: FakeAuthService, auth_headers) -> None:
    fake_auth_service.errors["delete_user"] = UserNotFoundError("User not found")

    client = TestClient(main_module.app)
    response = client.delete("/api/auth/users/usr_test_user", headers=auth_headers)

    assert response.status_code == 404


def test_api_auth_change_password_incorrect(fake_auth_service: FakeAuthService, auth_headers) -> None:
    fake_auth_service.errors["change_password"] = IncorrectPasswordError("Current password is incorrect")

    client = TestClient(main_module.app)
    response = client.put(
        "/api/auth/password",
        json={"current_password": "wrong", "new_password": "newpass"},
        headers=auth_headers,
    )

    assert response.status_code == 400
