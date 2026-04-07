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
    """返回聊天补全接口地址。"""
    return f"{get_ollama_base_url()}/v1/chat/completions"


def build_models_url() -> str:
    """返回模型列表接口地址。"""
    return f"{get_ollama_base_url()}/v1/models"


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
    tool_choice: str | dict[str, Any] | None = None,
) -> dict[str, Any]:
    """统一聊天补全 payload，减少各业务层重复拼装。"""
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
    if tool_choice is not None:
        payload["tool_choice"] = tool_choice
    return payload


async def post_chat_completion(
    *,
    model: str,
    messages: list[ChatMessageInput] | list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    tool_choice: str | dict[str, Any] | None = None,
) -> dict[str, Any]:
    """发送一次非流式聊天补全请求并返回 JSON。"""
    payload = build_chat_payload(
        model=model,
        messages=messages,
        stream=False,
        tools=tools,
        tool_choice=tool_choice,
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
    tool_choice: str | dict[str, Any] | None = None,
) -> AsyncIterator[dict[str, Any] | None]:
    """统一处理远端 SSE，返回解码后的 chunk，DONE 用 None 表示。"""
    payload = build_chat_payload(
        model=model,
        messages=messages,
        stream=True,
        tools=tools,
        tool_choice=tool_choice,
    )
    async with httpx.AsyncClient(timeout=build_timeout(stream=True)) as client:
        async with client.stream(
            "POST",
            build_chat_completion_url(),
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
                    yield None
                    return

                try:
                    yield json.loads(raw_data)
                except json.JSONDecodeError:
                    continue


def extract_first_message_content(response_payload: dict[str, Any]) -> str:
    """读取聊天补全首条消息正文。"""
    choices = response_payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""

    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        return ""

    message = first_choice.get("message")
    if not isinstance(message, dict):
        return ""

    return str(message.get("content", "")).strip()
