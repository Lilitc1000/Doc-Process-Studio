import mimetypes
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from ...models.conversation.artifacts import (
    GeneratedArtifact,
    GeneratedArtifactMetadata,
)
from ...settings import settings


def _utcnow() -> datetime:
    return datetime.now(UTC)


def get_generated_artifacts_root() -> Path:
    """返回受控产物目录，并在首次使用时自动创建。"""
    root = Path(settings.generated_artifacts_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _build_artifact_dir(artifact_id: str) -> Path:
    return get_generated_artifacts_root() / artifact_id


def _build_metadata_path(artifact_id: str) -> Path:
    return _build_artifact_dir(artifact_id) / "metadata.json"


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


def cleanup_expired_artifacts() -> None:
    """清理已过期或损坏的产物目录。"""
    now = _utcnow()
    root = get_generated_artifacts_root()

    for artifact_dir in root.iterdir():
        if not artifact_dir.is_dir():
            continue

        metadata_path = artifact_dir / "metadata.json"
        if not metadata_path.is_file():
            shutil.rmtree(artifact_dir, ignore_errors=True)
            continue

        try:
            metadata = GeneratedArtifactMetadata.model_validate_json(
                metadata_path.read_text(encoding="utf-8")
            )
        except Exception:
            shutil.rmtree(artifact_dir, ignore_errors=True)
            continue

        if metadata.expires_at <= now:
            shutil.rmtree(artifact_dir, ignore_errors=True)


def save_generated_artifact(
    *,
    source_path: Path,
    conversation_id: str,
    skill_id: str,
    output_name: str | None = None,
    mime_type: str | None = None,
) -> GeneratedArtifact:
    """保存脚本产物到受控目录，并返回前端可直接消费的信息。"""
    cleanup_expired_artifacts()

    artifact_id = uuid4().hex
    artifact_dir = _build_artifact_dir(artifact_id)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    resolved_name = output_name or source_path.name
    target_path = artifact_dir / resolved_name
    shutil.copy2(source_path, target_path)

    resolved_mime_type = mime_type or mimetypes.guess_type(resolved_name)[0]
    if not resolved_mime_type:
        resolved_mime_type = "application/octet-stream"

    stat_result = target_path.stat()
    created_at = _utcnow()
    expires_at = created_at + timedelta(
        seconds=settings.generated_artifact_ttl_seconds
    )

    metadata = GeneratedArtifactMetadata(
        artifact_id=artifact_id,
        conversation_id=conversation_id,
        skill_id=skill_id,
        name=resolved_name,
        mime_type=resolved_mime_type,
        size_bytes=stat_result.st_size,
        created_at=created_at,
        expires_at=expires_at,
    )
    _build_metadata_path(artifact_id).write_text(
        metadata.model_dump_json(indent=2),
        encoding="utf-8",
    )

    return GeneratedArtifact(
        artifact_id=artifact_id,
        name=resolved_name,
        mime_type=resolved_mime_type,
        size_bytes=stat_result.st_size,
        size_label=_build_size_label(stat_result.st_size),
        download_url=f"/api/artifacts/{artifact_id}/download",
        expires_at=expires_at,
    )


def resolve_generated_artifact_path(
    artifact_id: str,
) -> tuple[GeneratedArtifactMetadata | None, Path | None, bool]:
    """读取产物信息并判断是否过期。"""
    metadata_path = _build_metadata_path(artifact_id)
    if not metadata_path.is_file():
        cleanup_expired_artifacts()
        return None, None, False

    try:
        metadata = GeneratedArtifactMetadata.model_validate_json(
            metadata_path.read_text(encoding="utf-8")
        )
    except Exception:
        shutil.rmtree(_build_artifact_dir(artifact_id), ignore_errors=True)
        cleanup_expired_artifacts()
        return None, None, False

    if metadata.expires_at <= _utcnow():
        shutil.rmtree(_build_artifact_dir(artifact_id), ignore_errors=True)
        cleanup_expired_artifacts()
        return None, None, True

    artifact_path = _build_artifact_dir(artifact_id) / metadata.name
    if not artifact_path.is_file():
        shutil.rmtree(_build_artifact_dir(artifact_id), ignore_errors=True)
        cleanup_expired_artifacts()
        return None, None, False

    cleanup_expired_artifacts()
    return metadata, artifact_path, False
