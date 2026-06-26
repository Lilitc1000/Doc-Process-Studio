from __future__ import annotations

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

_SKIP_PATHS: frozenset[str] = frozenset({"/health", "/api/health"})


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """ASGI 中间件：记录每个请求的 method、path、status code 和耗时。"""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in _SKIP_PATHS:
            return await call_next(request)

        start = time.monotonic()
        try:
            response = await call_next(request)
        except Exception:
            elapsed = time.monotonic() - start
            logger.error(
                "%s %s | 500 | %.3fs (unhandled exception)",
                request.method,
                request.url.path,
                elapsed,
            )
            raise

        elapsed = time.monotonic() - start
        status = response.status_code
        level = logging.WARNING if status >= 400 else logging.INFO
        logger.log(
            level,
            "%s %s | %d | %.3fs",
            request.method,
            request.url.path,
            status,
            elapsed,
        )
        return response
