import os
from pathlib import Path

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_ENV = "dev"
BACKEND_DIR = Path(__file__).resolve().parents[4]


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
    ollama_base_url: str | None = None
    # 未显式传 model 时的兜底模型。必须填 Ollama 上真实存在的模型名，
    # 否则未传参会直接 404。可用 `GET /api/tags` 核对。
    ollama_default_model: str = "gemma4:e4b-mlx"
    ollama_timeout_seconds: float = 120.0
    ollama_stream_idle_timeout_seconds: float = 180.0
    redis_url: str | None = None
    redis_password: str | None = None
    redis_key_prefix: str = "doc-process-studio"
    redis_ttl_seconds: int = 60 * 60 * 12
    skill_context_max_characters: int = 16_000
    skill_chunk_max_characters: int = 1_800
    skill_memory_short_term_max_characters: int = 1_200
    skill_memory_episodic_max_characters: int = 1_800
    skill_memory_long_term_max_characters: int = 2_400
    skill_context_search_limit: int = 6
    skill_context_search_limit_max: int = 16
    skill_retrieval_lexical_candidate_limit: int = 24
    skill_retrieval_semantic_candidate_limit: int = 24
    skill_retrieval_rerank_candidate_limit: int = 12
    skill_retrieval_semantic_enabled: bool = True
    skill_retrieval_rerank_enabled: bool = True
    skill_retrieval_embedding_model: str = "nomic-embed-text"
    skill_retrieval_embedding_cache_ttl_seconds: int = 60 * 60 * 12
    skill_retrieval_embedding_batch_size: int = 16
    skill_tool_script_timeout_seconds: int = 120
    skill_tool_script_cpu_seconds: int = 60
    skill_tool_script_memory_limit_mb: int = 1_024
    skill_tool_script_output_limit_mb: int = 64
    skill_sensitive_operation_policy: str = "allow"
    request_timeout_seconds: float = 180.0
    request_queue_wait_timeout_seconds: float = 2.5
    request_rate_limit_window_seconds: int = 60
    request_rate_limit_max_requests_per_window: int = 120
    request_max_concurrent_global: int = 64
    request_max_concurrent_per_tenant: int = 16
    feature_planner_enabled: bool = True
    feature_planner_rollout_ratio: float = 1.0
    feature_executor_enabled: bool = True
    feature_executor_rollout_ratio: float = 1.0
    agent_trace_ttl_seconds: int = 60 * 60 * 24 * 30
    agent_trace_store_enabled: bool = True
    skill_tool_max_iterations: int = 12
    skill_planner_top_k_candidates: int = 4
    skill_planner_max_implicit_skills: int = 2
    skill_planner_min_confidence: float = 0.35
    skill_planner_trace_max_entries: int = 20
    skill_tool_history_max_entries: int = 200
    agent_executor_max_parallel_reads: int = 4
    agent_executor_tool_retry_max_attempts: int = 3
    agent_executor_tool_retry_base_delay_seconds: float = 0.25
    agent_executor_time_budget_seconds: float = 60.0
    agent_executor_max_tool_calls: int = 24
    agent_executor_prompt_budget_ratio: float = 0.82
    agent_executor_default_context_length: int = 8192
    agent_executor_model_context_cache_ttl_seconds: int = 60 * 60 * 12
    agent_executor_model_context_warmup_concurrency: int = 4
    generated_attachments_dir: str = str(BACKEND_DIR / "generated-attachments")
    generated_attachment_ttl_seconds: int = 60 * 60 * 24 * 7
    database_url: str = "postgresql+asyncpg://admin:postgres_password@db:5432/master"
    test_database_url: str = Field(
        default="postgresql+asyncpg://admin:postgres_password@db:5432/dps_test",
        validation_alias=AliasChoices("DPS_TEST_DATABASE_URL", "TEST_DATABASE_URL"),
    )
    auto_create_schema: bool = False
    jwt_secret_key: str = "your-super-secret-key-change-in-production-min-32-chars"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    admin_username: str = "admin"
    admin_password: str = "admin123"
    kb_max_upload_size_bytes: int = 100 * 1024 * 1024
    kb_search_top_k: int = 6
    # 知识库列表缓存秒数。RAGFlow 是外部真相源，其侧变更不会通知本服务，
    # 缓存会让应用与 RAGFlow 短暂不一致；默认 0（不缓存）保证强一致，
    # 需要减轻 RAGFlow 压力时可设为 10~60。
    kb_cache_ttl_seconds: int = 0
    # RAGFlow 知识增强。默认关闭，开启时需提供 base_url 与 api_key，
    # 切勿将 api_key 硬编码进代码。
    ragflow_base_url: str | None = None
    ragflow_api_key: str | None = None
    ragflow_enabled: bool = False
    ragflow_timeout_seconds: float = 15.0
    # 实测最高相似度 0.72，默认 0.70 余量偏小，暂取 0.55 观测召回。
    ragflow_similarity_threshold: float = 0.55
    ragflow_top_k: int = 3
    ragflow_datasets_json: str = '{"history":["f05e5a4aadac11f1b9211b18c23af0c8"]}'
    ragflow_enabled_sections: str = "quick,impact,root_cause,follow_up"
    # 知识库项目 → RAGFlow dataset 映射，形如 {"项目名": ["dataset_id"]}，值也允许是单个字符串。
    # 项目未命中映射时的兜底 dataset（直接按现有 dataset 读，不改语言标注）。
    # 触发服务端解析的超时（解析是异步的，只等触发动作本身）。
    ragflow_parse_timeout_seconds: float = 60.0

    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=str(resolve_env_file_path()),
    )

    @field_validator("redis_url", mode="before")
    @classmethod
    def validate_redis_url(cls, value: str | None) -> str | None:
        return normalize_redis_url(value)

    @field_validator("feature_planner_rollout_ratio", "feature_executor_rollout_ratio")
    @classmethod
    def validate_rollout_ratio(cls, value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    @field_validator("skill_sensitive_operation_policy")
    @classmethod
    def validate_sensitive_operation_policy(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"allow", "confirm", "deny_high"}:
            return "allow"
        return normalized


settings = Settings()
