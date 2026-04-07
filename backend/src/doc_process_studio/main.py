from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .routers import routers as app_routers
from .services.chat.attachments import cleanup_expired_attachments
from .settings import settings


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    cleanup_expired_attachments()
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

for router in app_routers:
    app.include_router(router)
