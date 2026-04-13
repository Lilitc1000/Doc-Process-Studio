import os
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_ENV = "dev"
BACKEND_DIR = Path(__file__).resolve().parents[2]


def resolve_runtime_env() -> str:
    runtime_env = os.getenv("ENV", DEFAULT_ENV).strip()
    return runtime_env or DEFAULT_ENV


def resolve_env_file_path(env_name: str | None = None) -> Path:
    normalized_env_name = (env_name or resolve_runtime_env()).strip() or DEFAULT_ENV
    return BACKEND_DIR / f".env.{normalized_env_name}"


def normalize_redis_url(raw_value: str | None) -> str | None:
    if raw_value is None:
        return None

    normalized = raw_value.strip()
    if not normalized:
        return None

    if normalized.startswith("http://"):
        return "redis://" + normalized[len("http://") :]
    if normalized.startswith("https://"):
        return "rediss://" + normalized[len("https://") :]
    return normalized


class Settings(BaseSettings):
    app_name: str = "doc-process-studio-service"
    env: str = resolve_runtime_env()
    db_dsn: str | None = None
    ollama_base_url: str | None = None
    ollama_timeout_seconds: float = 10.0
    redis_url: str | None = None
    redis_password: str | None = None
    redis_key_prefix: str = "doc-process-studio"
    redis_ttl_seconds: int = 60 * 60 * 12
    skill_context_max_characters: int = 16_000
    skill_chunk_max_characters: int = 1_800
    skill_compact_summary_max_characters: int = 2_400
    skill_context_search_limit: int = 4
    skill_tool_max_iterations: int = 12
    skill_planner_top_k_candidates: int = 4
    skill_planner_max_implicit_skills: int = 2
    skill_planner_min_confidence: float = 0.35
    skill_planner_trace_max_entries: int = 20
    skill_tool_history_max_entries: int = 200
    agent_executor_max_parallel_reads: int = 4
    agent_executor_tool_retry_max_attempts: int = 3
    agent_executor_tool_retry_base_delay_seconds: float = 0.25
    agent_executor_time_budget_seconds: float = 30.0
    agent_executor_max_tool_calls: int = 24
    agent_executor_prompt_budget_ratio: float = 0.82
    agent_executor_default_context_length: int = 8192
    agent_executor_model_context_cache_ttl_seconds: int = 60 * 60 * 12
    agent_executor_model_context_warmup_concurrency: int = 4
    generated_attachments_dir: str = str(BACKEND_DIR / "generated-attachments")
    generated_attachment_ttl_seconds: int = 60 * 60 * 24 * 7

    model_config = SettingsConfigDict(extra="ignore")

    @field_validator("redis_url", mode="before")
    @classmethod
    def validate_redis_url(cls, value: str | None) -> str | None:
        return normalize_redis_url(value)


settings = Settings(
    _env_file=resolve_env_file_path(),
)
