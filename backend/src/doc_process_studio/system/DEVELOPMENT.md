# System 业务域开发指南

## 概述

System 域负责系统级功能，包括健康检查、模型管理、Agent trace 审计、DAG 执行器和灰度发布。

## 目录结构

System 域采用 DDD 四层架构（端口与适配器模式）：

```text
backend/src/doc_process_studio/system/
├── domain/                       # 领域层：领域异常
│   └── errors.py                 # SystemError / TraceNotFoundError
├── application/                  # 应用层：用例编排 + 端口 + DTO
│   ├── ports.py                  # TraceStore / ModelCatalog 端口
│   ├── contracts.py              # TraceQueryServiceContract / ModelQueryServiceContract 应用服务契约
│   ├── dtos/                     # 应用层 DTO
│   └── system_service.py         # TraceQueryService / ModelQueryService
├── infrastructure/               # 基础设施层：端口实现 + 依赖装配 + 技术工具
│   ├── trace_store.py            # RedisTraceStore（读取侧）+ AgentTraceRecorder（写入/删除）
│   ├── model_catalog.py          # OllamaModelCatalog
│   ├── utils/                    # 跨域共享的纯技术工具
│   │   ├── executor.py           # DAG 工具图执行器
│   │   ├── feature_flags.py      # SHA256 灰度发布
│   │   └── error_detail.py       # 异常详情构建
│   └── dependencies.py           # FastAPI 依赖装配（get_trace_query_service / get_model_query_service）
└── router/                       # 用户接口层：API 端点 + 请求/响应 Schema
    ├── health.py                 # GET /health
    ├── models.py                 # GET /api/models
    ├── agent_traces.py           # GET /api/system/agent-traces/{trace_id}
    └── schemas/                  # HTTP DTO
        └── response.py           # 出参 Pydantic 模型
```

### 分层依赖规则

- **domain** 不依赖任何其他层，只包含领域异常定义
- **application** 依赖 domain + 端口抽象，不依赖 infrastructure 实现
- **infrastructure** 实现 application 端口，包含技术工具函数（utils/）和外部服务调用
- **router** 通过 `Depends(get_*_service)` 注入应用服务

### 依赖注入

查询类应用服务通过 `infrastructure/dependencies.py` 装配，使用 `@lru_cache(maxsize=1)` 单例。测试时通过 `app.dependency_overrides[get_*_service]` 替换为 mock。

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/models` | 获取可用模型列表 |
| GET | `/api/agent-traces/{trace_id}` | 获取 Agent trace 回放数据 |

## 核心模块

**executor.py** — DAG 执行器（infrastructure/utils/）：
- 接收工具调用列表，构建依赖图
- 按拓扑序并行执行无依赖的工具
- 支持超时控制和结果缓存

**feature_flags.py** — 灰度发布（infrastructure/utils/）：
- 基于 SHA256 哈希的灰度策略
- 按 conversation_id 决定是否启用新功能

**trace_store.py** — trace 审计（infrastructure/）：
- 记录每次工具执行的完整上下文
- 支持按 trace_id 查询回放数据
- 读取侧通过 `TraceStore` 端口封装，写入侧 `AgentTraceRecorder` 供跨域调用

## 跨域依赖

- `chat.router.schemas.request` — ChatStreamRequest（executor 使用）
- `skill.application.dtos.runtime` — 运行时状态模型（executor 使用）
- `common.infrastructure.ollama` — Ollama 调用
- `common.infrastructure.cache` — Redis 缓存

## 开发注意

- `executor.py` 是跨域共享的执行器，被 Chat 和 Skill 域通过 `system.infrastructure.utils.executor` 调用
- trace 数据存储在 Redis，有过期时间
- 灰度发布策略基于哈希，确保同一会话始终走同一分支
- **分层规范**：查询端点不要在 `router/` 写业务逻辑，编排逻辑放 `application/system_service.py`；领域异常定义在 `domain/errors.py`
- **测试规范**：集成测试通过 `app.dependency_overrides[get_*_service]` 注入 Fake 服务，不 patch 模块路径
