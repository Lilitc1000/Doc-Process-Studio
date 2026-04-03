import json
from collections.abc import AsyncIterator
from typing import Any

import httpx
from fastapi import UploadFile

from ...models.conversation.stream import ChatMessageInput, ChatStreamRequest
from ...settings import settings
from ..infra.ollama_client import (
    OllamaNotConfiguredError,
    stream_chat_completion,
)
from ..skill.registry import get_skill_interface
from ..skill.runtime import ensure_skill_context_for_request
from .file_context import build_uploaded_files_context


def format_sse_event(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def extract_delta_text(chunk_payload: dict[str, Any]) -> str:
    choices = chunk_payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""

    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        return ""

    delta = first_choice.get("delta")
    if not isinstance(delta, dict):
        return ""

    content = delta.get("content")
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_parts: list[str] = []
        for item in content:
            if not isinstance(item, dict):
                continue

            item_text = item.get("text")
            if isinstance(item_text, str):
                text_parts.append(item_text)

        return "".join(text_parts)

    return ""


def extract_finish_reason(chunk_payload: dict[str, Any]) -> str | None:
    choices = chunk_payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return None

    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        return None

    finish_reason = first_choice.get("finish_reason")
    if isinstance(finish_reason, str) and finish_reason:
        return finish_reason
    return None


def build_skill_prompt(skill_id: str) -> str:
    return get_skill_interface(skill_id).default_prompt


def build_upstream_messages(
    request: ChatStreamRequest,
    skill_context: str | None = None,
    uploaded_files_context: str | None = None,
) -> list[dict[str, str]]:
    system_message = ChatMessageInput(
        role="system",
        content=build_skill_prompt(request.skill_id),
    )
    upstream_messages = [system_message.model_dump()]
    if skill_context:
        upstream_messages.append(
            ChatMessageInput(
                role="system",
                content=skill_context,
            ).model_dump()
        )
    if uploaded_files_context:
        upstream_messages.append(
            ChatMessageInput(
                role="user",
                content=uploaded_files_context,
            ).model_dump()
        )

    upstream_messages.extend([message.model_dump() for message in request.messages])
    return upstream_messages


async def stream_remote_chat_completion(
    request: ChatStreamRequest,
    upload_files: list[UploadFile] | None = None,
) -> AsyncIterator[str]:
    if not settings.ollama_base_url:
        yield format_sse_event(
            {
                "type": "error",
                "message": "未配置 OLLAMA_BASE_URL，请检查后端环境配置文件。",
            }
        )
        return

    try:
        _, skill_context = await ensure_skill_context_for_request(request)
        upstream_messages = build_upstream_messages(
            request,
            skill_context=skill_context,
            uploaded_files_context=await build_uploaded_files_context(
                upload_files or []
            ),
        )
    except ValueError as exc:
        yield format_sse_event({"type": "error", "message": str(exc)})
        return

    try:
        async for chunk_payload in stream_chat_completion(
            model=request.model,
            messages=upstream_messages,
        ):
            if chunk_payload is None:
                yield format_sse_event({"type": "done"})
                return

            delta_text = extract_delta_text(chunk_payload)
            if delta_text:
                yield format_sse_event({"type": "delta", "content": delta_text})

            finish_reason = extract_finish_reason(chunk_payload)
            if finish_reason:
                yield format_sse_event(
                    {
                        "type": "done",
                        "finish_reason": finish_reason,
                    }
                )
                return
    except OllamaNotConfiguredError as exc:
        yield format_sse_event({"type": "error", "message": str(exc)})
    except httpx.HTTPStatusError as exc:
        error_message = (
            f"远程 Ollama 接口返回错误状态：{exc.response.status_code}"
        )
        try:
            error_payload = exc.response.json()
            if isinstance(error_payload, dict):
                detail = error_payload.get("error") or error_payload.get("message")
                if isinstance(detail, str) and detail.strip():
                    error_message = detail.strip()
        except ValueError:
            pass

        yield format_sse_event({"type": "error", "message": error_message})
    except httpx.HTTPError as exc:
        yield format_sse_event(
            {"type": "error", "message": f"连接远程 Ollama 失败：{exc}"}
        )

