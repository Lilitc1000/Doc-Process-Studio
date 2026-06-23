import httpx

from doc_process_studio.system.service.error_detail import (
    build_exception_detail,
    summarize_exception,
)


def test_summarize_exception_uses_type_when_message_empty() -> None:
    exc = RuntimeError("")
    summary = summarize_exception(exc)
    assert "RuntimeError" in summary


def test_summarize_exception_uses_args_when_message_empty() -> None:
    exc = RuntimeError("", "arg1", "arg2")
    summary = summarize_exception(exc)
    assert "arg1" in summary
    assert "arg2" in summary


def test_summarize_exception_returns_message() -> None:
    exc = ValueError("bad value")
    summary = summarize_exception(exc)
    assert summary == "bad value"


def test_summarize_exception_fallback_when_no_info() -> None:
    exc = RuntimeError()
    summary = summarize_exception(exc)
    assert "RuntimeError" in summary


async def test_build_exception_detail_basic() -> None:
    exc = ValueError("test error")
    detail = await build_exception_detail(exc)
    assert detail["type"] == "ValueError"
    assert detail["message"] == "test error"


async def test_build_exception_detail_includes_http_status_context() -> None:
    request = httpx.Request("POST", "http://localhost:11434/api/chat")
    response = httpx.Response(503, request=request, text="upstream overloaded")
    exc = httpx.HTTPStatusError(
        "upstream failure",
        request=request,
        response=response,
    )

    detail = await build_exception_detail(exc)

    assert detail["type"] == "HTTPStatusError"
    assert detail["status_code"] == 503
    assert detail["request_method"] == "POST"
    assert detail["request_url"] == "http://localhost:11434/api/chat"
    assert "upstream overloaded" in detail.get("response_excerpt", "")


async def test_build_exception_detail_http_error_without_status() -> None:
    request = httpx.Request("GET", "http://localhost:11434/api/tags")
    exc = httpx.ConnectError("connection refused")
    exc.request = request

    detail = await build_exception_detail(exc)
    assert detail["request_method"] == "GET"
    assert detail["request_url"] == "http://localhost:11434/api/tags"


async def test_build_exception_detail_contains_cause_chain() -> None:
    try:
        raise ValueError("inner failure")
    except ValueError as inner_exc:
        root_exc = RuntimeError("outer failure")
        root_exc.__cause__ = inner_exc

    detail = await build_exception_detail(root_exc)

    assert detail["type"] == "RuntimeError"
    cause = detail.get("cause")
    assert isinstance(cause, dict)
    assert cause.get("type") == "ValueError"
    assert cause.get("message") == "inner failure"


async def test_build_exception_detail_max_depth() -> None:
    exc1 = ValueError("level1")
    exc2 = RuntimeError("level2")
    exc2.__cause__ = exc1
    exc3 = TypeError("level3")
    exc3.__cause__ = exc2

    detail = await build_exception_detail(exc3, max_depth=1)
    assert detail["type"] == "TypeError"
    cause = detail.get("cause")
    assert isinstance(cause, dict)
    assert "cause" not in cause


async def test_build_exception_detail_circular_reference() -> None:
    exc1 = ValueError("circular")
    exc2 = RuntimeError("outer")
    exc2.__cause__ = exc1
    exc1.__cause__ = exc2

    detail = await build_exception_detail(exc2)
    assert detail["type"] == "RuntimeError"
