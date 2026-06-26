"""应用层角色 DTO。"""

from datetime import datetime

from pydantic import BaseModel, Field


class IncidentRoleEntry(BaseModel):
    user_id: str = Field(...)
    role: str = Field(...)
    assigned_by: str | None = Field(default=None)
    assigned_by_name: str | None = Field(default=None)
    assigned_at: datetime | None = Field(default=None)


class IncidentRoleDefinitionEntry(BaseModel):
    role_key: str = Field(...)
    role_name: str = Field(...)
    description: str | None = Field(default=None)
    permissions: list[str] = Field(default_factory=list)


class IncidentPermissionEntry(BaseModel):
    permission_key: str = Field(...)
    permission_name: str = Field(...)
    description: str | None = Field(default=None)
    category: str = Field(...)


class IncidentUserWithRolesEntry(BaseModel):
    user_id: str = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    roles: list[str] = Field(default_factory=list, description="已分配的角色列表")


class IncidentUserRolesResponse(BaseModel):
    user_id: str = Field(...)
    roles: list[str] = Field(default_factory=list)


class IncidentUserPermissionsResponse(BaseModel):
    user_id: str = Field(...)
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)


class IncidentRoleListResponse(BaseModel):
    items: list[IncidentRoleEntry] = Field(default_factory=list)


class IncidentRoleDefinitionListResponse(BaseModel):
    items: list[IncidentRoleDefinitionEntry] = Field(default_factory=list)


class IncidentPermissionListResponse(BaseModel):
    items: list[IncidentPermissionEntry] = Field(default_factory=list)


class IncidentUserWithRolesListResponse(BaseModel):
    items: list[IncidentUserWithRolesEntry] = Field(default_factory=list)
