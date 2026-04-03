import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_ENV = "dev"
BACKEND_DIR = Path(__file__).resolve().parents[2]


def resolve_runtime_env() -> str:
    runtime_env = os.getenv("APP_ENV", DEFAULT_ENV).strip()
    return runtime_env or DEFAULT_ENV


def resolve_env_file_path(env_name: str | None = None) -> Path:
    normalized_env_name = (env_name or resolve_runtime_env()).strip() or DEFAULT_ENV
    return BACKEND_DIR / f".env.{normalized_env_name}"


class Settings(BaseSettings):
    app_name: str = "doc-process-studio-service"
    env: str = resolve_runtime_env()
    db_dsn: str | None = None
    ollama_base_url: str | None = None
    ollama_timeout_seconds: float = 10.0

    model_config = SettingsConfigDict(
        env_prefix="APP_",
        extra="ignore",
    )


settings = Settings(
    _env_file=resolve_env_file_path(),
)
