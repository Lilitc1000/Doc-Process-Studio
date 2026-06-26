"""LLM 流式聊天补全端口实现。

封装 core.ollama 和 chat.infrastructure.streaming 的跨域调用。
"""

import logging
from typing import Any

from ....chat.infrastructure.streaming import extract_delta_text, extract_done_reason
from ....common.infrastructure.ollama import stream_chat_completion
from ...application.ports import LLMStreamingPort

logger = logging.getLogger(__name__)


class OllamaLLMStreaming(LLMStreamingPort):
    """基于 Ollama 的 LLM 流式聊天补全。"""

    async def stream_chat(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
    ) -> tuple[str, str]:
        content_parts: list[str] = []
        done_reason = "stop"
        async for chunk_payload in stream_chat_completion(
            model=model,
            messages=messages,
            tools=[],
        ):
            if chunk_payload is None:
                break
            delta_text = extract_delta_text(chunk_payload)
            if delta_text:
                content_parts.append(delta_text)
            chunk_done_reason = extract_done_reason(chunk_payload)
            if chunk_done_reason:
                done_reason = chunk_done_reason
        return "".join(content_parts), done_reason
