import time
from collections import deque

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm

from ..schemas.request import (
    ChangePasswordRequest,
    LogoutRequest,
    RefreshTokenRequest,
    RegisterRequest,
    UpdateProfileRequest,
)
from ..schemas.response import (
    MessageResponse,
    RegisterResponse,
    TokenResponse,
    UpdateProfileResponse,
    UserInfoResponse,
)
from ..service.auth import (
    authenticate_user,
    change_user_password,
    delete_user,
    delete_users_by_prefix,
    ensure_admin_user,
    get_current_user_info,
    logout_user,
    refresh_access_token,
    register_user,
    update_user_profile,
)
from ...core.config import settings
from ...core.security import get_current_user_id

router = APIRouter(prefix="/api/auth", tags=["auth"])

_auth_rate_windows: dict[str, deque[float]] = {}
_AUTH_RATE_LIMIT = 5
_AUTH_RATE_WINDOW_SECONDS = 60
_RATE_LIMIT_WHITELIST: set[str] = set()


def _check_auth_rate_limit(client_key: str) -> None:
    if client_key in _RATE_LIMIT_WHITELIST:
        return
    now = time.monotonic()
    window = _auth_rate_windows.get(client_key)
    if window is None:
        window = deque()
        _auth_rate_windows[client_key] = window

    while window and (now - window[0]) > _AUTH_RATE_WINDOW_SECONDS:
        window.popleft()
        if not window:
            del _auth_rate_windows[client_key]
            return

    if len(window) >= _AUTH_RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="请求过于频繁，请稍后重试。",
        )

    window.append(now)


@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(payload: RegisterRequest, request: Request) -> RegisterResponse:
    _check_auth_rate_limit(request.client.host if request.client else "unknown")
    try:
        return await register_user(payload.username, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
) -> TokenResponse:
    _check_auth_rate_limit(request.client.host if request.client else "unknown")
    try:
        return await authenticate_user(form.username, form.password)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(payload: RefreshTokenRequest) -> TokenResponse:
    try:
        return await refresh_access_token(payload.refresh_token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.get("/me", response_model=UserInfoResponse)
async def get_me(user_id: str = Depends(get_current_user_id)) -> UserInfoResponse:
    try:
        return await get_current_user_info(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.put("/me", response_model=UpdateProfileResponse)
async def update_me(
    payload: UpdateProfileRequest,
    user_id: str = Depends(get_current_user_id),
) -> UpdateProfileResponse:
    try:
        return await update_user_profile(
            user_id=user_id,
            username=payload.username,
            avatar_color=payload.avatar_color,
        )
    except ValueError as exc:
        if "already exists" in str(exc):
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/password", response_model=MessageResponse)
async def change_password(
    payload: ChangePasswordRequest,
    user_id: str = Depends(get_current_user_id),
) -> MessageResponse:
    try:
        await change_user_password(
            user_id=user_id,
            current_password=payload.current_password,
            new_password=payload.new_password,
        )
        return MessageResponse(message="Password updated successfully")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/logout", response_model=MessageResponse)
async def logout(
    payload: LogoutRequest,
    user_id: str = Depends(get_current_user_id),
) -> MessageResponse:
    await logout_user(access_token_sub=user_id, refresh_token=payload.refresh_token)
    return MessageResponse(message="Logged out successfully")


@router.delete("/users/{user_id}", response_model=MessageResponse)
async def delete_account(
    user_id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> MessageResponse:
    if user_id != current_user_id:
        raise HTTPException(
            status_code=403,
            detail="You can only delete your own account",
        )
    try:
        await delete_user(user_id)
        return MessageResponse(message="User deleted successfully")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


if settings.env == "dev":

    @router.delete("/users/by-prefix/{prefix}", response_model=MessageResponse)
    async def delete_users_by_username_prefix(prefix: str) -> MessageResponse:
        count = await delete_users_by_prefix(prefix)
        return MessageResponse(message=f"Deleted {count} user(s) with prefix '{prefix}'")

    @router.post("/rate-limit-whitelist", response_model=MessageResponse)
    async def add_rate_limit_whitelist(request: Request) -> MessageResponse:
        client_host = request.client.host if request.client else "unknown"
        _RATE_LIMIT_WHITELIST.add(client_host)
        return MessageResponse(message=f"Added {client_host} to rate limit whitelist")

    @router.post("/ensure-admin", response_model=MessageResponse)
    async def ensure_admin() -> MessageResponse:
        await ensure_admin_user()
        return MessageResponse(message="Admin user ensured")
