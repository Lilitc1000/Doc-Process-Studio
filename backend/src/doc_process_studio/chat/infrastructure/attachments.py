import hashlib
import logging
import mimetypes
import shutil
import time
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

from ...common.infrastructure.config import settings
from ...common.utils.dtutils import to_utc8, utcnow
from ..application.dtos.attachment import ChatAttachment, ChatAttachmentMetadata

logger = logging.getLogger(__name__)

_last_cleanup_timestamp: float = 0.0
_cleanup_interval_seconds: float = 300.0


def _should_run_cleanup() -> bool:
    global _last_cleanup_timestamp
    now = time.monotonic()
    if now - _last_cleanup_timestamp >= _cleanup_interval_seconds:
        _last_cleanup_timestamp = now
        return True
    return False


def get_generated_attachments_root() -> Path:
    """返回受控产物目录，并在首次使用时自动创建。"""
    root = Path(settings.generated_attachments_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _build_attachment_dir(attachment_id: str) -> Path:
    return get_generated_attachments_root() / attachment_id


def _build_metadata_path(attachment_id: str) -> Path:
    return _build_attachment_dir(attachment_id) / "metadata.json"


def _build_context_path(attachment_id: str) -> Path:
    return _build_attachment_dir(attachment_id) / "context.txt"


def _build_size_label(size_bytes: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    size = float(size_bytes)
    unit_index = 0

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    return f"{size:.1f} {units[unit_index]}"


def _build_content_hash(raw_bytes: bytes) -> str:
    return hashlib.sha256(raw_bytes).hexdigest()


def _build_chat_attachment_from_metadata(metadata: ChatAttachmentMetadata) -> ChatAttachment:
    return ChatAttachment(
        attachment_id=metadata.attachment_id,
        name=metadata.name,
        source=metadata.source,
        mime_type=metadata.mime_type,
        size_bytes=metadata.size_bytes,
        size_label=_build_size_label(metadata.size_bytes),
        download_url=f"/api/attachments/{metadata.attachment_id}/download",
        expires_at=to_utc8(metadata.expires_at),
    )


def cleanup_expired_attachments() -> None:
    """清理已过期或损坏的附件目录。"""
    now = utcnow()
    root = get_generated_attachments_root()

    for attachment_dir in root.iterdir():
        if not attachment_dir.is_dir():
            continue

        metadata_path = attachment_dir / "metadata.json"
        if not metadata_path.is_file():
            shutil.rmtree(attachment_dir, ignore_errors=True)
            continue

        try:
            metadata = ChatAttachmentMetadata.model_validate_json(metadata_path.read_text(encoding="utf-8"))
        except Exception:
            logger.debug("Failed to parse attachment metadata in %s, removing", attachment_dir, exc_info=True)
            shutil.rmtree(attachment_dir, ignore_errors=True)
            continue

        if metadata.expires_at <= now:
            shutil.rmtree(attachment_dir, ignore_errors=True)


def _save_session_attachment(
    *,
    raw_bytes: bytes,
    conversation_id: str,
    skill_id: str,
    output_name: str,
    mime_type: str | None,
    source: str,
    content_hash: str | None = None,
    extracted_text: str | None = None,
) -> ChatAttachment:
    """保存会话附件到受控目录，并返回前端可直接消费的信息。"""
    if _should_run_cleanup():
        cleanup_expired_attachments()

    attachment_id = uuid4().hex
    attachment_dir = _build_attachment_dir(attachment_id)
    attachment_dir.mkdir(parents=True, exist_ok=True)

    resolved_name = output_name
    target_path = attachment_dir / resolved_name
    target_path.write_bytes(raw_bytes)

    resolved_mime_type = mime_type or mimetypes.guess_type(resolved_name)[0]
    if not resolved_mime_type:
        resolved_mime_type = "application/octet-stream"

    stat_result = target_path.stat()
    created_at = utcnow()
    expires_at = created_at + timedelta(seconds=settings.generated_attachment_ttl_seconds)

    metadata = ChatAttachmentMetadata(
        attachment_id=attachment_id,
        conversation_id=conversation_id,
        skill_id=skill_id,
        source=source,
        content_hash=content_hash,
        name=resolved_name,
        mime_type=resolved_mime_type,
        size_bytes=stat_result.st_size,
        created_at=created_at,
        expires_at=expires_at,
    )
    _build_metadata_path(attachment_id).write_text(
        metadata.model_dump_json(indent=2),
        encoding="utf-8",
    )
    if extracted_text is not None:
        _build_context_path(attachment_id).write_text(
            extracted_text,
            encoding="utf-8",
        )

    return ChatAttachment(
        attachment_id=attachment_id,
        name=resolved_name,
        source=source,
        mime_type=resolved_mime_type,
        size_bytes=stat_result.st_size,
        size_label=_build_size_label(stat_result.st_size),
        download_url=f"/api/attachments/{attachment_id}/download",
        expires_at=to_utc8(expires_at),
    )


def save_generated_attachment(
    *,
    source_path: Path,
    conversation_id: str,
    skill_id: str,
    output_name: str | None = None,
    mime_type: str | None = None,
) -> ChatAttachment:
    """保存脚本产物到受控目录，并返回前端可直接消费的信息。"""
    resolved_name = output_name or source_path.name
    return _save_session_attachment(
        raw_bytes=source_path.read_bytes(),
        conversation_id=conversation_id,
        skill_id=skill_id,
        output_name=resolved_name,
        mime_type=mime_type,
        source="generated",
    )


def _find_reusable_uploaded_attachment(
    *,
    conversation_id: str,
    content_hash: str,
) -> ChatAttachment | None:
    root = get_generated_attachments_root()

    for attachment_dir in root.iterdir():
        if not attachment_dir.is_dir():
            continue

        metadata_path = attachment_dir / "metadata.json"
        if not metadata_path.is_file():
            continue

        try:
            metadata = ChatAttachmentMetadata.model_validate_json(metadata_path.read_text(encoding="utf-8"))
        except Exception:
            logger.debug("Failed to parse attachment metadata in %s", attachment_dir, exc_info=True)
            continue

        if metadata.expires_at <= utcnow():
            continue

        if metadata.source != "uploaded":
            continue

        if metadata.conversation_id != conversation_id:
            continue

        if metadata.content_hash != content_hash:
            continue

        attachment_path = attachment_dir / metadata.name
        if not attachment_path.is_file():
            continue

        return _build_chat_attachment_from_metadata(metadata)

    return None


def save_uploaded_attachment(
    *,
    raw_bytes: bytes,
    conversation_id: str,
    skill_id: str,
    file_name: str,
    mime_type: str | None = None,
    extracted_text: str | None = None,
) -> ChatAttachment:
    """保存用户上传文件到受控目录，并返回统一附件信息。"""
    content_hash = _build_content_hash(raw_bytes)
    reusable_attachment = _find_reusable_uploaded_attachment(
        conversation_id=conversation_id,
        content_hash=content_hash,
    )
    if reusable_attachment is not None:
        return reusable_attachment

    return _save_session_attachment(
        raw_bytes=raw_bytes,
        conversation_id=conversation_id,
        skill_id=skill_id,
        output_name=file_name,
        mime_type=mime_type,
        source="uploaded",
        content_hash=content_hash,
        extracted_text=extracted_text,
    )


def resolve_attachment_path(
    attachment_id: str,
) -> tuple[ChatAttachmentMetadata | None, Path | None, bool]:
    """读取附件信息并判断是否过期。"""
    metadata_path = _build_metadata_path(attachment_id)
    if not metadata_path.is_file():
        if _should_run_cleanup():
            cleanup_expired_attachments()
        return None, None, False

    try:
        metadata = ChatAttachmentMetadata.model_validate_json(metadata_path.read_text(encoding="utf-8"))
    except Exception:
        logger.debug("Failed to parse attachment metadata for %s", attachment_id, exc_info=True)
        shutil.rmtree(_build_attachment_dir(attachment_id), ignore_errors=True)
        if _should_run_cleanup():
            cleanup_expired_attachments()
        return None, None, False

    if metadata.expires_at <= utcnow():
        shutil.rmtree(_build_attachment_dir(attachment_id), ignore_errors=True)
        if _should_run_cleanup():
            cleanup_expired_attachments()
        return None, None, True

    attachment_path = _build_attachment_dir(attachment_id) / metadata.name
    if not attachment_path.is_file():
        shutil.rmtree(_build_attachment_dir(attachment_id), ignore_errors=True)
        if _should_run_cleanup():
            cleanup_expired_attachments()
        return None, None, False

    if _should_run_cleanup():
        cleanup_expired_attachments()
    return metadata, attachment_path, False


def load_uploaded_attachment_context(
    attachment_id: str,
) -> tuple[ChatAttachmentMetadata | None, str | None, bool]:
    """读取已持久化上传文件的提取文本，仅对 uploaded 来源生效。"""
    metadata, _, is_expired = resolve_attachment_path(attachment_id)
    if is_expired or metadata is None:
        return None, None, is_expired

    if metadata.source != "uploaded":
        return metadata, None, False

    context_path = _build_context_path(attachment_id)
    if not context_path.is_file():
        return metadata, None, False

    try:
        return metadata, context_path.read_text(encoding="utf-8"), False
    except OSError:
        return metadata, None, False


def delete_attachments_for_conversation(conversation_id: str) -> int:
    """删除指定会话关联的全部附件目录，返回删除数量。"""
    if _should_run_cleanup():
        cleanup_expired_attachments()
    root = get_generated_attachments_root()
    deleted_count = 0

    for attachment_dir in root.iterdir():
        if not attachment_dir.is_dir():
            continue

        metadata_path = attachment_dir / "metadata.json"
        if not metadata_path.is_file():
            shutil.rmtree(attachment_dir, ignore_errors=True)
            continue

        try:
            metadata = ChatAttachmentMetadata.model_validate_json(metadata_path.read_text(encoding="utf-8"))
        except Exception:
            logger.debug("Failed to parse attachment metadata in %s during cleanup", attachment_dir, exc_info=True)
            shutil.rmtree(attachment_dir, ignore_errors=True)
            continue

        if metadata.conversation_id != conversation_id:
            continue

        shutil.rmtree(attachment_dir, ignore_errors=True)
        deleted_count += 1

    return deleted_count
