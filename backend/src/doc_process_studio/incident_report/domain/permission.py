"""事故报告权限与角色定义。

包含权限枚举、角色枚举、角色-权限映射、角色定义、权限定义。
这些是领域知识，不属于 HTTP DTO。
"""

from enum import Enum


class Permission(str, Enum):
    """事故报告权限。"""

    REPORT_CREATE = "report:create"
    REPORT_EDIT_OWN = "report:edit_own"
    REPORT_EDIT_ALL = "report:edit_all"
    REPORT_SUBMIT = "report:submit"
    REPORT_VIEW = "report:view"
    REPORT_VIEW_ALL = "report:view_all"
    REPORT_EDIT_ASSIGNED = "report:edit_assigned"
    REPORT_CLOSE_ASSIGNED = "report:close_assigned"
    REPORT_AUDIT = "report:audit"
    REPORT_ASSIGN = "report:assign"
    REPORT_DELETE = "report:delete"
    REPORT_REOPEN = "report:reopen"
    ROLE_MANAGE = "role:manage"
    SYSTEM_CONFIG = "system:config"
    DATA_EXPORT = "data:export"
    ANALYTICS_VIEW = "analytics:view"


class Role(str, Enum):
    """事故报告角色。"""

    VIEWER = "viewer"
    REPORTER = "reporter"
    HANDLER = "handler"
    VERIFIER = "verifier"
    ADMIN = "admin"


# 有效集合（供校验使用）
VALID_ROLES: set[str] = {role.value for role in Role}
VALID_PERMISSIONS: set[str] = {perm.value for perm in Permission}
INCIDENT_VALID_ROLES: list[str] = sorted(VALID_ROLES)

# 每个领域动作需要的权限（从 service/report.py 散落处收敛）
# 用于 application 层在调用聚合根方法前做权限校验
ACTION_PERMISSIONS: dict[str, set[Permission]] = {
    "create": {Permission.REPORT_CREATE},
    "submit": {Permission.REPORT_SUBMIT},
    "approve": {Permission.REPORT_AUDIT},
    "reject": {Permission.REPORT_AUDIT},
    "assign": {Permission.REPORT_ASSIGN},
    "close": {Permission.REPORT_CLOSE_ASSIGNED},
    "reopen": {Permission.REPORT_REOPEN},
    "delete": {Permission.REPORT_DELETE},
}

# 角色 → 权限映射
ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.VIEWER: {Permission.REPORT_VIEW, Permission.ANALYTICS_VIEW},
    Role.REPORTER: {
        Permission.REPORT_VIEW,
        Permission.REPORT_CREATE,
        Permission.REPORT_EDIT_OWN,
        Permission.REPORT_SUBMIT,
        Permission.ANALYTICS_VIEW,
    },
    Role.HANDLER: {
        Permission.REPORT_VIEW,
        Permission.REPORT_VIEW_ALL,
        Permission.REPORT_EDIT_ASSIGNED,
        Permission.REPORT_CLOSE_ASSIGNED,
        Permission.ANALYTICS_VIEW,
    },
    Role.VERIFIER: {
        Permission.REPORT_VIEW,
        Permission.REPORT_VIEW_ALL,
        Permission.REPORT_AUDIT,
        Permission.REPORT_ASSIGN,
        Permission.ANALYTICS_VIEW,
    },
    Role.ADMIN: set(Permission),  # admin 拥有全部权限
}

# 角色定义
ROLE_DEFINITIONS: list[dict[str, str]] = [
    {"role_key": "admin", "role_name": "管理员", "description": "所有权限 + 角色分配 + 系统配置 + 数据导出"},
    {"role_key": "verifier", "role_name": "审核人", "description": "审核待审核报告、查看所有报告、分配处理人"},
    {"role_key": "handler", "role_name": "处理人", "description": "查看分配给自己的报告、更新处理进度、关闭报告"},
    {"role_key": "reporter", "role_name": "报告人", "description": "创建报告、编辑自己的草稿/被驳回报告、提交审核"},
    {"role_key": "viewer", "role_name": "观察者", "description": "仅查看报告列表和详情，无操作权限"},
]

# 权限定义
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
