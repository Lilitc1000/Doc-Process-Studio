import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from .config import settings
from .exceptions import OllamaNotConfiguredError


def get_ollama_base_url() -> str:
    if not settings.ollama_base_url:
        raise OllamaNotConfiguredError("未配置 OLLAMA_BASE_URL，请检查后端环境配置文件。")
    return settings.ollama_base_url.rstrip("/")


def _build_api_url(path: str) -> str:
    return f"{get_ollama_base_url()}/api/{path}"


def build_timeout(*, stream: bool = False) -> httpx.Timeout:
    return httpx.Timeout(
        connect=settings.ollama_timeout_seconds,
        read=settings.ollama_stream_idle_timeout_seconds if stream else settings.ollama_timeout_seconds,
        write=settings.ollama_timeout_seconds,
        pool=settings.ollama_timeout_seconds,
    )


def build_chat_payload(
    *,
    model: str,
    messages: list[Any],
    stream: bool,
    tools: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    normalized_messages: list[dict[str, Any]] = []
    for message in messages:
        if hasattr(message, "model_dump"):
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
    messages: list[Any],
    tools: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    payload = build_chat_payload(
        model=model,
        messages=messages,
        stream=False,
        tools=tools,
    )
    async with httpx.AsyncClient(timeout=build_timeout()) as client:
        response = await client.post(
            _build_api_url("chat"),
            json=payload,
        )
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result


async def stream_chat_completion(
    *,
    model: str,
    messages: list[Any],
    tools: list[dict[str, Any]] | None = None,
) -> AsyncIterator[dict[str, Any] | None]:
    payload = build_chat_payload(
        model=model,
        messages=messages,
        stream=True,
        tools=tools,
    )
    async with (
        httpx.AsyncClient(timeout=build_timeout(stream=True)) as client,
        client.stream(
            "POST",
            _build_api_url("chat"),
            json=payload,
        ) as response,
    ):
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
    message = response_payload.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str):
            return content.strip()
    return ""


async def fetch_remote_model_names() -> list[str]:
    from fastapi import HTTPException

    try:
        remote_url = _build_api_url("tags")
    except OllamaNotConfiguredError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc

    try:
        async with httpx.AsyncClient(timeout=build_timeout()) as client:
            response = await client.get(remote_url)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"读取远程 Ollama 模型列表失败：{exc}",
        ) from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=502,
            detail="远程 Ollama 返回了无法解析的 JSON 数据",
        ) from exc

    model_names = extract_model_names(payload)
    if not model_names:
        raise HTTPException(
            status_code=502,
            detail="远程 Ollama 未返回可用模型名称",
        )

    return model_names


def extract_model_names(payload: dict[str, Any] | list[Any]) -> list[str]:
    from .ollama_models import UpstreamOllamaModelRecord

    if isinstance(payload, dict):
        if isinstance(payload.get("models"), list):
            raw_models = payload["models"]
        elif isinstance(payload.get("data"), list):
            raw_models = payload["data"]
        else:
            raw_models = []
    elif isinstance(payload, list):
        raw_models = payload
    else:
        raw_models = []

    model_names: list[str] = []
    for item in raw_models:
        if not isinstance(item, dict):
            continue

        normalized_item = UpstreamOllamaModelRecord.model_validate(item)
        name = normalized_item.resolved_name()
        if name:
            model_names.append(name)

    return list(dict.fromkeys(model_names))
