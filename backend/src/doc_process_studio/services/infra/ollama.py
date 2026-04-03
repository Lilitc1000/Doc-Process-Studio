from typing import Any

import httpx
from fastapi import HTTPException

from ...models.system.ollama import UpstreamOllamaModelRecord
from .ollama_client import (
    OllamaNotConfiguredError,
    build_models_url,
    build_timeout,
)


def extract_model_names(payload: Any) -> list[str]:
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

    # 保持原始顺序去重，避免远端重复模型名污染下拉框。
    return list(dict.fromkeys(model_names))


async def fetch_remote_model_names() -> list[str]:
    try:
        remote_url = build_models_url()
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

