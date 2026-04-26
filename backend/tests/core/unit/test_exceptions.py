from fastapi import HTTPException

from doc_process_studio.core.exceptions import (
    AppError,
    NotFoundError,
    ConflictError,
    ValidationError,
    OllamaNotConfiguredError,
    RequestGuardError,
)


def test_app_error_default_status_code():
    err = AppError("test error")
    assert err.message == "test error"
    assert err.status_code == 500


def test_app_error_custom_status_code():
    err = AppError("custom", status_code=400)
    assert err.status_code == 400


def test_app_error_to_http_exception():
    err = AppError("not found", status_code=404)
    http_exc = err.to_http_exception()
    assert isinstance(http_exc, HTTPException)
    assert http_exc.status_code == 404
    assert http_exc.detail == "not found"


def test_not_found_error():
    err = NotFoundError()
    assert err.status_code == 404
    assert "未找到" in err.message


def test_not_found_error_custom_message():
    err = NotFoundError("自定义消息")
    assert err.message == "自定义消息"
    assert err.status_code == 404


def test_conflict_error():
    err = ConflictError()
    assert err.status_code == 409
    assert "冲突" in err.message


def test_conflict_error_custom_message():
    err = ConflictError("自定义冲突")
    assert err.message == "自定义冲突"


def test_validation_error():
    err = ValidationError()
    assert err.status_code == 422
    assert "校验失败" in err.message


def test_ollama_not_configured_error():
    err = OllamaNotConfiguredError("未配置")
    assert isinstance(err, RuntimeError)
    assert str(err) == "未配置"


def test_request_guard_error():
    err = RequestGuardError("请求被限制")
    assert isinstance(err, RuntimeError)
    assert str(err) == "请求被限制"
