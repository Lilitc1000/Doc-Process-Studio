import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from ..models.chat import ChatMessageInput, ChatStreamRequest, ProcessingMode
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


def build_processing_mode_prompt(processing_mode: ProcessingMode) -> str:
    prompt_map: dict[ProcessingMode, str] = {
        "快速摘要": (
            "你是文档处理助手。请优先输出简洁、重点明确的摘要，"
            "先给核心结论，再补充关键细节。"
        ),
        "智能问答": (
            "你是文档处理助手。请围绕用户问题直接作答，"
            "结论清晰、条理明确，并在必要时引用上下文中的关键信息。"
        ),
        "结构化提取": (
            "你是文档处理助手。请优先提取结构化信息，"
            "尽量用分点、表格式思路或字段化表达输出结果。"
        ),
        "全文整理": (
            "你是文档处理助手。请对内容进行系统整理与归纳，"
            "保持层次清晰，适合继续阅读、复盘或二次加工。"
        ),
    }
    return prompt_map[processing_mode]


def build_upstream_messages(
    request: ChatStreamRequest,
) -> list[dict[str, str]]:
    system_message = ChatMessageInput(
        role="system",
        content=build_processing_mode_prompt(request.processing_mode),
    )
    return [
        system_message.model_dump(),
        *[message.model_dump() for message in request.messages],
    ]


async def stream_remote_chat_completion(
    request: ChatStreamRequest,
) -> AsyncIterator[str]:
    if not settings.ollama_base_url:
        yield format_sse_event(
            {
                "type": "error",
                "message": "未配置 APP_OLLAMA_BASE_URL，请检查后端环境配置文件。",
            }
        )
        return

    remote_url = (
        f"{settings.ollama_base_url.rstrip('/')}/v1/chat/completions"
    )
    payload = {
        "model": request.model,
        "messages": build_upstream_messages(request),
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
