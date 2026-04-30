from datetime import UTC, datetime

from sqlalchemy import delete, select, update

from ...core.cache import get_redis_client
from ...core.config import settings
from ...core.database import async_session_factory
from ...core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_user_id,
    hash_password,
    verify_password,
)
from ...shared.dtutils import to_utc8
from ..models.user import User
from ..schemas.response import (
    RegisterResponse,
    TokenResponse,
    UpdateProfileResponse,
    UserInfoResponse,
)


def _build_token_blacklist_key(jti: str) -> str:
    return f"dps:token-blacklist:{jti}"


async def register_user(username: str, password: str) -> RegisterResponse:
    async with async_session_factory() as session:
        existing = await session.execute(
            select(User).where(User.username == username),
        )
        if existing.scalar_one_or_none() is not None:
            raise ValueError("Username already exists")

        user = User(
            user_id=generate_user_id(),
            username=username,
            hashed_password=hash_password(password),
            avatar_color="#4f46e5",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        return RegisterResponse(
            user_id=user.user_id,
            username=user.username,
            created_at=to_utc8(user.created_at),
        )


async def resolve_usernames(user_ids: set[str]) -> dict[str, str]:
    if not user_ids:
        return {}
    async with async_session_factory() as session:
        result = await session.execute(
            select(User.user_id, User.username).where(User.user_id.in_(user_ids)),
        )
        return {row[0]: row[1] for row in result.all()}


async def authenticate_user(username: str, password: str) -> TokenResponse:
    async with async_session_factory() as session:
        result = await session.execute(
            select(User).where(User.username == username),
        )
        user = result.scalar_one_or_none()
        if user is None or not verify_password(password, user.hashed_password):
            raise ValueError("Incorrect username or password")

        access_token = create_access_token(user.user_id, user.username)
        refresh_token = create_refresh_token(user.user_id)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        )


