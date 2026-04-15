from .attachments import router as attachments_router
from .incident_reports import router as incident_reports_router
from .sessions import router as sessions_router
from .stream import router as stream_router

routers = (stream_router, sessions_router, attachments_router, incident_reports_router)

__all__ = [
    "attachments_router",
    "incident_reports_router",
    "routers",
    "sessions_router",
    "stream_router",
]
