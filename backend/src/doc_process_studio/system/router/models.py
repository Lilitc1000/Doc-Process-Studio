from fastapi import APIRouter, Depends

from ...core.security import get_current_user_id
from ..application.system_service import ModelQueryService
from ..infrastructure.dependencies import get_model_query_service
from ..schemas import OllamaModelItem, OllamaModelListResponse

router = APIRouter(prefix="/api", tags=["models"])


@router.get("/models", response_model=OllamaModelListResponse)
async def list_remote_models(
    user_id: str = Depends(get_current_user_id),
    service: ModelQueryService = Depends(get_model_query_service),
) -> OllamaModelListResponse:
    model_names = await service.list_remote_models()
    return OllamaModelListResponse(models=[OllamaModelItem(name=name) for name in model_names])
