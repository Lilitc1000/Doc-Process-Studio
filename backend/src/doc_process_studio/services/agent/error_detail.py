from __future__ import annotations

from typing import Any

import httpx


def _truncate_text(value: str, *, max_chars: int = 2000) -> str:
    normalized = value.strip()
    if len(normalized) <= max_chars:
        return normalized
    return f"{normalized[:max_chars]}..."


def summarize_exception(exc: BaseException) -> str:
    message = str(exc).strip()
    if message:
        return message

    args = getattr(exc, "args", ())
    if isinstance(args, tuple):
        normalized_args = [str(item).strip() for item in args if str(item).strip()]
        if normalized_args:
            return "; ".join(normalized_args)

    return f"{exc.__class__.__name__}（异常未提供详细信息）"


async def _read_response_excerpt(
    response: httpx.Response,
    *,
    max_chars: int = 1200,
) -> str:
    try:
        response_text = response.text
    except httpx.ResponseNotRead:
        try:
            raw_body = await response.aread()
        except Exception:  # noqa: BLE001
            raw_body = b""
        response_text = raw_body.decode("utf-8", errors="ignore")
    except Exception:  # noqa: BLE001
        response_text = ""

    return _truncate_text(response_text, max_chars=max_chars)


async def _build_detail_recursive(
    exc: BaseException,
    *,
    depth: int,
    max_depth: int,
    visited: set[int],
) -> dict[str, Any]:
    detail: dict[str, Any] = {
        "type": exc.__class__.__name__,
        "message": summarize_exception(exc),
        "repr": _truncate_text(repr(exc), max_chars=1500),
    }

    if isinstance(exc, httpx.HTTPStatusError):
        detail["status_code"] = exc.response.status_code
        detail["request_method"] = exc.request.method
        detail["request_url"] = str(exc.request.url)
        response_excerpt = await _read_response_excerpt(exc.response)
        if response_excerpt:
            detail["response_excerpt"] = response_excerpt
    elif isinstance(exc, httpx.HTTPError):
        request = getattr(exc, "request", None)
        if request is not None:
            detail["request_method"] = request.method
            detail["request_url"] = str(request.url)

    if depth >= max_depth:
        return detail

    cause = exc.__cause__ or exc.__context__
    if cause is None:
        return detail
    if id(cause) in visited:
        return detail

    visited.add(id(cause))
    detail["cause"] = await _build_detail_recursive(
        cause,
        depth=depth + 1,
        max_depth=max_depth,
        visited=visited,
    )
    return detail


async def build_exception_detail(
    exc: BaseException,
    *,
    max_depth: int = 2,
) -> dict[str, Any]:
    return await _build_detail_recursive(
        exc,
        depth=0,
        max_depth=max_depth,
        visited={id(exc)},
    )
