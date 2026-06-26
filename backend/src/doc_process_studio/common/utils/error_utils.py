from typing import Any


def summarize_exception(exc: BaseException) -> str:
    """将异常转为可读字符串，供日志和错误响应使用。"""
    message = str(exc).strip()
    if message:
        return message

    args = getattr(exc, "args", ())
    if isinstance(args, tuple):
        normalized_args = [str(item).strip() for item in args if str(item).strip()]
        if normalized_args:
            return "; ".join(normalized_args)

    return f"{exc.__class__.__name__}（异常未提供详细信息）"


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
