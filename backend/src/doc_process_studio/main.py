from fastapi import FastAPI

from .routers.chat import router as chat_router
from .routers.health import router as health_router
from .routers.models import router as models_router
from .settings import settings

app = FastAPI(title=settings.app_name, version="0.1.0")
app.include_router(health_router)
app.include_router(chat_router)
app.include_router(models_router)
