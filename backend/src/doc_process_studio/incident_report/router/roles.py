from fastapi import APIRouter, Depends, HTTPException

from ...core.security import get_current_user_id
from ...shared.dtutils import to_utc8
from ..schemas.request import IncidentRoleAssignRequest
from ..schemas.response import (
    IncidentPermissionEntry,
    IncidentPermissionListResponse,
    IncidentRoleDefinitionEntry,
    IncidentRoleDefinitionListResponse,
    IncidentRoleEntry,
    IncidentRoleListResponse,
    IncidentUserPermissionsResponse,
    IncidentUserRolesResponse,
)
from ..service.role import (
    assign_incident_role,
    get_user_incident_roles,
    get_user_permissions,
    get_role_permissions_map,
    list_all_role_assignments,
    list_permissions,
    list_role_definitions,
    revoke_incident_role,
)
from .dependencies import require_admin

router = APIRouter(prefix="/api/incident-report", tags=["incident-report-roles"])


@router.get("/roles/me", response_model=IncidentUserPermissionsResponse)
async def get_my_roles(
    user_id: str = Depends(get_current_user_id),
) -> IncidentUserPermissionsResponse:
    roles = await get_user_incident_roles(user_id)
    permissions = await get_user_permissions(user_id)
    return IncidentUserPermissionsResponse(
        user_id=user_id,
        roles=sorted(roles),
        permissions=sorted(permissions),
    )


@router.get("/roles", response_model=IncidentRoleListResponse)
async def list_roles(
    user_id: str = Depends(require_admin),
) -> IncidentRoleListResponse:
    assignments = await list_all_role_assignments()
    items = [
        IncidentRoleEntry(
            user_id=a.user_id,
            role=a.role_key,
            assigned_by=a.assigned_by,
            assigned_at=to_utc8(a.assigned_at),
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


@router.get("/role-definitions", response_model=IncidentRoleDefinitionListResponse)
async def list_role_defs(
    user_id: str = Depends(get_current_user_id),
) -> IncidentRoleDefinitionListResponse:
    definitions = await list_role_definitions()
    role_perms_map = await get_role_permissions_map()
    items = [
        IncidentRoleDefinitionEntry(
            role_key=d.role_key,
            role_name=d.role_name,
            description=d.description,
            permissions=role_perms_map.get(d.role_key, []),
        )
        for d in definitions
    ]
    return IncidentRoleDefinitionListResponse(items=items)


@router.get("/permissions", response_model=IncidentPermissionListResponse)
async def list_perms(
    user_id: str = Depends(get_current_user_id),
) -> IncidentPermissionListResponse:
    perms = await list_permissions()
    items = [
        IncidentPermissionEntry(
            permission_key=p.permission_key,
            permission_name=p.permission_name,
            description=p.description,
            category=p.category,
        )
        for p in perms
    ]
    return IncidentPermissionListResponse(items=items)
