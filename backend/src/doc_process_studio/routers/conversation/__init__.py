from .artifacts import router as artifacts_router
from .sessions import router as sessions_router
from .stream import router as stream_router

routers = (stream_router, sessions_router, artifacts_router)

__all__ = [
    "artifacts_router",
    "routers",
    "sessions_router",
    "stream_router",
]
