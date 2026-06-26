import asyncio

import pytest

from doc_process_studio.common.middleware import request_guard as guard_module


def _reset_guard_state() -> None:
    guard_module._global_semaphore = None
    guard_module._tenant_semaphores.clear()
    guard_module._tenant_rate_windows.clear()


async def test_request_guard_rejects_when_rate_limit_exceeded(monkeypatch) -> None:
    _reset_guard_state()
    monkeypatch.setattr(
        guard_module.settings,
        "request_rate_limit_window_seconds",
        60,
    )
    monkeypatch.setattr(
        guard_module.settings,
        "request_rate_limit_max_requests_per_window",
        2,
    )
    monkeypatch.setattr(guard_module.settings, "request_max_concurrent_global", 8)
    monkeypatch.setattr(guard_module.settings, "request_max_concurrent_per_tenant", 8)
    monkeypatch.setattr(guard_module.settings, "request_queue_wait_timeout_seconds", 0.5)

    async with guard_module.guard_request_slot("tenant-a"):
        pass
    async with guard_module.guard_request_slot("tenant-a"):
        pass
    with pytest.raises(guard_module.RequestGuardError, match="请求过于频繁"):
        async with guard_module.guard_request_slot("tenant-a"):
            pass


async def test_request_guard_rejects_when_queue_wait_timeout(monkeypatch) -> None:
    _reset_guard_state()
    monkeypatch.setattr(
        guard_module.settings,
        "request_rate_limit_window_seconds",
        60,
    )
    monkeypatch.setattr(
        guard_module.settings,
        "request_rate_limit_max_requests_per_window",
        1000,
    )
    monkeypatch.setattr(guard_module.settings, "request_max_concurrent_global", 1)
    monkeypatch.setattr(guard_module.settings, "request_max_concurrent_per_tenant", 1)
    monkeypatch.setattr(guard_module.settings, "request_queue_wait_timeout_seconds", 0.05)

    async def _hold_slot() -> None:
        async with guard_module.guard_request_slot("tenant-a"):
            await asyncio.sleep(0.12)

    async def _expect_timeout() -> None:
        with pytest.raises(guard_module.RequestGuardError, match="系统当前繁忙"):
            async with guard_module.guard_request_slot("tenant-a"):
                pass

    holder = asyncio.create_task(_hold_slot())
    await asyncio.sleep(0.01)
    await _expect_timeout()
    await holder
