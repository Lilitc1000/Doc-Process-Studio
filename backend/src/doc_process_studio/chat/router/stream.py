from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

from ...common.security.security import get_current_user_id
from ..infrastructure.stream import stream_remote_chat_completion
from .schemas.request import ChatStreamRequest

router = APIRouter(
    prefix="/api",
    tags=["chat"],
    dependencies=[Depends(get_current_user_id)],
)


@router.post("/chat/stream")
async def stream_chat(
    payload: str = Form(...),
    files: list[UploadFile] = File(default=[]),
) -> StreamingResponse:
    try:
        request = ChatStreamRequest.model_validate_json(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    return StreamingResponse(
        stream_remote_chat_completion(request, files),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
