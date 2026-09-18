"""全局角色定义。

**与事故报告模块的角色是两套东西**，不要混用：

- 本模块的 ``users.role`` 是**全局角色**，决定能否修改全系统共享的设置
  （如 RAGFlow 连接信息与密钥）。
- ``incident_report_user_roles`` 是**事故报告模块级 RBAC**，只在该模块内生效。

一期只需要 admin / member 两种，用字符串列而不是布尔列，是为了将来加
``operator`` / ``auditor`` 时不必再来一次迁移。
"""

from enum import StrEnum


class Role(StrEnum):
    """全局角色。"""

    ADMIN = "admin"
    MEMBER = "member"


ROLE_ADMIN = Role.ADMIN.value
ROLE_MEMBER = Role.MEMBER.value
VALID_ROLES: frozenset[str] = frozenset({ROLE_ADMIN, ROLE_MEMBER})


def is_admin_role(role: str | None) -> bool:
    """判断给定角色值是否为管理员。

    **严格匹配**，只容忍首尾空白（数据库中偶尔会带上），不做大小写折叠：
    这是权限判定，未知取值一律视为非管理员（fail closed）。
    宽容地接受 ``"Admin"`` 这类变体，等于给"某个地方不小心写了个变体值"
    留下提权空间，宁可让它在启动日志里露出 ERROR（见
    ``AuthService.ensure_admin_user``），也不要静默放行。
    """
    return (role or "").strip() == ROLE_ADMIN
