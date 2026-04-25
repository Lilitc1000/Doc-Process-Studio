import doc_process_studio.main as main_module
import doc_process_studio.auth.router.auth as auth_router_module
from doc_process_studio.auth.schemas.response import (
    RegisterResponse,
    TokenResponse,
    UserInfoResponse,
)
from doc_process_studio.core.security import create_access_token


def test_api_auth_register_success(monkeypatch) -> None:
    async def fake_register_user(username: str, password: str) -> RegisterResponse:
        return RegisterResponse(
            user_id="usr_test123",
            username=username,
            created_at="2026-01-01T00:00:00Z",
        )

    monkeypatch.setattr(auth_router_module, "register_user", fake_register_user)

    from fastapi.testclient import TestClient

    client = TestClient(main_module.app)
    response = client.post(
        "/api/auth/register",
        json={"username": "newuser", "password": "password123"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == "usr_test123"
    assert data["username"] == "newuser"


def test_api_auth_register_duplicate_username(monkeypatch) -> None:
    async def fake_register_user(username: str, password: str) -> RegisterResponse:
        raise ValueError("Username already exists")

    monkeypatch.setattr(auth_router_module, "register_user", fake_register_user)

    from fastapi.testclient import TestClient

    client = TestClient(main_module.app)
    response = client.post(
        "/api/auth/register",
        json={"username": "duplicate", "password": "password123"},
    )

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_api_auth_login_success(monkeypatch) -> None:
    async def fake_authenticate_user(username: str, password: str) -> TokenResponse:
        return TokenResponse(
            access_token="fake_access_token",
            refresh_token="fake_refresh_token",
            token_type="bearer",
        )

    monkeypatch.setattr(
        auth_router_module, "authenticate_user", fake_authenticate_user
    )

    from fastapi.testclient import TestClient

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


def test_api_auth_login_wrong_password(monkeypatch) -> None:
    async def fake_authenticate_user(username: str, password: str) -> TokenResponse:
        raise ValueError("Incorrect username or password")

    monkeypatch.setattr(
        auth_router_module, "authenticate_user", fake_authenticate_user
    )

    from fastapi.testclient import TestClient

    client = TestClient(main_module.app)
    response = client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "wrong"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == 401


def test_api_auth_refresh_success(monkeypatch) -> None:
    async def fake_refresh_access_token(refresh_token: str) -> TokenResponse:
        return TokenResponse(
            access_token="new_access_token",
            refresh_token="new_refresh_token",
            token_type="bearer",
        )

    monkeypatch.setattr(
        auth_router_module, "refresh_access_token", fake_refresh_access_token
    )

    from fastapi.testclient import TestClient

    client = TestClient(main_module.app)
    response = client.post(
        "/api/auth/refresh",
        json={"refresh_token": "old_refresh_token"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["access_token"] == "new_access_token"


def test_api_auth_refresh_invalid_token(monkeypatch) -> None:
    async def fake_refresh_access_token(refresh_token: str) -> TokenResponse:
        raise ValueError("Invalid or expired refresh token")

    monkeypatch.setattr(
        auth_router_module, "refresh_access_token", fake_refresh_access_token
    )

    from fastapi.testclient import TestClient

    client = TestClient(main_module.app)
    response = client.post(
        "/api/auth/refresh",
        json={"refresh_token": "invalid_token"},
    )

    assert response.status_code == 401


def test_api_auth_me_with_valid_token(monkeypatch, auth_headers) -> None:
    captured = {}

    async def fake_get_current_user_info(user_id: str) -> UserInfoResponse:
        captured["user_id"] = user_id
        return UserInfoResponse(
            user_id=user_id,
            username="testuser",
            avatar_color="#4f46e5",
            created_at="2026-01-01T00:00:00Z",
        )

    monkeypatch.setattr(
        auth_router_module, "get_current_user_info", fake_get_current_user_info
    )

    from fastapi.testclient import TestClient

    client = TestClient(main_module.app)
    response = client.get("/api/auth/me", headers=auth_headers)

    assert response.status_code == 200
    assert captured.get("user_id") == "usr_test_user"


def test_api_auth_me_without_token() -> None:
    from fastapi.testclient import TestClient

    client = TestClient(main_module.app)
    response = client.get("/api/auth/me")

    assert response.status_code == 401


def test_api_protected_endpoint_without_token() -> None:
    from fastapi.testclient import TestClient

    client = TestClient(main_module.app)
    response = client.get("/api/models")

    assert response.status_code == 401


def test_api_auth_rate_limit(monkeypatch) -> None:
    call_count = 0

    async def fake_register_user(username: str, password: str) -> RegisterResponse:
        nonlocal call_count
        call_count += 1
        return RegisterResponse(
            user_id=f"usr_{call_count}",
            username=username,
            created_at="2026-01-01T00:00:00Z",
        )

    monkeypatch.setattr(auth_router_module, "register_user", fake_register_user)

    from fastapi.testclient import TestClient

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


def test_api_auth_delete_own_account(monkeypatch, auth_headers) -> None:
    deleted_user_id = {}

    async def fake_delete_user(user_id: str) -> bool:
        deleted_user_id["id"] = user_id
        return True

    monkeypatch.setattr(auth_router_module, "delete_user", fake_delete_user)

    from fastapi.testclient import TestClient

    client = TestClient(main_module.app)
    response = client.delete("/api/auth/users/usr_test_user", headers=auth_headers)

    assert response.status_code == 200
    assert deleted_user_id.get("id") == "usr_test_user"


def test_api_auth_delete_other_account_forbidden(auth_headers) -> None:
    from fastapi.testclient import TestClient

    client = TestClient(main_module.app)
    response = client.delete(
        "/api/auth/users/usr_other_user", headers=auth_headers
    )

    assert response.status_code == 403


def test_api_auth_delete_user_not_found(monkeypatch, auth_headers) -> None:
    async def fake_delete_user(user_id: str) -> bool:
        raise ValueError("User not found")

    monkeypatch.setattr(auth_router_module, "delete_user", fake_delete_user)

    from fastapi.testclient import TestClient

    client = TestClient(main_module.app)
    response = client.delete("/api/auth/users/usr_test_user", headers=auth_headers)

    assert response.status_code == 404
