class AppError(Exception):
    def __init__(self, message: str, *, status_code: int = 500) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class NotFoundError(AppError):
    def __init__(self, message: str = "资源未找到") -> None:
        super().__init__(message, status_code=404)


class ValidationError(AppError):
    def __init__(self, message: str = "请求参数校验失败") -> None:
        super().__init__(message, status_code=422)


class OllamaNotConfiguredError(RuntimeError):
    pass


class RequestGuardError(RuntimeError):
    pass
