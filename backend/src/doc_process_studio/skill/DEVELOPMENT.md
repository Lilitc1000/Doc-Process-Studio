# Skill 业务域开发指南

## 概述

Skill 域负责 Skill 的发现、选择、上下文检索和工具执行循环。Skill 是系统可扩展的能力单元，每个 Skill 定义了工具配置和参考文档。

## 目录结构

Skill 域采用 DDD 四层架构（端口与适配器模式）：

```text
backend/src/doc_process_studio/skill/
├── domain/                      # 领域层：领域异常
│   └── errors.py                # SkillError / SkillNotFoundError
├── application/                 # 应用层：用例编排 + 端口 + DTO
│   ├── ports.py                 # SkillRegistry / SkillContextSearcher / ConversationStateRepository 端口
│   ├── contracts.py             # SkillServiceContract 应用服务契约
│   ├── dtos/                    # 应用层 DTO
│   │   ├── catalog.py           # SkillInterfaceConfig / SkillToolConfig 等目录模型
│   │   ├── interaction.py       # InteractionStep 等交互模型
│   │   └── runtime.py           # SkillConversationState / SkillPlanDecision 等运行时模型
│   └── skill_service.py         # SkillService（Skill 列表、上下文检索、会话缓存 TTL/清理）
├── infrastructure/              # 基础设施层：端口实现 + 依赖装配 + 技术工具
│   ├── skill_repository.py      # LocalSkillRegistry / HybridSkillContextSearcher / RedisConversationStateRepository
│   ├── registry.py              # 文件系统 Skill 发现
│   ├── planner.py               # LLM Skill 规划选择
│   ├── selector.py              # Skill 选择策略入口
│   ├── context.py               # 语义上下文检索
│   ├── context_packer.py        # 层级记忆压缩
│   ├── conversation_store.py    # 会话状态 Redis 存储
│   ├── runtime.py               # 上下文状态同步
│   ├── tool_loop/               # 工具执行循环（子包）
│   │   ├── __init__.py          # 公共 API 重导出
│   │   ├── tool_exec.py         # 工具调用执行
│   │   ├── tool_schema.py       # 工具 Schema 构建
│   │   ├── tool_status.py       # 工具状态文本
│   │   ├── tool_args.py         # 参数校验与归一化
│   │   └── skill_files.py       # Skill 文件操作与作用域
│   └── dependencies.py          # FastAPI 依赖装配（get_skill_service 工厂）
└── router/                      # 用户接口层：API 端点 + 请求/响应 Schema
    ├── routes.py                # Skill API（依赖注入 SkillService）
    └── schemas/                 # HTTP DTO
        └── response.py          # 出参 Pydantic 模型
```

### 分层依赖规则

- **domain** 不依赖任何其他层，只包含领域异常定义
- **application** 依赖 domain + 端口抽象，不依赖 infrastructure 实现
- **infrastructure** 实现 application 端口，包含技术工具函数和外部服务调用
- **router** 通过 `Depends(get_skill_service)` 注入应用服务，将领域异常映射为 HTTP 状态码

### 依赖注入

应用服务通过 `infrastructure/dependencies.py` 装配，使用 `@lru_cache(maxsize=1)` 单例。测试时通过 `app.dependency_overrides[get_skill_service]` 替换为桩服务。

### 异常映射

router 将领域异常映射为 HTTP 状态码：`SkillNotFoundError`→404。

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/skills` | 获取 Skill 列表 |
| POST | `/api/skills/interact` | Skill 交互 |
| POST | `/api/skills/context` | 获取 Skill 上下文 |

## 核心流程

1. 用户发送消息时，可选绑定 Skill ID
2. `selector.py` 根据 feature flag 决定使用规划器还是直接匹配
3. 规划器 (`planner.py`) 使用 LLM 选择合适的 Skill
4. `context.py` 检索相关上下文（BM25 + embedding 混合召回）
5. `context_packer.py` 压缩上下文以适应模型窗口
6. `tool_loop/` 执行工具调用循环
7. 执行结果返回给 Chat 域的流式编排

## 跨域依赖

- `chat.application.dtos.attachment` — 附件类型
- `chat.router.schemas.request` — ChatStreamRequest
- `system.infrastructure.utils.executor` — DAG 执行器
- `system.infrastructure.trace_store` — trace 审计
- `common.infrastructure.ollama` — Ollama 调用
- `common.infrastructure.config` — 配置（含 BACKEND_DIR）

## 开发注意

- `tool_loop/` 子包拆分为 tool_exec、tool_schema、tool_status、skill_files、tool_args 五个模块，修改时注意不要引入循环导入
- Skill 定义目录是 `backend/skills/`，每个 Skill 至少包含 `agents/config.yaml`
- 工具执行支持 DAG 依赖，由 `system/infrastructure/utils/executor.py` 处理
- 会话状态存储在 Redis，使用 `conversation_store.py`
- 上下文检索（`context.py`）使用异步 HTTP 客户端调用 Ollama embedding 接口（`/api/embed`）
- 服务层异常处理使用 `logging` 记录上下文信息（如 model 名称、text 数量），与 `AgentTraceRecorder` 审计日志互补
- `tool_status.py` 中内置工具的状态文案需在 `build_tool_status_start`、`_build_reused_tool_status`、`_build_builtin_tool_status` 三个函数中同步添加，否则会误走到 `_build_declared_tool_status` 显示"工具执行失败：未知错误"
