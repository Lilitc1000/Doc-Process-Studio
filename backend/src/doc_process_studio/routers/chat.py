from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ..models.chat import ChatStreamRequest
from ..services.ollama_chat import stream_remote_chat_completion

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat/stream")
async def stream_chat(request: ChatStreamRequest) -> StreamingResponse:
    return StreamingResponse(
        stream_remote_chat_completion(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
