from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import bcrypt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from ..infrastructure.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(password: str) -> str:
    return str(bcrypt.hashpw(password.encode(), bcrypt.gensalt()), encoding="utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bool(bcrypt.checkpw(plain_password.encode(), hashed_password.encode()))


def create_access_token(user_id: str, username: str) -> str:
    expire = datetime.now(UTC) + timedelta(
        minutes=settings.access_token_expire_minutes,
    )
    payload = {
        "sub": user_id,
        "username": username,
        "type": "access",
        "exp": expire,
    }
    encoded: str = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded


def create_refresh_token(user_id: str) -> str:
    expire = datetime.now(UTC) + timedelta(
        days=settings.refresh_token_expire_days,
    )
    payload = {
        "sub": user_id,
        "type": "refresh",
        "jti": uuid4().hex,
        "exp": expire,
    }
    encoded: str = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded


def decode_token(token: str) -> dict[str, Any] | None:
    try:
        decoded: dict[str, Any] = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return decoded
    except JWTError:
        return None


def generate_user_id() -> str:
    return f"usr_{uuid4().hex[:12]}"


async def get_current_user_id(token: str = Depends(oauth2_scheme)) -> str:
    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Not authenticated")
    user_id: str = payload.get("sub", "")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user_id