async def refresh_access_token(refresh_token: str) -> TokenResponse:
    payload = decode_token(refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise ValueError("Invalid or expired refresh token")

    jti = payload.get("jti", "")
    redis_client = get_redis_client()
    is_blacklisted = await redis_client.get(_build_token_blacklist_key(jti))
    if is_blacklisted:
        raise ValueError("Invalid or expired refresh token")

    user_id = payload.get("sub", "")
    async with async_session_factory() as session:
        result = await session.execute(
            select(User).where(User.user_id == user_id),
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise ValueError("Invalid or expired refresh token")

        new_access_token = create_access_token(user.user_id, user.username)
        new_refresh_token = create_refresh_token(user.user_id)

        if jti:
            expire_seconds = settings.refresh_token_expire_days * 86400
            await redis_client.set(
                _build_token_blacklist_key(jti),
                "1",
                ex=expire_seconds,
            )

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
        )


async def get_current_user_info(user_id: str) -> UserInfoResponse:
    async with async_session_factory() as session:
        result = await session.execute(
            select(User).where(User.user_id == user_id),
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise ValueError("User not found")

        return UserInfoResponse(
            user_id=user.user_id,
            username=user.username,
            avatar_color=user.avatar_color,
            created_at=to_utc8(user.created_at),
        )


async def update_user_profile(
    user_id: str,
    username: str | None = None,
    avatar_color: str | None = None,
) -> UpdateProfileResponse:
    async with async_session_factory() as session:
        result = await session.execute(
            select(User).where(User.user_id == user_id),
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise ValueError("User not found")

        if username is not None and username != user.username:
            existing = await session.execute(
                select(User).where(User.username == username),
            )
            if existing.scalar_one_or_none() is not None:
                raise ValueError("Username already exists")
            user.username = username

        if avatar_color is not None:
            user.avatar_color = avatar_color

        user.updated_at = datetime.now(UTC)
        await session.commit()
        await session.refresh(user)

        return UpdateProfileResponse(
            user_id=user.user_id,
            username=user.username,
            avatar_color=user.avatar_color,
            created_at=to_utc8(user.created_at),
        )


async def change_user_password(
    user_id: str,
    current_password: str,
    new_password: str,
) -> None:
    async with async_session_factory() as session:
        result = await session.execute(
            select(User).where(User.user_id == user_id),
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise ValueError("User not found")

        if not verify_password(current_password, user.hashed_password):
            raise ValueError("Current password is incorrect")

        user.hashed_password = hash_password(new_password)
        user.updated_at = datetime.now(UTC)
        await session.commit()


async def logout_user(access_token_sub: str, refresh_token: str) -> None:
    payload = decode_token(refresh_token)
    if payload and payload.get("type") == "refresh":
        jti = payload.get("jti", "")
        if jti:
            redis_client = get_redis_client()
            expire_seconds = settings.refresh_token_expire_days * 86400
            await redis_client.set(
                _build_token_blacklist_key(jti),
                "1",
                ex=expire_seconds,
            )


async def delete_user(user_id: str) -> bool:
    async with async_session_factory() as session:
        result = await session.execute(
            select(User).where(User.user_id == user_id),
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise ValueError("User not found")

        await session.execute(delete(User).where(User.user_id == user_id))
        await session.commit()
        return True


async def delete_users_by_prefix(username_prefix: str) -> int:
    from ...incident_report.models.incident_report_orm import (
        IncidentComment,
        IncidentReport,
    )
    from ...incident_report.models.audit_log import IncidentAuditLog
    from ...incident_report.models.incident_report_role import IncidentReportUserRole

    async with async_session_factory() as session:
        user_ids_result = await session.execute(
            select(User.user_id).where(User.username.like(f"{username_prefix}%"))
        )
        user_ids = [row[0] for row in user_ids_result.all()]

        if not user_ids:
            return 0

        report_ids_result = await session.execute(
            select(IncidentReport.id).where(
                IncidentReport.reporter_id.in_(user_ids)
            )
        )
        report_ids = [row[0] for row in report_ids_result.all()]

        if report_ids:
            await session.execute(
                delete(IncidentComment).where(
                    IncidentComment.report_id.in_(report_ids)
                )
            )
            await session.execute(
                delete(IncidentAuditLog).where(
                    IncidentAuditLog.report_id.in_(report_ids)
                )
            )
            await session.execute(
                delete(IncidentReport).where(
                    IncidentReport.id.in_(report_ids)
                )
            )

        await session.execute(
            delete(IncidentComment).where(
                IncidentComment.author_id.in_(user_ids)
            )
        )
        await session.execute(
            delete(IncidentAuditLog).where(
                IncidentAuditLog.actor_id.in_(user_ids)
            )
        )
        await session.execute(
            delete(IncidentReportUserRole).where(
                IncidentReportUserRole.user_id.in_(user_ids)
            )
        )
        await session.execute(
            delete(IncidentReport).where(
                IncidentReport.reporter_id.in_(user_ids)
            )
        )

        result = await session.execute(
            delete(User).where(User.username.like(f"{username_prefix}%"))
        )
        await session.commit()
        return result.rowcount


async def ensure_admin_user() -> None:
    async with async_session_factory() as session:
        result = await session.execute(select(User).limit(1))
        if result.scalar_one_or_none() is not None:
            return

        admin = User(
            user_id=generate_user_id(),
            username=settings.admin_username,
            hashed_password=hash_password(settings.admin_password),
            avatar_color="#4f46e5",
        )
        session.add(admin)
        await session.flush()

        from ...incident_report.models.incident_report_role import IncidentReportUserRole
        from ...incident_report.schemas.common import VALID_ROLES

        for role_key in VALID_ROLES:
            role_entry = IncidentReportUserRole(
                id=generate_user_id(),
                user_id=admin.user_id,
                role_key=role_key,
                assigned_by=admin.user_id,
            )
            session.add(role_entry)

        await session.commit()
