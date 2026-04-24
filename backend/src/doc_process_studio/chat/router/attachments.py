from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..service.attachments import resolve_attachment_path

router = APIRouter(prefix="/api", tags=["attachments"])


def _build_attachment_download_response(attachment_id: str) -> FileResponse:
    metadata, attachment_path, is_expired = resolve_attachment_path(attachment_id)
    if is_expired:
        raise HTTPException(status_code=410, detail="该文件已过期，请重新生成。")

    if metadata is None or attachment_path is None:
        raise HTTPException(status_code=404, detail="未找到对应文件。")

    return FileResponse(
        attachment_path,
        media_type=metadata.mime_type,
        filename=metadata.name,
    )


@router.get("/attachments/{attachment_id}/download")
async def download_attachment(attachment_id: str) -> FileResponse:
    return _build_attachment_download_response(attachment_id)
