from typing import Any


def build_error_event_detail(
    *,
    message: str,
    exc: BaseException | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    detail: dict[str, Any] = {"message": message}
    if exc is not None:
        detail["error_detail"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }
    if extra:
        detail.update(extra)
    return detail
