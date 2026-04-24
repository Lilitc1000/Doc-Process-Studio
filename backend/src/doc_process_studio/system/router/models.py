from fastapi import APIRouter

from ..schemas import OllamaModelListResponse
from ...core.ollama import fetch_remote_model_names

router = APIRouter(prefix="/api", tags=["models"])


@router.get("/models", response_model=OllamaModelListResponse)
async def list_remote_models() -> OllamaModelListResponse:
    model_names = await fetch_remote_model_names()
    return OllamaModelListResponse(models=[{"name": name} for name in model_names])

