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
├── exceptions.py       # 全局异常层级（AppError、NotFoundError）
├── logging_config.py   # 日志配置（控制台 + 按天轮转文件 + 分级文件 + 环境差异化 + JSON 格式化）
├── request_id.py       # 请求关联 ID 中间件（contextvars + 响应头注入）
├── request_logging.py  # 请求日志中间件（method/path/status/duration）
├── ollama.py           # Ollama HTTP 调用（流式/非流式聊天、模型列表）
├── model_context.py    # 模型上下文长度缓存与预热
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
| `logging_config.py` | 日志初始化（控制台 + 按天轮转文件 + 分级文件 + 环境差异化 + JSON 格式化） | `main.py` 启动时调用 |
| `request_id.py` | 请求关联 ID 中间件，为每个请求生成唯一 ID 并注入 contextvars 和响应头 | `main.py` 注册中间件、`logging_config.py` 日志格式引用 |
| `request_logging.py` | 请求日志中间件，记录每个请求的 method/path/status/duration | `main.py` 注册中间件 |
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

## 日志配置

`logging_config.py` 在应用启动时由 `main.py` 调用 `setup_logging()` 初始化日志系统。

### 日志输出

| 输出目标 | 文件路径 | 级别 | 说明 |
|----------|----------|------|------|
| 控制台 | `stdout` | dev: DEBUG / prod: INFO | 开发调试用 |
| 全量日志 | `backend/logs/app.log` | dev: DEBUG / prod: INFO | 按天轮转，保留 30 天 |
| 错误日志 | `backend/logs/error.log` | ERROR+ | 按天轮转，保留 30 天，仅记录错误 |

### 日志格式

- **dev 环境**：可读文本格式，包含 request_id
  ```
  2026-06-24 10:00:00 | INFO     | a1b2c3d4 | doc_process_studio.chat.service.stream | ...
  ```
- **prod 环境**：JSON 结构化格式，便于日志系统检索
  ```json
  {"timestamp":"2026-06-24 10:00:00","level":"INFO","request_id":"a1b2c3d4","logger":"...","message":"..."}
  ```

### 请求关联 ID

`request_id.py` 提供请求级关联 ID：
- 每个请求自动生成 12 位 hex 的 `request_id`（支持从请求头 `X-Request-Id` 传入）
- 通过 `contextvars` 在请求生命周期内传递，日志自动携带
- 响应头中返回 `X-Request-Id`，方便前端反馈问题时提供
- 业务代码通过 `get_request_id()` 获取当前请求 ID

### 请求日志中间件

`request_logging.py` 自动记录每个请求的入口/出口：
```
INFO  | a1b2c3d4 | POST /api/chat/stream | 200 | 1.23s
WARN  | e5f6g7h8 | GET /api/knowledge-base/projects/999 | 404 | 0.05s
ERROR | i9j0k1l2 | POST /api/incident-report/reports | 500 | 2.10s
```

### 全局异常处理

`main.py` 注册了 `@app.exception_handler(Exception)`，捕获所有未处理异常：
- 记录完整异常堆栈（`logger.exception`）
- 返回通用 500 响应，不暴露内部细节

### Router 层日志

各 router 的异常映射函数（`_handle_*_error`）在将领域异常映射为 HTTP 响应时，同步记录 `logger.warning`：
- 4xx 类异常：`logger.warning`（客户端错误）
- 5xx 类异常：`logger.error`（服务端问题）

### 降噪

`uvicorn.access`、`sqlalchemy.engine`、`httpx` 设为 WARNING 级别。

### 使用方式

业务模块使用 `logger = logging.getLogger(__name__)` 获取日志器即可，无需额外配置。日志中自动携带当前请求的 `request_id`。
