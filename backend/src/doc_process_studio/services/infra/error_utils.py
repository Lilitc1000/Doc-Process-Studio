from typing import Any

from ..agent.error_detail import build_exception_detail


async def build_error_event_detail(
    *,
    message: str,
    exc: BaseException | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    detail: dict[str, Any] = {"message": message}
    if exc is not None:
        detail["error_detail"] = await build_exception_detail(exc)
    if extra:
        detail.update(extra)
    return detail
