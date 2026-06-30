from doc_process_studio.common.infrastructure.exceptions import (
    AppError,
    OllamaNotConfiguredError,
    RequestGuardError,
    ValidationError,
)


def test_app_error_default_status_code() -> None:
    err = AppError("test error")
    assert err.message == "test error"
    assert err.status_code == 500


def test_app_error_custom_status_code() -> None:
    err = AppError("custom", status_code=400)
    assert err.status_code == 400


def test_validation_error() -> None:
    err = ValidationError()
    assert err.status_code == 422
    assert "校验失败" in err.message


def test_ollama_not_configured_error() -> None:
    err = OllamaNotConfiguredError("未配置")
    assert isinstance(err, RuntimeError)
    assert str(err) == "未配置"


def test_request_guard_error() -> None:
    err = RequestGuardError("请求被限制")
    assert isinstance(err, RuntimeError)
    assert str(err) == "请求被限制"
