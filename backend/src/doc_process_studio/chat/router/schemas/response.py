"""对话 API 响应 Schema。

结构形状（会话列表 / 会话详情 = 摘要 + 快照）定义在应用层 ``application.dtos``，
本模块只做**再导出**并保持历史命名 ``ChatSessionListResponse`` / ``ChatSessionDetail``，
保证既有导入方与 API 契约不变。
"""

from ...application.dtos.session import ChatSessionDetail, ChatSessionList

# 历史命名再导出（API 契约沿用旧名）
ChatSessionListResponse = ChatSessionList

__all__ = [
    "ChatSessionDetail",
    "ChatSessionListResponse",
]
