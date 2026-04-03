import json
from collections.abc import AsyncIterator
from typing import Any

import httpx
from fastapi import UploadFile

from ..models.chat import ChatMessageInput, ChatStreamRequest
from .file_context import build_uploaded_files_context
from .skill_runtime import ensure_skill_context_for_request
from .skill_registry import get_skill_interface
from ..settings import settings


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
    upstream_messages = [
        system_message.model_dump(),
    ]
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

    upstream_messages.extend(
        [message.model_dump() for message in request.messages]
    )
    return upstream_messages


async def stream_remote_chat_completion(
    request: ChatStreamRequest,
    upload_files: list[UploadFile] | None = None,
) -> AsyncIterator[str]:
    if not settings.ollama_base_url:
        yield format_sse_event(
            {
                "type": "error",
                "message": "未配置 APP_OLLAMA_BASE_URL，请检查后端环境配置文件。",
            }
        )
        return

    try:
        skill_state, skill_context = await ensure_skill_context_for_request(
            request
        )
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

    remote_url = (
        f"{settings.ollama_base_url.rstrip('/')}/v1/chat/completions"
    )
    payload = {
        "model": request.model,
        "messages": upstream_messages,
        "stream": True,
    }

    timeout = httpx.Timeout(
        connect=settings.ollama_timeout_seconds,
        read=None,
        write=settings.ollama_timeout_seconds,
        pool=settings.ollama_timeout_seconds,
    )

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST",
                remote_url,
                json=payload,
                headers={"Accept": "text/event-stream"},
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue

                    raw_data = line[5:].strip()
                    if not raw_data:
                        continue

                    if raw_data == "[DONE]":
                        yield format_sse_event({"type": "done"})
                        return

                    try:
                        chunk_payload = json.loads(raw_data)
                    except json.JSONDecodeError:
                        continue

                    delta_text = extract_delta_text(chunk_payload)
                    if delta_text:
                        yield format_sse_event(
                            {"type": "delta", "content": delta_text}
                        )

                    finish_reason = extract_finish_reason(chunk_payload)
                    if finish_reason:
                        yield format_sse_event(
                            {
                                "type": "done",
                                "finish_reason": finish_reason,
                            }
                        )
                        return
    except httpx.HTTPStatusError as exc:
        error_message = (
            f"远程 Ollama 接口返回错误状态：{exc.response.status_code}"
        )
        try:
            error_payload = exc.response.json()
            if isinstance(error_payload, dict):
                detail = error_payload.get("error") or error_payload.get(
                    "message"
                )
                if isinstance(detail, str) and detail.strip():
                    error_message = detail.strip()
        except ValueError:
            pass

        yield format_sse_event({"type": "error", "message": error_message})
    except httpx.HTTPError as exc:
        yield format_sse_event(
            {"type": "error", "message": f"连接远程 Ollama 失败：{exc}"}
        )
