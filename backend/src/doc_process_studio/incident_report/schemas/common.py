from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class PermissionDenied(ValueError):
    pass

IncidentReportStatus = Literal["draft", "pending", "approved", "rejected", "in_progress", "closed"]
IncidentSeverity = Literal["P0", "P1", "P2", "P3"]

VALID_STATUSES: set[str] = {"draft", "pending", "approved", "rejected", "in_progress", "closed"}
VALID_SEVERITIES: set[str] = {"P0", "P1", "P2", "P3"}
VALID_ROLES: set[str] = {"reporter", "handler", "verifier", "admin", "viewer"}
INCIDENT_VALID_ROLES: list[str] = sorted(VALID_ROLES)

VALID_PERMISSIONS: set[str] = {
    "report:create",
    "report:edit_own",
    "report:edit_all",
    "report:submit",
    "report:view",
    "report:view_all",
    "report:edit_assigned",
    "report:close_assigned",
    "report:audit",
    "report:assign",
    "report:delete",
    "report:reopen",
    "role:manage",
    "system:config",
    "data:export",
    "analytics:view",
}

ROLE_DEFINITIONS: list[dict[str, str]] = [
    {"role_key": "admin", "role_name": "管理员", "description": "所有权限 + 角色分配 + 系统配置 + 数据导出"},
    {"role_key": "verifier", "role_name": "审核人", "description": "审核待审核报告、查看所有报告、分配处理人"},
    {"role_key": "handler", "role_name": "处理人", "description": "查看分配给自己的报告、更新处理进度、关闭报告"},
    {"role_key": "reporter", "role_name": "报告人", "description": "创建报告、编辑自己的草稿/被驳回报告、提交审核"},
    {"role_key": "viewer", "role_name": "观察者", "description": "仅查看报告列表和详情，无操作权限"},
]

PERMISSION_DEFINITIONS: list[dict[str, str]] = [
    {"permission_key": "report:create", "permission_name": "创建报告", "description": "创建新的事故报告", "category": "report"},
    {"permission_key": "report:edit_own", "permission_name": "编辑自己的报告", "description": "编辑自己创建的草稿或被驳回的报告", "category": "report"},
    {"permission_key": "report:edit_all", "permission_name": "编辑所有报告", "description": "编辑任意状态的任意报告", "category": "report"},
    {"permission_key": "report:submit", "permission_name": "提交审核", "description": "将报告提交审核", "category": "report"},
    {"permission_key": "report:view", "permission_name": "查看报告", "description": "查看报告列表和详情", "category": "report"},
    {"permission_key": "report:view_all", "permission_name": "查看所有报告", "description": "查看所有用户的报告", "category": "report"},
    {"permission_key": "report:edit_assigned", "permission_name": "编辑被指派的报告", "description": "编辑被指派给自己处理的报告", "category": "report"},
    {"permission_key": "report:close_assigned", "permission_name": "关闭被指派的报告", "description": "关闭被指派给自己处理的报告", "category": "report"},
    {"permission_key": "report:audit", "permission_name": "审核报告", "description": "审核待审核报告（批准/驳回）", "category": "report"},
    {"permission_key": "report:assign", "permission_name": "分配处理人", "description": "为已批准的报告分配处理人", "category": "report"},
    {"permission_key": "report:delete", "permission_name": "删除报告", "description": "删除任意状态的报告", "category": "report"},
    {"permission_key": "report:reopen", "permission_name": "重新打开报告", "description": "重新打开已关闭的报告", "category": "report"},
    {"permission_key": "role:manage", "permission_name": "角色管理", "description": "分配和撤销用户角色", "category": "role"},
    {"permission_key": "system:config", "permission_name": "系统配置", "description": "事故报告系统配置管理", "category": "system"},
    {"permission_key": "data:export", "permission_name": "数据导出", "description": "导出事故报告数据", "category": "data"},
    {"permission_key": "analytics:view", "permission_name": "查看统计分析", "description": "查看事故报告统计分析数据", "category": "analytics"},
]

ROLE_PERMISSIONS_MAP: dict[str, set[str]] = {
    "viewer": {"report:view", "analytics:view"},
    "reporter": {"report:view", "report:create", "report:edit_own", "report:submit", "analytics:view"},
    "handler": {"report:view", "report:view_all", "report:edit_assigned", "report:close_assigned", "analytics:view"},
    "verifier": {"report:view", "report:view_all", "report:audit", "report:assign", "analytics:view"},
    "admin": VALID_PERMISSIONS.copy(),
}

STATUS_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"pending"},
    "rejected": {"pending"},
    "pending": {"approved", "rejected"},
    "approved": {"in_progress"},
    "in_progress": {"closed"},
    "closed": {"draft"},
}


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")


class IncidentFormAnswer(BaseModel):
    value: Any | None = Field(
        default=None,
        description="步骤值。支持字符串、列表、对象等结构。",
    )
    custom_value: str | None = Field(
        default=None,
        description="当步骤支持自定义输入时的补充值。",
    )


class IncidentGeneratedVersion(BaseModel):
    version: int = Field(..., description="版本号，从 1 开始递增。")
    label: str = Field(..., description="用于前端展示的版本标签。")
    generated_at: datetime = Field(..., description="该版本生成时间。")
    report_data: dict[str, Any] = Field(
        default_factory=dict,
        description="该版本生成时使用的 report_data 快照。",
    )


class IncidentFormSnapshot(BaseModel):
    form_answers: dict[str, IncidentFormAnswer] = Field(
        default_factory=dict,
        description="表单各步骤的已填写答案。",
    )
    report_data: dict[str, Any] | None = Field(
        default=None,
        description="最近一次用于生成文档的 report_data 内容。",
    )
    generated_trace_id: str | None = Field(
        default=None,
        description="最近一次正文 AI 生成链路 trace_id，可用于回放。",
    )
    section_trace_ids: dict[str, str] = Field(
        default_factory=dict,
        description="正文分段生成对应的 trace_id。",
    )
    generated_at: datetime | None = Field(
        default=None,
        description="最近一次文档生成完成时间。",
    )
    polish_error: str | None = Field(
        default=None,
        description="最近一次正文 AI 生成失败原因（如有）。",
    )


def build_empty_form_snapshot() -> IncidentFormSnapshot:
    return IncidentFormSnapshot(
        form_answers={},
        report_data=None,
        generated_trace_id=None,
        section_trace_ids={},
        generated_at=None,
        polish_error=None,
    )
