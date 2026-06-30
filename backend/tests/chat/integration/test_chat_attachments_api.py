from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

import doc_process_studio.chat.infrastructure.attachments as attachments_module
from doc_process_studio.chat.application.dtos.attachment import ChatAttachmentMetadata


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


def test_delete_attachments_for_conversation_removes_only_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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

    deleted_count = attachments_module.delete_attachments_for_conversation("conversation-a")

    assert deleted_count == 1
    assert not (tmp_path / "attachment-a").exists()
    assert (tmp_path / "attachment-b").exists()


def test_save_uploaded_attachment_reuses_same_content_in_same_conversation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        attachments_module.settings,
        "generated_attachments_dir",
        str(tmp_path),
    )

    first_attachment = attachments_module.save_uploaded_attachment(
        raw_bytes=b"same-content",
        conversation_id="conversation-a",
        skill_id="document-assistant",
        file_name="first.txt",
        mime_type="text/plain",
        extracted_text="same-content",
    )
    second_attachment = attachments_module.save_uploaded_attachment(
        raw_bytes=b"same-content",
        conversation_id="conversation-a",
        skill_id="document-assistant",
        file_name="first.txt",
        mime_type="text/plain",
        extracted_text="same-content",
    )

    assert first_attachment.attachment_id == second_attachment.attachment_id
    attachment_dirs = [path for path in tmp_path.iterdir() if path.is_dir()]
    assert len(attachment_dirs) == 1


def test_save_uploaded_attachment_does_not_reuse_across_conversations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        attachments_module.settings,
        "generated_attachments_dir",
        str(tmp_path),
    )

    first_attachment = attachments_module.save_uploaded_attachment(
        raw_bytes=b"same-content",
        conversation_id="conversation-a",
        skill_id="document-assistant",
        file_name="shared.txt",
        mime_type="text/plain",
        extracted_text="same-content",
    )
    second_attachment = attachments_module.save_uploaded_attachment(
        raw_bytes=b"same-content",
        conversation_id="conversation-b",
        skill_id="document-assistant",
        file_name="shared.txt",
        mime_type="text/plain",
        extracted_text="same-content",
    )

    assert first_attachment.attachment_id != second_attachment.attachment_id
