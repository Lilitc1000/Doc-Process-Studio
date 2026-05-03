import logging
import sys

from .config import BACKEND_DIR

LOG_DIR = BACKEND_DIR / "logs"


def setup_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    handlers: dict[str, logging.Handler] = {
        "console": logging.StreamHandler(sys.stdout),
        "file": logging.FileHandler(
            LOG_DIR / "app.log", encoding="utf-8", delay=True
        ),
    }

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=list(handlers.values()),
    )

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
