import asyncio
import re
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from .config import settings
from .exceptions import OllamaNotConfiguredError
from .ollama import _build_api_url, build_timeout, fetch_remote_model_names

_CONTEXT_CACHE: dict[str, tuple[int, datetime]] = {}
_CACHE_LOCK = asyncio.Lock()
_WARMED_UP = False


def estimate_prompt_tokens(messages: list[dict[str, Any]]) -> int:
    if not messages:
        return 0

    total_chars = 0
    for message in messages:
        role = str(message.get("role", "") or "")
        content = str(message.get("content", "") or "")
        total_chars += len(role) + len(content)
        tool_calls = message.get("tool_calls")
        if isinstance(tool_calls, list):
            total_chars += len(str(tool_calls))

    estimated = int(total_chars / 3.4)
    return max(1, estimated)


def _extract_int_like(value: int | float | str | None) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, float):
        parsed = int(value)
        return parsed if parsed > 0 else None
    if isinstance(value, str):
        matched = re.search(r"(\d{3,})", value)
        if matched:
            parsed = int(matched.group(1))
            return parsed if parsed > 0 else None
    return None


def _extract_context_length(payload: dict[str, Any]) -> int | None:
    candidate_keys = [
        "context_length",
        "num_ctx",
        "num_ctx_train",
    ]
    for key in candidate_keys:
        parsed = _extract_int_like(payload.get(key))
        if parsed is not None:
            return parsed

    details = payload.get("details")
    if isinstance(details, dict):
        for key in candidate_keys:
            parsed = _extract_int_like(details.get(key))
            if parsed is not None:
                return parsed

    model_info = payload.get("model_info")
    if isinstance(model_info, dict):
        for key, value in model_info.items():
            normalized_key = str(key).lower()
            if "context" in normalized_key or "ctx" in normalized_key:
                parsed = _extract_int_like(value)
                if parsed is not None:
                    return parsed

    parameters = payload.get("parameters")
    if isinstance(parameters, str):
        matched = re.search(r"(?:num_ctx|context_length)\s*[:=]?\s*(\d+)", parameters)
        if matched:
            parsed = int(matched.group(1))
            return parsed if parsed > 0 else None

    return None


async def _fetch_model_context_length(model: str) -> int | None:
    if not model.strip():
        return None

    try:
        remote_url = _build_api_url("show")
    except OllamaNotConfiguredError:
        return None

    payload = {
        "model": model.strip(),
    }
    try:
        async with httpx.AsyncClient(timeout=build_timeout()) as client:
            response = await client.post(remote_url, json=payload)
            response.raise_for_status()
            response_payload = response.json()
    except (httpx.HTTPError, ValueError):
        return None

    if not isinstance(response_payload, dict):
        return None
    return _extract_context_length(response_payload)


async def _set_cached_context_length(model: str, context_length: int) -> None:
    async with _CACHE_LOCK:
        _CONTEXT_CACHE[model] = (context_length, datetime.now(UTC))


async def warmup_model_context_cache() -> None:
    global _WARMED_UP
    if _WARMED_UP:
        return
    if not settings.ollama_base_url:
        _WARMED_UP = True
        return

    try:
        model_names = await asyncio.wait_for(
            fetch_remote_model_names(),
            timeout=min(2.0, max(0.5, settings.ollama_timeout_seconds)),
        )
    except Exception:
        return

    semaphore = asyncio.Semaphore(max(1, settings.agent_executor_model_context_warmup_concurrency))

    async def _warm_single(model: str) -> None:
        async with semaphore:
            context_length = await _fetch_model_context_length(model)
            if context_length is None:
                return
            await _set_cached_context_length(model, context_length)

    await asyncio.gather(*[_warm_single(model) for model in model_names], return_exceptions=True)
    _WARMED_UP = True


def _is_cache_fresh(cached_at: datetime) -> bool:
    ttl_seconds = max(1, settings.agent_executor_model_context_cache_ttl_seconds)
    return datetime.now(UTC) - cached_at <= timedelta(seconds=ttl_seconds)


async def get_model_context_length(model: str) -> int:
    normalized_model = model.strip()
    if not normalized_model:
        return settings.agent_executor_default_context_length

    async with _CACHE_LOCK:
        cached = _CONTEXT_CACHE.get(normalized_model)
    if cached is not None:
        cached_length, cached_at = cached
        if _is_cache_fresh(cached_at):
            return cached_length

    async def _refresh() -> None:
        refreshed = await _fetch_model_context_length(normalized_model)
        if refreshed is None:
            return
        await _set_cached_context_length(normalized_model, refreshed)

    try:
        asyncio.create_task(_refresh())
    except RuntimeError:
        pass

    return settings.agent_executor_default_context_length
