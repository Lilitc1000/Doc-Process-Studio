import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .auth.infrastructure.dependencies import get_auth_service
from .auth.router.auth import router as auth_router
from .chat.router.attachments import router as chat_attachments_router
from .chat.router.sessions import router as chat_sessions_router
from .chat.router.stream import router as chat_stream_router
from .chat.service.attachments import cleanup_expired_attachments
from .core.config import settings
from .core.database import Base, engine
from .core.logging_config import setup_logging
from .core.model_context import warmup_model_context_cache
from .core.request_id import RequestIdMiddleware
from .core.request_logging import RequestLoggingMiddleware
from .incident_report.infrastructure.dependencies import get_role_repository
from .incident_report.router.analytics import router as incident_report_analytics_router
from .incident_report.router.reports import router as incident_report_reports_router
from .incident_report.router.roles import router as incident_report_roles_router
from .knowledge_base.router import router as knowledge_base_router
from .skill.router.routes import router as skill_routes_router
from .system.router.agent_traces import router as agent_traces_router
from .system.router.health import router as health_router
from .system.router.models import router as models_router

_logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    setup_logging()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await get_auth_service().ensure_admin_user(
        admin_username=settings.admin_username,
        admin_password=settings.admin_password,
    )
    role_repo = get_role_repository()
    await role_repo.seed_rbac_data()
    await role_repo.ensure_admin_role()
    cleanup_expired_attachments()
    await warmup_model_context_cache()

    from .core.qdrant import ensure_knowledge_base_collection

    ensure_knowledge_base_collection()

    yield


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RequestIdMiddleware)


@app.exception_handler(Exception)
async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
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
