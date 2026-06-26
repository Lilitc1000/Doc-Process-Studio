from __future__ import annotations

import json
import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from typing import Any

from ..infrastructure.config import BACKEND_DIR, settings

LOG_DIR = BACKEND_DIR / "logs"

_TEXT_FORMAT = "%(asctime)s | %(levelname)-8s | %(request_id)s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class _LogRecord(logging.LogRecord):
    """扩展标准 LogRecord，增加 request_id 字段供格式化使用。"""

    request_id: str = ""


class _RequestIdFilter(logging.Filter):
    """将 contextvars 中的 request_id 注入每条日志记录。"""

    def filter(self, record: logging.LogRecord) -> bool:
        from .request_id import get_request_id

        assert isinstance(record, _LogRecord)
        record.request_id = get_request_id()
        return True


class _JsonFormatter(logging.Formatter):
    """生产环境使用的 JSON 结构化日志格式。"""

    def format(self, record: logging.LogRecord) -> str:
        from .request_id import get_request_id

        log_entry: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "request_id": get_request_id(),
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, ensure_ascii=False)


def _build_console_handler(env: str) -> logging.StreamHandler:
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(_RequestIdFilter())
    if env == "prod":
        handler.setFormatter(_JsonFormatter(datefmt=_DATE_FORMAT))
    else:
        handler.setFormatter(logging.Formatter(_TEXT_FORMAT, datefmt=_DATE_FORMAT))
    handler.setLevel(logging.DEBUG if env == "dev" else logging.INFO)
    return handler


def _build_app_file_handler(env: str) -> TimedRotatingFileHandler:
    handler = TimedRotatingFileHandler(
        LOG_DIR / "app.log",
        when="midnight",
        backupCount=30,
        encoding="utf-8",
        delay=True,
    )
    handler.addFilter(_RequestIdFilter())
    if env == "prod":
        handler.setFormatter(_JsonFormatter(datefmt=_DATE_FORMAT))
    else:
        handler.setFormatter(logging.Formatter(_TEXT_FORMAT, datefmt=_DATE_FORMAT))
    handler.setLevel(logging.DEBUG if env == "dev" else logging.INFO)
    return handler


def _build_error_file_handler(env: str) -> TimedRotatingFileHandler:
    handler = TimedRotatingFileHandler(
        LOG_DIR / "error.log",
        when="midnight",
        backupCount=30,
        encoding="utf-8",
        delay=True,
    )
    handler.addFilter(_RequestIdFilter())
    if env == "prod":
        handler.setFormatter(_JsonFormatter(datefmt=_DATE_FORMAT))
    else:
        handler.setFormatter(logging.Formatter(_TEXT_FORMAT, datefmt=_DATE_FORMAT))
    handler.setLevel(logging.ERROR)
    return handler


_APP_LOGGER_PREFIX = "doc_process_studio"


def setup_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logging.setLogRecordFactory(_LogRecord)

    env = settings.env

    handlers: list[logging.Handler] = [
        _build_console_handler(env),
        _build_app_file_handler(env),
        _build_error_file_handler(env),
    ]

    logging.basicConfig(
        level=logging.INFO,
        format=_TEXT_FORMAT,
        datefmt=_DATE_FORMAT,
        handlers=handlers,
    )

    if env == "dev":
        logging.getLogger(_APP_LOGGER_PREFIX).setLevel(logging.DEBUG)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
