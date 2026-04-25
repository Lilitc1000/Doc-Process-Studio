import asyncio

import httpx

from doc_process_studio.system.service.error_detail import (
    build_exception_detail,
    summarize_exception,
)


def test_summarize_exception_uses_type_when_message_empty() -> None:
    exc = RuntimeError("")
    summary = summarize_exception(exc)
    assert "RuntimeError" in summary


def test_build_exception_detail_includes_http_status_context() -> None:
    request = httpx.Request("POST", "http://localhost:11434/api/chat")
    response = httpx.Response(503, request=request, text="upstream overloaded")
    exc = httpx.HTTPStatusError(
        "upstream failure",
        request=request,
        response=response,
    )

    detail = asyncio.run(build_exception_detail(exc))

    assert detail["type"] == "HTTPStatusError"
    assert detail["status_code"] == 503
    assert detail["request_method"] == "POST"
    assert detail["request_url"] == "http://localhost:11434/api/chat"
    assert "upstream overloaded" in detail.get("response_excerpt", "")


def test_build_exception_detail_contains_cause_chain() -> None:
    try:
        raise ValueError("inner failure")
    except ValueError as inner_exc:
        root_exc = RuntimeError("outer failure")
        root_exc.__cause__ = inner_exc

    detail = asyncio.run(build_exception_detail(root_exc))

    assert detail["type"] == "RuntimeError"
    cause = detail.get("cause")
    assert isinstance(cause, dict)
    assert cause.get("type") == "ValueError"
    assert cause.get("message") == "inner failure"
