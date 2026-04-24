from contextlib import asynccontextmanager

from fastapi import FastAPI

from .core.config import settings
from .core.model_context import warmup_model_context_cache
from .chat.service.attachments import cleanup_expired_attachments
from .chat.router.stream import router as chat_stream_router
from .chat.router.sessions import router as chat_sessions_router
from .chat.router.attachments import router as chat_attachments_router
from .incident_report.router.incident_reports import router as incident_reports_router
from .skill.router.routes import router as skill_routes_router
from .system.router.health import router as health_router
from .system.router.models import router as models_router
from .system.router.agent_traces import router as agent_traces_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    cleanup_expired_attachments()
    await warmup_model_context_cache()
    yield


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
)

app.include_router(chat_stream_router)
app.include_router(chat_sessions_router)
app.include_router(chat_attachments_router)
app.include_router(incident_reports_router)
app.include_router(skill_routes_router)
app.include_router(health_router)
app.include_router(models_router)
app.include_router(agent_traces_router)
