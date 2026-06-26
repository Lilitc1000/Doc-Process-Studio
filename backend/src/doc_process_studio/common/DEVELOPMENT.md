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
│   ├── qdrant.py                # Qdrant 向量数据库客户端
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
| `QDRANT_HOST` | Qdrant 服务地址 | `localhost` |
| `QDRANT_PORT` | Qdrant 服务端口 | `6333` |

### security.py

提供 JWT 令牌管理和密码哈希功能。`get_current_user_id` 作为 FastAPI 依赖被各域 router 使用。

### cache.py / cache_client.py

Redis 操作封装。`cache_client.py` 负责客户端初始化和生命周期；`cache.py` 提供 `get_json`/`set_json`/`build_cache_key` 等高层操作。

### ollama.py

Ollama HTTP 客户端封装，提供流式和非流式聊天接口、模型发现等。各域通过 `from ...common.infrastructure.ollama import xxx` 引用。
