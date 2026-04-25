from fastapi import APIRouter, Depends

from ..schemas import OllamaModelListResponse
from ...core.ollama import fetch_remote_model_names
from ...core.security import get_current_user_id

router = APIRouter(prefix="/api", tags=["models"])


@router.get("/models", response_model=OllamaModelListResponse)
async def list_remote_models(
    user_id: str = Depends(get_current_user_id),
) -> OllamaModelListResponse:
    model_names = await fetch_remote_model_names()
    return OllamaModelListResponse(models=[{"name": name} for name in model_names])
