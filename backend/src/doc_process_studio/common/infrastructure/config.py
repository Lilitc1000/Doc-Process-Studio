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

    # ------------------------------------------------------------------ 敏感凭据加密
    # 用于把系统级凭据（RAGFlow API Key）加密后落库的主密钥。
    # 取值：base64 编码的 32 字节，或 64 位 hex。
    #   - env == "prod" 时必须显式配置，否则启动直接失败（fail fast，
    #     不给"以为加密了其实没有"留口子）
    #   - env != "prod" 且未配置时，允许从 jwt_secret_key 经 HKDF-SHA256 确定性派生，
    #     并打 WARNING。派生是确定性的，因此所有开发从同一份 .env.<env> 派生出的
    #     主密钥一致，即使共用同一个 dev 数据库也能互相解密，无需传递密钥文件。
    #     代价：dev 的加密强度等于 jwt_secret_key 的强度，而它本身就在 .env.dev 里，
    #     所以 dev 只做到"防脱库裸读"，不是强保护。
    # 切勿把主密钥写进被 git 跟踪的 .env.dev；生产环境改用部署机 .env / 环境变量注入。
    # 仓库已不再提交 .env.prod（其含真实生产凭据），仅留 .env.prod.example 模板。
    settings_encryption_key: str | None = None
    settings_encryption_key_id: str = "k1"
    # 是否允许开发环境从 jwt_secret_key 派生主密钥。生产环境该开关无效（永远要求显式配置）。
    settings_encryption_allow_dev_kdf: bool = True
    # 系统级配置（含密文凭据）的进程内缓存秒数。多 worker 部署下，某个 worker 改了配置，
    # 其他 worker 最长要等这个 TTL 才生效。设为 0 表示每次都查库（强一致但多一次查询）。
    system_settings_cache_ttl_seconds: int = 60

    # ------------------------------------------------------------------ RAGFlow
    # RAGFlow 本体开关（结构性）：决定"要不要把 RAGFlow 检索引擎装进报告侧参考上下文"。
    # 改它需要重启。运行期的启停由系统设置里的 ragflow.enabled 控制（admin 可改，立即生效）。
    ragflow_enabled: bool = False
    # 连接信息与凭据的**开发期兜底**。生产环境应通过管理员的设置页写入数据库
    # （system_settings / system_secrets），这里的值只在库中没有配置时生效。
    # 切勿把 api_key 提交进版本库 —— 用 .env.<env>.local。
    ragflow_base_url: str | None = None
    ragflow_api_key: str | None = None
    ragflow_timeout_seconds: float = 15.0
    # 实测最高相似度 0.72，默认 0.70 余量偏小，暂取 0.55 观测召回。
    ragflow_similarity_threshold: float = 0.55
    ragflow_top_k: int = 6
    # 同一文档最多取回的片段数。原先按 document_id 整体去重（等于 1），
    # 语料只有一篇时每次只注入 1 个片段，top_k 形同虚设。
    ragflow_max_chunks_per_document: int = 2
    # 报告侧参考上下文使用的 dataset 列表，形如 {"scope": ["dataset_id", ...]}。
    # 只接受**数组**值：字符串值会被 _parse_datasets_json 静默忽略
    # （见 incident_report/infrastructure/adapters/ragflow_knowledge.py）。
    # 注意当前唯一调用点把 scope 写死为 "history"
    # （reference_context.py 的 CompositeReferenceContext.resolve），
    # 因此本项实际上等价于"一个 dataset 列表"，多 scope 能力尚未接线。
    ragflow_datasets_json: str = '{"history":["f05e5a4aadac11f1b9211b18c23af0c8"]}'
    # 启用 RAGFlow 知识增强的报告章节。description / timeline 是纯事实章节，
    # 注入外部素材会诱导编造，必须排除在外。
    ragflow_enabled_sections: str = "quick,impact,root_cause,follow_up"
    # 触发服务端解析的超时（解析是异步的，只等触发动作本身）。
    ragflow_parse_timeout_seconds: float = 60.0

    model_config = SettingsConfigDict(
        extra="ignore",
        # 两段式加载：``.env.{env}`` 入库（不放密钥），
        # ``.env.{env}.local`` 由 .gitignore 覆盖，用于放主密钥等敏感值。
        # pydantic-settings 按顺序读取，后面的文件覆盖前面的。
        env_file=(
            str(resolve_env_file_path()),
            f"{resolve_env_file_path()}.local",
        ),
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
