"""附件用例服务。"""

from pathlib import Path

from fastapi.responses import FileResponse

from ..domain.errors import AttachmentExpiredError, AttachmentNotFoundError
from .dtos.attachment import ChatAttachment, ChatAttachmentMetadata
from .ports import AttachmentStore


class AttachmentService:
    """附件用例服务：解析附件下载响应、保存上传/生成产物。"""

    def __init__(self, store: AttachmentStore) -> None:
        self._store = store

    def build_download_response(self, attachment_id: str) -> FileResponse:
        metadata, attachment_path, is_expired = self._store.resolve_path(attachment_id)
        if is_expired:
            raise AttachmentExpiredError("该文件已过期，请重新生成。")
        if metadata is None or attachment_path is None:
            raise AttachmentNotFoundError("未找到对应文件。")
        return FileResponse(
            attachment_path,
            media_type=metadata.mime_type,
            filename=metadata.name,
        )

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
        return self._store.save_uploaded(
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
        return self._store.save_generated(
            source_path=source_path,
            conversation_id=conversation_id,
            skill_id=skill_id,
            output_name=output_name,
            mime_type=mime_type,
        )

    def resolve_path(self, attachment_id: str) -> tuple[ChatAttachmentMetadata | None, Path | None, bool]:
        return self._store.resolve_path(attachment_id)
