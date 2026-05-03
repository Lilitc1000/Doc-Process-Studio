from doc_process_studio.core.exceptions import (
    AppError,
    NotFoundError,
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


def test_not_found_error():
    err = NotFoundError()
    assert err.status_code == 404
    assert "未找到" in err.message


def test_not_found_error_custom_message():
    err = NotFoundError("自定义消息")
    assert err.message == "自定义消息"
    assert err.status_code == 404


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
