"""认证领域异常。

所有认证相关业务错误继承 AuthError，应用层抛出后由 router 映射为 HTTP 状态码。
"""


class AuthError(Exception):
    """认证领域异常基类。"""


class UserAlreadyExistsError(AuthError):
    """用户名已被占用。"""


class InvalidCredentialsError(AuthError):
    """用户名或密码错误。"""


class UserNotFoundError(AuthError):
    """用户不存在。"""


class InvalidTokenError(AuthError):
    """刷新令牌无效或已过期。"""


class IncorrectPasswordError(AuthError):
    """当前密码不正确。"""
