"""事故报告领域异常。

application 层捕获这些异常后由 router 映射为 HTTP 状态码：
- PermissionDeniedError → 403
- ReportNotFoundError → 404
- 其他 DomainError 子类 → 400
"""


class DomainError(Exception):
    """领域异常基类。"""


class InvalidTransitionError(DomainError):
    """状态转换不合法。"""

    def __init__(self, current: str, action: str, detail: str = ""):
        message = f"当前状态 {current} 不允许执行 {action}"
        if detail:
            message = f"{message}（{detail}）"
        super().__init__(message)
        self.current = current
        self.action = action


class PermissionDeniedError(DomainError):
    """权限不足。"""

    def __init__(self, message: str = "权限不足"):
        super().__init__(message)


class FormIncompleteError(DomainError):
    """表单未填写完整，不允许提交。"""

    def __init__(self, missing: list[str]):
        super().__init__(f"缺少必填字段: {', '.join(missing)}")
        self.missing = missing


class ReportNotFoundError(DomainError):
    """报告不存在。"""

    def __init__(self, report_id: str):
        super().__init__(f"报告 {report_id} 不存在")
        self.report_id = report_id


class UserNotFoundError(DomainError):
    """用户不存在。"""

    def __init__(self, user_id: str):
        super().__init__(f"用户 {user_id} 不存在")
        self.user_id = user_id
