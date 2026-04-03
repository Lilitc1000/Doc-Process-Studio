from fastapi import APIRouter

from ...models.system.ollama import OllamaModelListResponse
from ...services.infra.ollama import fetch_remote_model_names

router = APIRouter(prefix="/api", tags=["models"])


@router.get("/models", response_model=OllamaModelListResponse)
async def list_remote_models() -> OllamaModelListResponse:
    model_names = await fetch_remote_model_names()
    return OllamaModelListResponse(models=[{"name": name} for name in model_names])

