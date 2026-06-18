from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from .core.config import settings
from .core.logging_config import setup_logging
from .core.database import Base, engine
from .core.model_context import warmup_model_context_cache
from .auth.router.auth import router as auth_router
from .auth.infrastructure.dependencies import get_auth_service
from .chat.service.attachments import cleanup_expired_attachments
from .chat.router.stream import router as chat_stream_router
from .chat.router.sessions import router as chat_sessions_router
from .chat.router.attachments import router as chat_attachments_router
from .incident_report.router.reports import router as incident_report_reports_router
from .incident_report.router.roles import router as incident_report_roles_router
from .incident_report.router.analytics import router as incident_report_analytics_router
from .incident_report.infrastructure.dependencies import get_role_repository
from .skill.router.routes import router as skill_routes_router
from .system.router.health import router as health_router
from .system.router.models import router as models_router
from .system.router.agent_traces import router as agent_traces_router
from .knowledge_base.router import router as knowledge_base_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
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
