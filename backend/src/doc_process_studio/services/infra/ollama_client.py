import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from ...models.conversation.stream import ChatMessageInput
from ...settings import settings


class OllamaNotConfiguredError(RuntimeError):
    """远端 Ollama 未配置时抛出的异常。"""


def get_ollama_base_url() -> str:
    """统一读取远端 Ollama 地址，避免各服务重复拼文案。"""
    if not settings.ollama_base_url:
        raise OllamaNotConfiguredError(
            "未配置 OLLAMA_BASE_URL，请检查后端环境配置文件。"
        )
    return settings.ollama_base_url.rstrip("/")


def build_chat_completion_url() -> str:
    """返回 Ollama 原生聊天接口地址。"""
    return f"{get_ollama_base_url()}/api/chat"


def build_models_url() -> str:
    """返回 Ollama 原生模型列表接口地址。"""
    return f"{get_ollama_base_url()}/api/tags"


def build_model_show_url() -> str:
    """返回 Ollama 原生模型详情接口地址。"""
    return f"{get_ollama_base_url()}/api/show"


def build_timeout(*, stream: bool = False) -> httpx.Timeout:
    """统一远端调用超时策略。"""
    return httpx.Timeout(
        connect=settings.ollama_timeout_seconds,
        read=None if stream else settings.ollama_timeout_seconds,
        write=settings.ollama_timeout_seconds,
        pool=settings.ollama_timeout_seconds,
    )


def build_chat_payload(
    *,
    model: str,
    messages: list[ChatMessageInput] | list[dict[str, Any]],
    stream: bool,
    tools: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """统一 Ollama 原生 /api/chat payload，减少各业务层重复拼装。"""
    normalized_messages: list[dict[str, Any]] = []
    for message in messages:
        if isinstance(message, ChatMessageInput):
            normalized_messages.append(message.model_dump())
            continue
        normalized_messages.append(message)

    payload: dict[str, Any] = {
        "model": model,
        "stream": stream,
        "messages": normalized_messages,
    }
    if tools:
        payload["tools"] = tools
    return payload


async def post_chat_completion(
    *,
    model: str,
    messages: list[ChatMessageInput] | list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """发送一次非流式聊天补全请求并返回 JSON。"""
    payload = build_chat_payload(
        model=model,
        messages=messages,
        stream=False,
        tools=tools,
    )
    async with httpx.AsyncClient(timeout=build_timeout()) as client:
        response = await client.post(
            build_chat_completion_url(),
            json=payload,
        )
        response.raise_for_status()
        return response.json()


async def stream_chat_completion(
    *,
    model: str,
    messages: list[ChatMessageInput] | list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
) -> AsyncIterator[dict[str, Any] | None]:
    """统一处理 Ollama 原生流式响应，返回解码后的 JSON chunk。"""
    payload = build_chat_payload(
        model=model,
        messages=messages,
        stream=True,
        tools=tools,
    )
    async with httpx.AsyncClient(timeout=build_timeout(stream=True)) as client:
        async with client.stream(
            "POST",
            build_chat_completion_url(),
            json=payload,
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue

                raw_data = line.strip()
                if not raw_data:
                    continue

                try:
                    yield json.loads(raw_data)
                except json.JSONDecodeError:
                    continue


def extract_first_message_content(response_payload: dict[str, Any]) -> str:
    """读取 Ollama 原生响应中的首条正文。"""
    message = response_payload.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str):
            return content.strip()
    return ""
