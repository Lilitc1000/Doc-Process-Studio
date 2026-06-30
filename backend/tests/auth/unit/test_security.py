import pytest
from fastapi import HTTPException

from doc_process_studio.common.security.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_user_id,
    get_current_user_id,
    hash_password,
    verify_password,
)


def test_hash_password_and_verify() -> None:
    hashed = hash_password("mypassword123")
    assert hashed != "mypassword123"
    assert verify_password("mypassword123", hashed) is True
    assert verify_password("wrongpassword", hashed) is False


def test_hash_password_different_salts() -> None:
    h1 = hash_password("samepassword")
    h2 = hash_password("samepassword")
    assert h1 != h2
    assert verify_password("samepassword", h1) is True
    assert verify_password("samepassword", h2) is True


def test_create_access_token_contains_expected_fields() -> None:
    token = create_access_token("usr_abc123", "testuser")
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "usr_abc123"
    assert payload["username"] == "testuser"
    assert payload["type"] == "access"
    assert "exp" in payload


def test_create_refresh_token_contains_expected_fields() -> None:
    token = create_refresh_token("usr_abc123")
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "usr_abc123"
    assert payload["type"] == "refresh"
    assert "jti" in payload
    assert "exp" in payload


def test_decode_token_returns_none_for_invalid_token() -> None:
    result = decode_token("invalid.token.here")
    assert result is None


def test_decode_token_returns_none_for_expired_token() -> None:
    from datetime import UTC, datetime, timedelta

    from jose import jwt

    from doc_process_studio.common.infrastructure.config import settings

    expired_payload = {
        "sub": "usr_test",
        "type": "access",
        "exp": datetime.now(UTC) - timedelta(hours=1),
    }
    expired_token = jwt.encode(expired_payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    result = decode_token(expired_token)
    assert result is None


def test_generate_user_id_format() -> None:
    uid = generate_user_id()
    assert uid.startswith("usr_")
    assert len(uid) == 16


def test_generate_user_id_uniqueness() -> None:
    ids = {generate_user_id() for _ in range(100)}
    assert len(ids) == 100


async def test_get_current_user_id_returns_user_id_from_valid_token() -> None:
    token = create_access_token("usr_test123", "testuser")
    result = await get_current_user_id(token=token)
    assert result == "usr_test123"


async def test_get_current_user_id_raises_for_invalid_token() -> None:
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user_id(token="invalid.token.here")
    assert exc_info.value.status_code == 401


async def test_get_current_user_id_raises_for_refresh_token() -> None:
    token = create_refresh_token("usr_test123")
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user_id(token=token)
    assert exc_info.value.status_code == 401


async def test_get_current_user_id_raises_for_token_without_sub() -> None:
    from jose import jwt

    from doc_process_studio.common.infrastructure.config import settings

    payload = {"type": "access", "sub": "", "exp": 9999999999}
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user_id(token=token)
    assert exc_info.value.status_code == 401
