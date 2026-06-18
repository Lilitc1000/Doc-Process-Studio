# Skill 业务域开发指南

## 概述

Skill 域负责 Skill 的发现、选择、上下文检索和工具执行循环。Skill 是系统可扩展的能力单元，每个 Skill 定义了工具配置和参考文档。

## 后端

### 目录结构

Skill 域采用 DDD 分层架构。Skill 列表、上下文检索、会话状态管理走 domain/application/infrastructure 分层；Skill 选择策略、工具执行循环、上下文打包等纯函数工具保留在 service/ 供 infrastructure 委托和跨域调用。

```text
backend/src/doc_process_studio/skill/
├── domain/                      # 领域层：领域异常
│   └── errors.py                # SkillError / SkillNotFoundError / SkillToolNotFoundError
├── application/                 # 应用层：用例编排 + 端口
│   ├── ports.py                 # SkillRegistry / SkillContextSearcher / ConversationStateRepository 端口
│   └── skill_service.py         # SkillService（Skill 列表、上下文检索、会话缓存 TTL/清理）
├── infrastructure/              # 基础设施层：端口实现 + 依赖装配
│   ├── skill_repository.py      # LocalSkillRegistry / HybridSkillContextSearcher / RedisConversationStateRepository
│   └── dependencies.py          # FastAPI 依赖装配（get_skill_service 工厂）
├── router/
│   └── routes.py                # Skill API（依赖注入 SkillService）
├── service/                     # 纯函数工具层（被 infrastructure 委托 + 跨域调用）
│   ├── registry.py              # 文件系统 Skill 发现
│   ├── planner.py               # LLM Skill 选择
│   ├── selector.py              # Skill 选择策略入口
│   ├── context.py               # 语义上下文检索
│   ├── context_packer.py        # 层级记忆压缩
│   ├── conversation_store.py    # 会话状态 Redis 存储
│   ├── tool_loop/               # 工具执行循环（子包）
│   │   ├── __init__.py          # 公共 API 重导出
│   │   ├── tool_exec.py         # 工具调用执行
│   │   ├── tool_schema.py       # 工具 Schema 构建
│   │   ├── tool_status.py       # 工具状态文本
│   │   ├── tool_args.py         # 参数校验与归一化
│   │   └── skill_files.py       # Skill 文件操作与作用域
│   └── runtime.py               # 上下文状态同步
├── models/
│   └── __init__.py
└── schemas/
    ├── request.py               # 入参 Pydantic 模型
    ├── response.py              # 出参 Pydantic 模型
    ├── catalog.py               # Skill 目录模型（SkillInterface, SkillToolConfig 等）
    ├── interaction.py           # 交互步骤模型（InteractionStep 等）
    ├── runtime.py               # 运行时状态模型（SkillConversationState, SkillPlanDecision 等）
    └── common.py                # 共享基类
```

### 分层依赖规则

- **domain** 不依赖任何其他层，只包含领域异常定义
- **application** 依赖 domain + 端口抽象，不依赖 infrastructure 实现
- **infrastructure** 实现 application 端口，委托 service/ 纯函数和 core/cache
- **router** 通过 `Depends(get_skill_service)` 注入应用服务，将领域异常映射为 HTTP 状态码
- **service/** 是纯函数工具层，被 infrastructure 委托，也被 chat/incident_report 跨域直接调用（registry/context/conversation_store/tool_loop）

### 依赖注入

应用服务通过 `infrastructure/dependencies.py` 装配，使用 `@lru_cache(maxsize=1)` 单例。测试时通过 `app.dependency_overrides[get_skill_service]` 替换为桩服务。

### 异常映射

router 将领域异常映射为 HTTP 状态码：`SkillNotFoundError`→404。

### API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/skills` | 获取 Skill 列表 |
| POST | `/api/skills/interact` | Skill 交互 |
| POST | `/api/skills/context` | 获取 Skill 上下文 |

### 核心流程

1. 用户发送消息时，可选绑定 Skill ID
2. `selector.py` 根据 feature flag 决定使用规划器还是直接匹配
3. 规划器 (`planner.py`) 使用 LLM 选择合适的 Skill
4. `context.py` 检索相关上下文（BM25 + embedding 混合召回）
5. `context_packer.py` 压缩上下文以适应模型窗口
6. `tool_loop/` 执行工具调用循环
7. 执行结果返回给 Chat 域的流式编排

### 跨域依赖

- `chat.schemas.attachment` — 附件类型
- `chat.schemas.request` — ChatStreamRequest
- `system.service.executor` — DAG 执行器
- `system.service.trace_store` — trace 审计
- `core.ollama` — Ollama 调用
- `core.config` — 配置（含 BACKEND_DIR）

### 开发注意

- `tool_loop/` 子包拆分为 tool_exec、tool_schema、tool_status、skill_files、tool_args 五个模块，修改时注意不要引入循环导入
- Skill 定义目录是 `backend/skills/`，每个 Skill 至少包含 `agents/config.yaml`
- 工具执行支持 DAG 依赖，由 `system/service/executor.py` 处理
- 会话状态存储在 Redis，使用 `conversation_store.py`
- Pydantic 数据模型统一放在 `schemas/` 目录，`models/` 仅保留 ORM 模型
- 上下文检索（`context.py`）使用异步 HTTP 客户端调用 Ollama embedding 接口（`/api/embed`）
- 服务层异常处理使用 `logging` 记录上下文信息（如 model 名称、text 数量），与 `AgentTraceRecorder` 审计日志互补
- `tool_status.py` 中内置工具（list_skill_directory、read_skill_file、search_skill_context、read_skill_context、search_knowledge_base）的状态文案需在 `build_tool_status_start`、`_build_reused_tool_status`、`_build_builtin_tool_status` 三个函数中同步添加，否则会误走到 `_build_declared_tool_status` 显示"工具执行失败：未知错误"
