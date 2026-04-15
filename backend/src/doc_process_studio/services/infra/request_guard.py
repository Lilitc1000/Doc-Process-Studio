import asyncio
import time
from collections import deque
from contextlib import asynccontextmanager
from typing import AsyncIterator

from ...settings import settings
from .dtutils import normalize_tenant_id

_global_semaphore: asyncio.Semaphore | None = None
_tenant_semaphores: dict[str, asyncio.Semaphore] = {}
_tenant_rate_windows: dict[str, deque[float]] = {}
_guard_lock = asyncio.Lock()


class RequestGuardError(RuntimeError):
    pass


async def _get_global_semaphore() -> asyncio.Semaphore:
    global _global_semaphore
    async with _guard_lock:
        if _global_semaphore is None:
            _global_semaphore = asyncio.Semaphore(max(1, settings.request_max_concurrent_global))
        return _global_semaphore


async def _get_tenant_semaphore(tenant_id: str) -> asyncio.Semaphore:
    normalized_tenant_id = normalize_tenant_id(tenant_id)
    async with _guard_lock:
        semaphore = _tenant_semaphores.get(normalized_tenant_id)
        if semaphore is None:
            semaphore = asyncio.Semaphore(max(1, settings.request_max_concurrent_per_tenant))
            _tenant_semaphores[normalized_tenant_id] = semaphore
        return semaphore


async def _check_rate_limit(tenant_id: str) -> None:
    normalized_tenant_id = normalize_tenant_id(tenant_id)
    window_seconds = max(1, settings.request_rate_limit_window_seconds)
    max_requests = max(1, settings.request_rate_limit_max_requests_per_window)
    now = time.monotonic()

    async with _guard_lock:
        request_window = _tenant_rate_windows.get(normalized_tenant_id)
        if request_window is None:
            request_window = deque()
            _tenant_rate_windows[normalized_tenant_id] = request_window

        while request_window and (now - request_window[0]) > window_seconds:
            request_window.popleft()

        if len(request_window) >= max_requests:
            raise RequestGuardError(
                f"租户 `{normalized_tenant_id}` 请求过于频繁，请稍后重试。"
            )

        request_window.append(now)


@asynccontextmanager
async def guard_request_slot(tenant_id: str) -> AsyncIterator[None]:
    """请求级并发与速率保护：全局 + 租户双层隔离。"""
    await _check_rate_limit(tenant_id)

    wait_timeout = max(0.1, settings.request_queue_wait_timeout_seconds)
    global_semaphore = await _get_global_semaphore()
    tenant_semaphore = await _get_tenant_semaphore(tenant_id)

    acquired_global = False
    acquired_tenant = False
    try:
        await asyncio.wait_for(global_semaphore.acquire(), timeout=wait_timeout)
        acquired_global = True
        await asyncio.wait_for(tenant_semaphore.acquire(), timeout=wait_timeout)
        acquired_tenant = True
        yield
    except TimeoutError as exc:
        raise RequestGuardError("系统当前繁忙，请稍后重试。") from exc
    finally:
        if acquired_tenant:
            tenant_semaphore.release()
        if acquired_global:
            global_semaphore.release()

