"""对话 API 请求 Schema。

结构形状（消息 / 流式选项 / 会话 upsert / 标题更新）定义在应用层
``application.dtos``，本模块只做**再导出**并保持历史命名，保证既有导入方与
API 契约不变：``ChatMessageInput`` / ``ChatStreamRequest`` /
``ChatSessionUpsertRequest`` / ``ChatSessionTitleUpdateRequest``。
"""

from ...application.dtos.message import ChatMessage
from ...application.dtos.session import ChatSessionTitleUpdate, ChatSessionUpsert
from ...application.dtos.stream import ChatStreamOptions

# 历史命名再导出（API 契约沿用旧名）
ChatMessageInput = ChatMessage
ChatStreamRequest = ChatStreamOptions
ChatSessionUpsertRequest = ChatSessionUpsert
ChatSessionTitleUpdateRequest = ChatSessionTitleUpdate

__all__ = [
    "ChatMessageInput",
    "ChatSessionTitleUpdateRequest",
    "ChatSessionUpsertRequest",
    "ChatStreamRequest",
]
