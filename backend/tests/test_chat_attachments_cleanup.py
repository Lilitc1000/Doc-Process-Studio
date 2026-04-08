from datetime import UTC, datetime, timedelta
from pathlib import Path

from doc_process_studio.models.conversation.attachments import ChatAttachmentMetadata
from doc_process_studio.services.chat import attachments as attachments_module


def _write_attachment_dir(
    root: Path,
    *,
    attachment_id: str,
    conversation_id: str,
) -> None:
    attachment_dir = root / attachment_id
    attachment_dir.mkdir(parents=True, exist_ok=True)
    metadata = ChatAttachmentMetadata(
        attachment_id=attachment_id,
        conversation_id=conversation_id,
        skill_id="document-assistant",
        source="uploaded",
        name=f"{attachment_id}.txt",
        mime_type="text/plain",
        size_bytes=3,
        created_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    (attachment_dir / "metadata.json").write_text(
        metadata.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (attachment_dir / f"{attachment_id}.txt").write_text("abc", encoding="utf-8")


def test_delete_attachments_for_conversation_removes_only_target(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        attachments_module.settings,
        "generated_attachments_dir",
        str(tmp_path),
    )

    _write_attachment_dir(
        tmp_path,
        attachment_id="attachment-a",
        conversation_id="conversation-a",
    )
    _write_attachment_dir(
        tmp_path,
        attachment_id="attachment-b",
        conversation_id="conversation-b",
    )

    deleted_count = attachments_module.delete_attachments_for_conversation(
        "conversation-a"
    )

    assert deleted_count == 1
    assert not (tmp_path / "attachment-a").exists()
    assert (tmp_path / "attachment-b").exists()
