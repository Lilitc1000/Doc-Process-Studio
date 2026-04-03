from fastapi import APIRouter

from ..models.skills import SkillListResponse
from ..services.skill_registry import (
    get_default_skill_id,
    list_skill_interfaces,
)

router = APIRouter(prefix="/api", tags=["skills"])


@router.get("/skills", response_model=SkillListResponse)
async def list_skills() -> SkillListResponse:
    return SkillListResponse(
        skills=list_skill_interfaces(),
        default_skill_id=get_default_skill_id(),
    )
