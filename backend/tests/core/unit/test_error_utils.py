from doc_process_studio.common.utils.error_utils import build_error_event_detail


def test_build_error_event_detail_message_only() -> None:
    result = build_error_event_detail(message="something failed")
    assert result["message"] == "something failed"
    assert "error_detail" not in result


def test_build_error_event_detail_with_exception() -> None:
    exc = ValueError("bad value")
    result = build_error_event_detail(message="error", exc=exc)
    assert result["error_detail"]["type"] == "ValueError"
    assert result["error_detail"]["message"] == "bad value"


def test_build_error_event_detail_with_extra() -> None:
    result = build_error_event_detail(message="error", extra={"key": "value"})
    assert result["key"] == "value"


def test_build_error_event_detail_with_exception_and_extra() -> None:
    exc = RuntimeError("crash")
    result = build_error_event_detail(message="error", exc=exc, extra={"trace_id": "abc"})
    assert result["error_detail"]["type"] == "RuntimeError"
    assert result["trace_id"] == "abc"
