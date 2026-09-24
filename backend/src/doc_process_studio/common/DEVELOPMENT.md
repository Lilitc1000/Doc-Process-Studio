# Common 共享内核开发指南

## 概述

`common/` 是跨业务域的共享内核（Shared Kernel），提供通用的技术基础设施。不包含任何业务逻辑，不套用 DDD 四层架构，按职责分子目录组织。

## 目录结构

```text
backend/src/doc_process_studio/common/
├── infrastructure/              # 基础设施
│   ├── config.py                # 全局配置（环境变量、路径、特性开关）
│   ├── database.py              # PostgreSQL 异步引擎 + session 工厂
│   ├── cache.py                 # Redis 缓存操作（get/set/delete/json/keys）
│   ├── cache_client.py          # Redis 客户端初始化与生命周期管理
│   ├── ollama.py                # Ollama HTTP 客户端（流式/非流式聊天、模型发现）
│   ├── ollama_models.py         # UpstreamOllamaModelRecord 数据模型
│   ├── model_context.py         # LLM 上下文窗口估算与缓存
│   └── exceptions.py            # 通用异常基类（AppError/ValidationError/...）
├── security/                    # 安全
│   └── security.py              # JWT 令牌生成/验证、密码哈希/校验、get_current_user_id 依赖
├── middleware/                  # 中间件
│   ├── request_id.py            # 请求 ID 注入
│   ├── request_logging.py       # 请求/响应日志
│   ├── logging_config.py        # 日志格式配置
│   └── request_guard.py         # 速率限制 + 并发控制
└── utils/                       # 工具函数
    ├── dtutils.py               # 日期时间工具（UTC+8 转换）
    ├── text_utils.py            # 文本工具（JSON 解析）
    ├── error_utils.py           # 错误工具（异常摘要、错误事件详情）
    └── tool_args.py             # 工具参数工具（归一化 tool_calls）
```

## 设计原则

- **不包含业务逻辑**：common/ 只提供纯技术基础设施，不涉及任何业务域的概念
- **不依赖业务域**：common/ 不引用任何业务域（auth/chat/skill/system/incident_report/knowledge_base）的代码
- **被所有域引用**：各业务域通过 `from ...common.infrastructure.xxx import yyy` 引用共享基础设施
- **按职责分目录**：infrastructure（配置/存储/外部服务）、security（认证）、middleware（请求处理）、utils（工具函数）

## 关键模块说明

### config.py

全局配置通过 `pydantic-settings` 管理，按环境分文件（`.env.dev`/`.env.prod`）。核心配置项包括：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `DATABASE_URL` | PostgreSQL 连接字符串 | `postgresql+asyncpg://admin:postgres_password@db:5432/master` |
| `REDIS_URL` | Redis 连接字符串 | `redis://localhost:6379/0` |
| `OLLAMA_BASE_URL` | Ollama 服务地址 | `http://localhost:11434` |
| `JWT_SECRET_KEY` | JWT 签名密钥 | - |
| `JWT_ALGORITHM` | JWT 算法 | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | access_token 有效期 | `15` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | refresh_token 有效期 | `7` |
| `OLLAMA_DEFAULT_MODEL` | 生成兜底模型（避免硬编码导致 404） | `gemma4:e4b-mlx` |
| `RAGFLOW_ENABLED` | RAGFlow 的**首次兜底启用状态**（见下方「RAGFlow 的配置优先级」） | `False` |
| `RAGFLOW_BASE_URL` | RAGFlow 服务地址。**开发期兜底**，生产应由管理员在设置页写入 `system_settings` | - |
| `RAGFLOW_API_KEY` | RAGFlow API Key。**开发期兜底**，优先级低于 `system_secrets` 里的密文。**切勿提交进版本库，用 `.env.<env>.local`** | - |
| `RAGFLOW_SIMILARITY_THRESHOLD` | 检索相似度阈值 | `0.55` |
| `RAGFLOW_TOP_K` | 每次检索返回的素材块数 | `3` |
| `RAGFLOW_DATASETS_JSON` | scope→dataset_id 映射 JSON。**只接受数组值**（字符串值会被静默忽略）；当前唯一调用点把 scope 写死为 `"history"`，故实际等价于「一个 dataset 列表」 | `{"history":["f05e5a4aadac11f1b9211b18c23af0c8"]}` |
| `SETTINGS_ENCRYPTION_KEY` | 敏感凭据加密主密钥（base64 的 32 字节或 64 位 hex）。`ENV=prod` 未配置则**启动失败** | - |
| `SETTINGS_ENCRYPTION_KEY_ID` | 主密钥标识，为轮换预留 | `k1` |
| `SETTINGS_ENCRYPTION_ALLOW_DEV_KDF` | 非生产环境允许从 `JWT_SECRET_KEY` 派生主密钥（生产忽略此开关） | `True` |
| `SYSTEM_SETTINGS_CACHE_TTL_SECONDS` | 系统级配置（含密文）的进程内缓存秒数 | `60` |

### 配置文件加载与敏感值

`.env.{env}` 与 `.env.{env}.local` 是**两段式加载**，后者覆盖前者、且被 `.gitignore`
的 `.env*.local` 忽略。所以：

- 需要覆盖配置的人自己建 `backend/.env.dev.local`；**不要把密钥写进入库的 `.env.dev`**（生产 `.env.prod` 已移出仓库，改用部署注入，仅留 `.env.prod.example` 模板）**；
- 生产用环境变量注入，或在部署机上放 `.env.prod.local`。

### RAGFlow 的配置优先级（只有一个开关）

**启用开关只有一个**：`system_settings` 表里的 `ragflow.enabled`。知识库模块与报告侧检索
都读它，管理员在设置页改完**立即生效**（≤ `SYSTEM_SETTINGS_CACHE_TTL_SECONDS`）。

`RAGFLOW_ENABLED` 环境变量**只是库里没有这一行时的兜底值**；一旦管理员在页面上保存过，
env 就不再参与。

> **历史坑，别退回旧写法**：这里曾经有一道 `settings.ragflow_enabled` 的「结构门禁」，
> 在装配期决定要不要把 RAGFlow 检索引擎装进报告侧参考上下文。它和库里的 `ragflow.enabled`
> 构成两套语义 —— env 为 `false` 时管理员在设置页打开开关，**知识库模块生效、报告侧检索却不生效**，
> 而页面文案承诺的是"保存后立即生效，无需重启服务"。
> 现在 `get_reference_context()` 的装配形状恒定（永远 Composite），启停一律由运行期解析决定。

凭据本身（`base_url` / `api_key`）由
`settings/infrastructure/ragflow_config_provider.py` 按「系统级配置 → env 兜底 → 不可用」
三级解析，**不再由消费方直接从 `settings` 读取**。详见 `settings/DEVELOPMENT.md`。

### security.py

提供 JWT 令牌管理和密码哈希功能。`get_current_user_id` 作为 FastAPI 依赖被各域 router 使用。

### cache.py / cache_client.py

Redis 操作封装。`cache_client.py` 负责客户端初始化和生命周期；`cache.py` 提供 `get_json`/`set_json`/`build_cache_key` 等高层操作。

### ollama.py

Ollama HTTP 客户端封装，提供流式和非流式聊天接口、模型发现等。各域通过 `from ...common.infrastructure.ollama import xxx` 引用。
