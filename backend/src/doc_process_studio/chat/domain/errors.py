"""Chat 域领域异常。"""


class ChatError(Exception):
    """Chat 域异常基类。"""


class SessionNotFoundError(ChatError):
    """会话不存在。"""


class SessionAccessDeniedError(ChatError):
    """无权访问该会话。"""


class AttachmentNotFoundError(ChatError):
    """附件不存在。"""


class AttachmentExpiredError(ChatError):
    """附件已过期。"""
