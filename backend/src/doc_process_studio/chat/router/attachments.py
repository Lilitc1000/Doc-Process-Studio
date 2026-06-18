from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from ..application.attachment_service import AttachmentService
from ..domain.errors import AttachmentExpiredError, AttachmentNotFoundError, ChatError
from ..infrastructure.dependencies import get_attachment_service
from ...core.security import get_current_user_id

router = APIRouter(prefix="/api", tags=["attachments"])


def _handle_attachment_error(exc: ChatError) -> HTTPException:
    if isinstance(exc, AttachmentExpiredError):
        return HTTPException(status_code=410, detail=str(exc))
    if isinstance(exc, AttachmentNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=400, detail=str(exc))


@router.get("/attachments/{attachment_id}/download")
async def download_attachment(
    attachment_id: str,
    user_id: str = Depends(get_current_user_id),
    service: AttachmentService = Depends(get_attachment_service),
) -> FileResponse:
    try:
        return service.build_download_response(attachment_id)
    except ChatError as exc:
        raise _handle_attachment_error(exc) from exc
