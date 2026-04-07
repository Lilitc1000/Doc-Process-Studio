from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ...services.chat.artifacts import resolve_generated_artifact_path

router = APIRouter(prefix="/api", tags=["artifacts"])


@router.get("/artifacts/{artifact_id}/download")
async def download_generated_artifact(artifact_id: str) -> FileResponse:
    metadata, artifact_path, is_expired = resolve_generated_artifact_path(artifact_id)
    if is_expired:
        raise HTTPException(status_code=410, detail="该文件已过期，请重新生成。")

    if metadata is None or artifact_path is None:
        raise HTTPException(status_code=404, detail="未找到对应文件。")

    return FileResponse(
        artifact_path,
        media_type=metadata.mime_type,
        filename=metadata.name,
    )
