"""对话状态存储实现：委托 skill 域 conversation_store。"""

from ...skill.infrastructure.conversation_store import clear_conversation_state
from ..application.ports import ConversationStateStore


class SkillConversationStateStore(ConversationStateStore):
    """基于 skill 域 conversation_store 的对话状态存储。"""

    async def clear_state(self, conversation_id: str) -> bool:
        return await clear_conversation_state(conversation_id)
