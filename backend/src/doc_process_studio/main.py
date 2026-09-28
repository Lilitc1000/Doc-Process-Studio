import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .auth.router.auth import router as auth_router
from .chat.infrastructure.attachments import cleanup_expired_attachments
from .chat.router.attachments import router as chat_attachments_router
from .chat.router.sessions import router as chat_sessions_router
from .chat.router.stream import router as chat_stream_router
from .common.infrastructure.config import settings
from .common.infrastructure.database import Base, engine
from .common.infrastructure.model_context import warmup_model_context_cache
from .common.middleware.logging_config import setup_logging
from .common.middleware.request_id import RequestIdMiddleware
from .common.middleware.request_logging import RequestLoggingMiddleware
from .common.security.secret_cipher import get_secret_cipher
from .incident_report.infrastructure.dependencies import get_role_repository
from .incident_report.router.analytics import router as incident_report_analytics_router
from .incident_report.router.reports import router as incident_report_reports_router
from .incident_report.router.roles import router as incident_report_roles_router
from .knowledge_base.router import router as knowledge_base_router
from .settings.router.settings import router as settings_router
from .skill.router.routes import router as skill_routes_router
from .system.router.agent_traces import router as agent_traces_router
from .system.router.health import router as health_router
from .system.router.models import router as models_router

_logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    setup_logging()

    # 敏感凭据加密器：主密钥缺失 / 非法时在这里 fail fast，
    # 而不是等管理员第一次保存密钥时才发现问题。
    get_secret_cipher()

    if settings.auto_create_schema:
        _logger.warning(
            "AUTO_CREATE_SCHEMA is on: using Base.metadata.create_all as fallback. "
            "Schema should be managed by alembic migrations instead."
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    # 管理员不再由 ADMIN_USERNAME/ADMIN_PASSWORD 在启动时创建：
    # 全新部署时前端会引导到 /setup 由部署者自行创建首个管理员（auth_service.setup_admin）。
    role_repo = get_role_repository()
    await role_repo.seed_rbac_data()
    cleanup_expired_attachments()
    await warmup_model_context_cache()

    yield


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RequestIdMiddleware)


@app.exception_handler(Exception)
async def _unhandled_exception_handler(request: Request, _exc: Exception) -> JSONResponse:
    _logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误，请稍后重试。"},
    )


app.include_router(auth_router)
app.include_router(chat_stream_router)
app.include_router(chat_sessions_router)
app.include_router(chat_attachments_router)
app.include_router(incident_report_reports_router)
app.include_router(incident_report_roles_router)
app.include_router(incident_report_analytics_router)
app.include_router(skill_routes_router)
app.include_router(health_router)
app.include_router(models_router)
app.include_router(agent_traces_router)
app.include_router(knowledge_base_router)
app.include_router(settings_router)
