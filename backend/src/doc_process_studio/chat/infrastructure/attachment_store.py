"""附件存储实现：委托 service/attachments 工具层。"""

from pathlib import Path

from ..application.ports import AttachmentStore
from ..schemas.attachment import ChatAttachment, ChatAttachmentMetadata
from ..service.attachments import (
    cleanup_expired_attachments,
    delete_attachments_for_conversation,
    resolve_attachment_path,
    save_generated_attachment,
    save_uploaded_attachment,
)


class FsAttachmentStore(AttachmentStore):
    """基于文件系统的附件存储。"""

    def resolve_path(self, attachment_id: str) -> tuple[ChatAttachmentMetadata | None, Path | None, bool]:
        return resolve_attachment_path(attachment_id)

    def save_uploaded(
        self,
        *,
        raw_bytes: bytes,
        conversation_id: str,
        skill_id: str,
        file_name: str,
        mime_type: str | None = None,
        extracted_text: str | None = None,
    ) -> ChatAttachment:
        return save_uploaded_attachment(
            raw_bytes=raw_bytes,
            conversation_id=conversation_id,
            skill_id=skill_id,
            file_name=file_name,
            mime_type=mime_type,
            extracted_text=extracted_text,
        )

    def save_generated(
        self,
        *,
        source_path: Path,
        conversation_id: str,
        skill_id: str,
        output_name: str | None = None,
        mime_type: str | None = None,
    ) -> ChatAttachment:
        return save_generated_attachment(
            source_path=source_path,
            conversation_id=conversation_id,
            skill_id=skill_id,
            output_name=output_name,
            mime_type=mime_type,
        )

    def delete_for_conversation(self, conversation_id: str) -> int:
        return delete_attachments_for_conversation(conversation_id)

    def cleanup_expired(self) -> None:
        cleanup_expired_attachments()
