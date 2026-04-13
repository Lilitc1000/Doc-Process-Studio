from .agent_traces import router as agent_traces_router
from .health import router as health_router
from .models import router as models_router

routers = (health_router, models_router, agent_traces_router)

__all__ = [
    "agent_traces_router",
    "health_router",
    "models_router",
    "routers",
]
