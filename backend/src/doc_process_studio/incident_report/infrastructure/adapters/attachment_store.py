"""附件存储端口实现。

封装 chat.infrastructure.attachments 的跨域调用。
"""

from typing import Any

from ....chat.application.dtos.attachment import ChatAttachment
from ....chat.infrastructure.attachments import resolve_attachment_path, save_generated_attachment
from ...application.ports import AttachmentStore


class ChatAttachmentStore(AttachmentStore):
    """基于 chat.infrastructure.attachments 的附件存储。"""

    async def save_generated(
        self,
        *,
        source_path: Any,
        conversation_id: str,
        skill_id: str,
        output_name: str,
        mime_type: str,
    ) -> ChatAttachment:
        return save_generated_attachment(
            source_path=source_path,
            conversation_id=conversation_id,
            skill_id=skill_id,
            output_name=output_name,
            mime_type=mime_type,
        )

    async def resolve_path(self, attachment_id: str) -> tuple[Any, Any | None, bool]:
        return resolve_attachment_path(attachment_id)
