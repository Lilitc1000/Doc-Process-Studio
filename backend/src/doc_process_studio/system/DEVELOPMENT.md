# System 业务域开发指南

## 概述

System 域负责系统级功能，包括健康检查、模型管理、Agent trace 审计、DAG 执行器、质量门控和灰度发布。

## 后端

### 目录结构

```text
backend/src/doc_process_studio/system/
├── router/
│   ├── health.py           # GET /api/health
│   ├── models.py           # GET /api/models
│   └── agent_traces.py     # GET /api/agent-traces/{trace_id}
├── service/
│   ├── executor.py         # DAG 工具图执行器
│   ├── quality_gate.py     # 质量门控
│   ├── feature_flags.py    # SHA256 灰度发布
│   ├── trace_store.py      # Redis trace 存储
│   └── error_detail.py     # 异常详情构建
├── models/
│   ├── agent_trace.py      # AgentTraceRecord
│   └── ollama.py           # UpstreamOllamaModelRecord
└── schemas/
    ├── request.py          # 入参 Pydantic 模型
    ├── response.py         # 出参 Pydantic 模型
    └── common.py           # 共享基类
```

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

**quality_gate.py** — 质量门控：
- 评估工具执行结果的质量
- 决定是否需要重试或降级

**feature_flags.py** — 灰度发布：
- 基于 SHA256 哈希的灰度策略
- 按 conversation_id 决定是否启用新功能

**trace_store.py** — trace 审计：
- 记录每次工具执行的完整上下文
- 支持按 trace_id 查询回放数据

### 跨域依赖

- `chat.schemas.request` — ChatStreamRequest（executor 使用）
- `skill.models.runtime` — 运行时状态模型（executor 使用）
- `core.ollama` — Ollama 调用
- `core.cache` — Redis 缓存

### 开发注意

- `executor.py` 是跨域共享的执行器，被 Chat 和 Skill 域调用
- trace 数据存储在 Redis，有过期时间
- 灰度发布策略基于哈希，确保同一会话始终走同一分支
- 不要在 `models/` 中引入 Pydantic
