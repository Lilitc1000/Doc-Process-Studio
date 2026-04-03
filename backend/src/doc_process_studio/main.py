from fastapi import FastAPI

from .routers import routers as app_routers
from .settings import settings

app = FastAPI(title=settings.app_name, version="0.1.0")

for router in app_routers:
    app.include_router(router)
