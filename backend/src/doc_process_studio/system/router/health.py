from fastapi import APIRouter

from ...common.infrastructure.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.env}
