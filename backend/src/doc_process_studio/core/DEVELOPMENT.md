# Core 开发指南

核心基础设施目录，存放被多个业务域共享的基础能力模块。所有业务域通过这里统一访问外部服务（数据库、Redis、Ollama）和通用功能（安全、配置、异常）。

## 目录结构

```text
backend/src/doc_process_studio/core/
├── config.py           # 配置管理（Settings 类，从环境变量 / .env 读取）
├── database.py         # PostgreSQL 异步连接池 + SQLAlchemy Base
├── security.py         # JWT 令牌 + 密码哈希 + get_current_user_id 依赖
├── cache_client.py     # Redis 连接池
├── cache.py            # Redis 缓存操作（get_json、set_json、build_cache_key）
├── exceptions.py       # 全局异常层级（AppError、NotFoundError、ConflictError）
├── ollama.py           # Ollama HTTP 调用（流式/非流式聊天、模型列表）
├── model_context.py    # 模型上下文长度缓存与预热
├── language_policy.py  # 语言检测与校验（LLM 驱动）
└── request_guard.py    # 请求防护（速率限制、并发控制）
```

## 模块说明

| 模块 | 职责 | 被谁使用 |
|------|------|----------|
| `config.py` | 所有配置参数集中管理 | 全局 |
| `database.py` | PostgreSQL 异步引擎 + Session 工厂 | 所有业务域 service |
| `security.py` | JWT 生成/验证、密码哈希/校验、用户认证依赖 | auth router、所有需要认证的 router |
| `cache.py` | Redis 缓存读写封装 | 所有业务域 |
| `exceptions.py` | 全局异常基类 | 所有业务域 |
| `ollama.py` | Ollama API 调用封装 | chat、skill、system |
| `request_guard.py` | 速率限制 + 并发控制 | chat stream 入口 |

## 配置加载

- 运行时读取环境变量 `ENV`，加载对应 `.env.<env>` 文件
- 未设置 `ENV` 时默认使用 `dev`
- 所有配置项通过 `settings` 单例访问，不要在代码中写死

## 开发注意

- 不要在业务代码中重复创建数据库连接或 Redis 连接，统一使用 `database.py` 和 `cache_client.py`
- 不要在业务代码中直接调用 Ollama HTTP API，统一使用 `ollama.py`
- `ollama_timeout_seconds`（默认 10s）用于连接/写入/池超时，`ollama_stream_idle_timeout_seconds`（默认 180s）用于流式读取超时
- `get_current_user_id` 是被所有受保护路由共享的认证依赖
- 新增全局基础设施时，优先放入 `core/` 而非散落在业务域中
