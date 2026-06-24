import logging
import time
from collections import deque

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm

from ...core.config import settings
from ...core.security import get_current_user_id
from ..application.auth_service import AuthService
from ..domain.errors import (
    AuthError,
    IncorrectPasswordError,
    InvalidCredentialsError,
    InvalidTokenError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from ..infrastructure.dependencies import get_auth_service
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

logger = logging.getLogger(__name__)

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


def _handle_auth_error(exc: AuthError) -> HTTPException:
    if isinstance(exc, UserAlreadyExistsError):
        logger.warning("Auth error: %s", exc)
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, (InvalidCredentialsError, InvalidTokenError)):
        logger.warning("Auth error: %s", exc)
        return HTTPException(status_code=401, detail=str(exc))
    if isinstance(exc, IncorrectPasswordError):
        logger.warning("Auth error: %s", exc)
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, UserNotFoundError):
        logger.warning("Auth error: %s", exc)
        return HTTPException(status_code=404, detail=str(exc))
    logger.warning("Auth error: %s", exc)
    return HTTPException(status_code=400, detail=str(exc))


@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(
    payload: RegisterRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
) -> RegisterResponse:
    _check_auth_rate_limit(request.client.host if request.client else "unknown")
    try:
        return await service.register(username=payload.username, password=payload.password)
    except AuthError as exc:
        raise _handle_auth_error(exc) from exc


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    _check_auth_rate_limit(request.client.host if request.client else "unknown")
    try:
        return await service.authenticate(username=form.username, password=form.password)
    except AuthError as exc:
        raise _handle_auth_error(exc) from exc


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    payload: RefreshTokenRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    try:
        return await service.refresh_token(payload.refresh_token)
    except AuthError as exc:
        raise _handle_auth_error(exc) from exc


@router.get("/me", response_model=UserInfoResponse)
async def get_me(
    user_id: str = Depends(get_current_user_id),
    service: AuthService = Depends(get_auth_service),
) -> UserInfoResponse:
    try:
        return await service.get_current_user_info(user_id)
    except AuthError as exc:
        raise _handle_auth_error(exc) from exc


@router.put("/me", response_model=UpdateProfileResponse)
async def update_me(
    payload: UpdateProfileRequest,
    user_id: str = Depends(get_current_user_id),
    service: AuthService = Depends(get_auth_service),
) -> UpdateProfileResponse:
    try:
        return await service.update_profile(
            user_id,
            username=payload.username,
            avatar_color=payload.avatar_color,
        )
    except AuthError as exc:
        raise _handle_auth_error(exc) from exc


@router.put("/password", response_model=MessageResponse)
async def change_password(
    payload: ChangePasswordRequest,
    user_id: str = Depends(get_current_user_id),
    service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    try:
        await service.change_password(
            user_id,
            current_password=payload.current_password,
            new_password=payload.new_password,
        )
        return MessageResponse(message="Password updated successfully")
    except AuthError as exc:
        raise _handle_auth_error(exc) from exc


@router.post("/logout", response_model=MessageResponse)
async def logout(
    payload: LogoutRequest,
    user_id: str = Depends(get_current_user_id),
    service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    await service.logout(refresh_token=payload.refresh_token)
    return MessageResponse(message="Logged out successfully")


@router.delete("/users/{user_id}", response_model=MessageResponse)
async def delete_account(
    user_id: str,
    current_user_id: str = Depends(get_current_user_id),
    service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    if user_id != current_user_id:
        raise HTTPException(
            status_code=403,
            detail="You can only delete your own account",
        )
    try:
        await service.delete_user(user_id)
        return MessageResponse(message="User deleted successfully")
    except AuthError as exc:
        raise _handle_auth_error(exc) from exc


if settings.env == "dev":

    @router.delete("/users/by-prefix/{prefix}", response_model=MessageResponse)
    async def delete_users_by_username_prefix(
        prefix: str,
        service: AuthService = Depends(get_auth_service),
    ) -> MessageResponse:
        count = await service.delete_users_by_prefix(prefix)
        return MessageResponse(message=f"Deleted {count} user(s) with prefix '{prefix}'")

    @router.post("/rate-limit-whitelist", response_model=MessageResponse)
    async def add_rate_limit_whitelist(request: Request) -> MessageResponse:
        client_host = request.client.host if request.client else "unknown"
        _RATE_LIMIT_WHITELIST.add(client_host)
        return MessageResponse(message=f"Added {client_host} to rate limit whitelist")

    @router.post("/ensure-admin", response_model=MessageResponse)
    async def ensure_admin(
        service: AuthService = Depends(get_auth_service),
    ) -> MessageResponse:
        await service.ensure_admin_user(
            admin_username=settings.admin_username,
            admin_password=settings.admin_password,
        )
        return MessageResponse(message="Admin user ensured")
