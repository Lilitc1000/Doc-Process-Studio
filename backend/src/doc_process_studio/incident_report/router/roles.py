from fastapi import APIRouter, Depends, HTTPException

from ...core.security import get_current_user_id
from ..schemas.request import IncidentRoleAssignRequest
from ..schemas.response import (
    IncidentPermissionListResponse,
    IncidentRoleDefinitionListResponse,
    IncidentRoleEntry,
    IncidentRoleListResponse,
    IncidentUserPermissionsResponse,
    IncidentUserWithRolesListResponse,
)
from ..service.role import (
    assign_role_and_return_entry,
    get_user_incident_roles,
    get_user_permissions,
    list_permissions_response,
    list_role_assignments_with_names,
    list_role_definitions_with_permissions,
    list_users_with_roles_response,
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
    return await list_role_assignments_with_names()


@router.get("/users-with-roles", response_model=IncidentUserWithRolesListResponse)
async def list_users_with_roles(
    admin_id: str = Depends(require_admin),
) -> IncidentUserWithRolesListResponse:
    return await list_users_with_roles_response()


@router.post("/roles", response_model=IncidentRoleEntry)
async def assign_role(
    payload: IncidentRoleAssignRequest,
    admin_id: str = Depends(require_admin),
) -> IncidentRoleEntry:
    try:
        return await assign_role_and_return_entry(
            user_id=payload.user_id,
            role=payload.role,
            assigned_by=admin_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
    return await list_role_definitions_with_permissions()


@router.get("/permissions", response_model=IncidentPermissionListResponse)
async def list_perms(
    user_id: str = Depends(get_current_user_id),
) -> IncidentPermissionListResponse:
    return await list_permissions_response()
