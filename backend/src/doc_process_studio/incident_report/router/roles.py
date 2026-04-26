from fastapi import APIRouter, Depends, HTTPException

from ...core.security import get_current_user_id
from ..schemas.request import IncidentRoleAssignRequest
from ..schemas.response import IncidentRoleEntry, IncidentRoleListResponse, IncidentUserRolesResponse
from ..service.role import (
    assign_incident_role,
    get_user_incident_roles,
    list_all_role_assignments,
    revoke_incident_role,
)
from .dependencies import require_admin

router = APIRouter(prefix="/api/incident-report", tags=["incident-report-roles"])


@router.get("/roles/me", response_model=IncidentUserRolesResponse)
async def get_my_roles(
    user_id: str = Depends(get_current_user_id),
) -> IncidentUserRolesResponse:
    roles = await get_user_incident_roles(user_id)
    return IncidentUserRolesResponse(user_id=user_id, roles=sorted(roles))


@router.get("/roles", response_model=IncidentRoleListResponse)
async def list_roles(
    user_id: str = Depends(require_admin),
) -> IncidentRoleListResponse:
    assignments = await list_all_role_assignments()
    items = [
        IncidentRoleEntry(
            user_id=a.user_id,
            role=a.role,
            assigned_by=a.assigned_by,
            assigned_at=a.assigned_at,
        )
        for a in assignments
    ]
    return IncidentRoleListResponse(items=items)


@router.post("/roles", response_model=IncidentRoleEntry)
async def assign_role(
    payload: IncidentRoleAssignRequest,
    admin_id: str = Depends(require_admin),
) -> IncidentRoleEntry:
    try:
        await assign_incident_role(
            user_id=payload.user_id,
            role=payload.role,
            assigned_by=admin_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return IncidentRoleEntry(
        user_id=payload.user_id,
        role=payload.role,
        assigned_by=admin_id,
    )


@router.delete("/roles/{target_user_id}/{role}")
async def revoke_role(
    target_user_id: str,
    role: str,
    admin_id: str = Depends(require_admin),
) -> dict[str, bool]:
    try:
        await revoke_incident_role(user_id=target_user_id, role=role)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"revoked": True}
