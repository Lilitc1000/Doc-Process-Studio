"""系统领域异常。

所有系统域业务错误继承 SystemError，应用层抛出后由 router 映射为 HTTP 状态码。
"""


class SystemError(Exception):
    """系统域异常基类。"""


class TraceNotFoundError(SystemError):
    """Agent trace 记录不存在。"""
