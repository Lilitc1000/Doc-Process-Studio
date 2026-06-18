# System 业务域开发指南

## 概述

System 域负责系统级功能，包括健康检查、模型管理、Agent trace 审计、DAG 执行器和灰度发布。

## 后端

### 目录结构

System 域采用 DDD 分层架构。查询类端点（health/models/agent-traces）走 domain/application/infrastructure 分层；跨域共享的纯工具（executor/feature_flags/error_detail/trace_store 写入侧）保留在 service/ 供其他域直接调用。

```text
backend/src/doc_process_studio/system/
├── domain/                       # 领域层：领域异常
│   └── errors.py                 # SystemError / TraceNotFoundError
├── application/                  # 应用层：用例编排 + 端口
│   ├── ports.py                  # TraceStore / ModelCatalog 端口
│   └── system_service.py         # TraceQueryService / ModelQueryService
├── infrastructure/               # 基础设施层：端口实现 + 依赖装配
│   ├── trace_store.py            # RedisTraceStore（读取侧）
│   ├── model_catalog.py          # OllamaModelCatalog
│   └── dependencies.py           # FastAPI 依赖装配（get_trace_query_service / get_model_query_service）
├── router/
│   ├── health.py                 # GET /health
│   ├── models.py                 # GET /api/models（依赖注入 ModelQueryService）
│   └── agent_traces.py           # GET /api/system/agent-traces/{trace_id}（依赖注入 TraceQueryService）
├── service/                      # 跨域共享的纯函数工具层
│   ├── executor.py               # DAG 工具图执行器
│   ├── feature_flags.py          # SHA256 灰度发布
│   ├── trace_store.py            # Redis trace 存储（写入/删除 + AgentTraceRecorder）
│   └── error_detail.py           # 异常详情构建
├── models/
│   └── __init__.py
└── schemas/
    ├── request.py                # 入参 Pydantic 模型
    ├── response.py               # 出参 Pydantic 模型
    ├── agent_trace.py            # AgentTraceRecord
    ├── ollama.py                 # UpstreamOllamaModelRecord
    └── common.py                 # 共享基类
```

### 分层依赖规则

- **domain** 不依赖任何其他层，只包含领域异常定义
- **application** 依赖 domain + 端口抽象，不依赖 infrastructure 实现
- **infrastructure** 实现 application 端口，委托 service/trace_store 和 core/ollama
- **router** 通过 `Depends(get_*_service)` 注入应用服务
- **service/** 是跨域共享的纯函数工具层，被 chat/skill/incident_report 直接调用，不参与查询端点的依赖注入链路

### 依赖注入

查询类应用服务通过 `infrastructure/dependencies.py` 装配，使用 `@lru_cache(maxsize=1)` 单例。测试时通过 `app.dependency_overrides[get_*_service]` 替换为 mock。

### API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/models` | 获取可用模型列表 |
| GET | `/api/agent-traces/{trace_id}` | 获取 Agent trace 回放数据 |

### 核心模块

**executor.py** — DAG 执行器：
- 接收工具调用列表，构建依赖图
- 按拓扑序并行执行无依赖的工具
- 支持超时控制和结果缓存

**feature_flags.py** — 灰度发布：
- 基于 SHA256 哈希的灰度策略
- 按 conversation_id 决定是否启用新功能

**trace_store.py** — trace 审计：
- 记录每次工具执行的完整上下文
- 支持按 trace_id 查询回放数据

### 跨域依赖

- `chat.schemas.request` — ChatStreamRequest（executor 使用）
- `skill.schemas.runtime` — 运行时状态模型（executor 使用）
- `core.ollama` — Ollama 调用
- `core.cache` — Redis 缓存

### 开发注意

- `executor.py` 是跨域共享的执行器，被 Chat 和 Skill 域调用
- trace 数据存储在 Redis，有过期时间；读取侧通过 `TraceStore` 端口封装，写入侧 `AgentTraceRecorder` 仍由 service/trace_store.py 提供
- 灰度发布策略基于哈希，确保同一会话始终走同一分支
- Pydantic 数据模型统一放在 `schemas/` 目录，`models/` 仅保留 ORM 模型
- **分层规范**：查询端点不要在 `router/` 写业务逻辑，编排逻辑放 `application/system_service.py`；领域异常定义在 `domain/errors.py`
- **测试规范**：集成测试通过 `app.dependency_overrides[get_*_service]` 注入 Fake 服务，不 patch 模块路径
