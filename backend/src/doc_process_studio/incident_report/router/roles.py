from fastapi import APIRouter, Depends, HTTPException

from ...core.security import get_current_user_id
from ..application.role_service import RoleService
from ..domain.errors import DomainError
from ..infrastructure.dependencies import get_role_service
from ..schemas.request import IncidentRoleAssignRequest
from ..schemas.response import (
    IncidentPermissionListResponse,
    IncidentRoleDefinitionListResponse,
    IncidentRoleEntry,
    IncidentRoleListResponse,
    IncidentUserPermissionsResponse,
    IncidentUserWithRolesListResponse,
)
from .dependencies import require_admin

router = APIRouter(prefix="/api/incident-report", tags=["incident-report-roles"])


@router.get("/roles/me", response_model=IncidentUserPermissionsResponse)
async def get_my_roles(
    user_id: str = Depends(get_current_user_id),
    service: RoleService = Depends(get_role_service),
) -> IncidentUserPermissionsResponse:
    return await service.get_my_permissions(user_id=user_id)


@router.get("/roles", response_model=IncidentRoleListResponse)
async def list_roles(
    user_id: str = Depends(require_admin),
    service: RoleService = Depends(get_role_service),
) -> IncidentRoleListResponse:
    return await service.list_role_assignments()


@router.get("/users-with-roles", response_model=IncidentUserWithRolesListResponse)
async def list_users_with_roles(
    admin_id: str = Depends(require_admin),
    service: RoleService = Depends(get_role_service),
) -> IncidentUserWithRolesListResponse:
    return await service.list_users_with_roles()


@router.post("/roles", response_model=IncidentRoleEntry)
async def assign_role(
    payload: IncidentRoleAssignRequest,
    admin_id: str = Depends(require_admin),
    service: RoleService = Depends(get_role_service),
) -> IncidentRoleEntry:
    try:
        return await service.assign_role(
            user_id=payload.user_id,
            role=payload.role,
            assigned_by=admin_id,
        )
    except (ValueError, DomainError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/roles/{target_user_id}/{role}")
async def revoke_role(
    target_user_id: str,
    role: str,
    admin_id: str = Depends(require_admin),
    service: RoleService = Depends(get_role_service),
) -> dict[str, bool]:
    try:
        await service.revoke_role(user_id=target_user_id, role=role)
    except (ValueError, DomainError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"revoked": True}


@router.get("/role-definitions", response_model=IncidentRoleDefinitionListResponse)
async def list_role_defs(
    user_id: str = Depends(get_current_user_id),
    service: RoleService = Depends(get_role_service),
) -> IncidentRoleDefinitionListResponse:
    return await service.list_role_definitions()


@router.get("/permissions", response_model=IncidentPermissionListResponse)
async def list_perms(
    user_id: str = Depends(get_current_user_id),
    service: RoleService = Depends(get_role_service),
) -> IncidentPermissionListResponse:
    return await service.list_permissions()
