# Chat 业务域开发指南

## 概述

Chat 域负责对话功能，包括消息流式生成、会话管理、文件附件处理和 Skill 工具调用。

## 目录结构

Chat 域采用 DDD 分层架构。会话 CRUD 与附件管理走 domain/application/infrastructure 分层；流式聊天编排、SSE 格式化、文件上下文准备等纯函数工具保留在 service/ 供 infrastructure 委托和跨域调用。

```text
backend/src/doc_process_studio/chat/
├── domain/                      # 领域层：领域异常
│   └── errors.py                # ChatError / SessionNotFoundError / AttachmentExpiredError / ...
├── application/                 # 应用层：用例编排 + 端口
│   ├── ports.py                 # SessionRepository / TitleGenerator / ConversationStateStore / AttachmentStore 端口
│   ├── session_service.py       # SessionService（会话 CRUD、归属校验、标题生成、状态清理）
│   └── attachment_service.py    # AttachmentService（附件下载响应、上传/生成保存）
├── infrastructure/              # 基础设施层：端口实现 + 依赖装配
│   ├── session_repository.py    # SqlSessionRepository / OllamaTitleGenerator
│   ├── attachment_store.py      # FsAttachmentStore
│   ├── conversation_state_store.py  # SkillConversationStateStore
│   └── dependencies.py          # FastAPI 依赖装配（get_session_service / get_attachment_service 工厂）
├── router/
│   ├── stream.py                # POST /api/chat/stream
│   ├── sessions.py              # 会话 API（依赖注入 SessionService）
│   └── attachments.py           # 附件下载 API（依赖注入 AttachmentService）
├── service/                     # 纯函数工具层（被 infrastructure 委托 + 跨域调用）
│   ├── stream.py                # 流式聊天编排入口
│   ├── sessions.py              # 会话 CRUD 工具函数
│   ├── attachments.py           # 附件管理工具函数
│   ├── db_session_store.py      # PostgreSQL 会话存储
│   ├── file_context.py          # 上传文件上下文准备
│   └── streaming/               # SSE 格式化、工具调用合并、上下文构建
├── models/
│   ├── chat_session_orm.py      # ChatSession ORM
│   └── __init__.py
└── schemas/
    ├── request.py               # ChatStreamRequest, ChatMessageInput 等
    ├── response.py              # ChatSessionListResponse, ChatSessionDetail
    ├── session.py               # ChatSessionSummary, ChatSessionSnapshot
    ├── attachment.py            # ChatAttachment, ChatAttachmentMetadata
    ├── file_context.py          # UploadedFileContext, PreparedUploadedFile
    └── common.py                # 共享基类
```

### 分层依赖规则

- **domain** 不依赖任何其他层，只包含领域异常定义
- **application** 依赖 domain + 端口抽象，不依赖 infrastructure 实现
- **infrastructure** 实现 application 端口，委托 service/ 纯函数和 skill/system 域工具
- **router** 通过 `Depends(get_session_service)` / `Depends(get_attachment_service)` 注入应用服务，将领域异常映射为 HTTP 状态码
- **service/** 是纯函数工具层，被 infrastructure 委托，也被 incident_report/skill 跨域直接调用（attachments/streaming）

### 依赖注入

应用服务通过 `infrastructure/dependencies.py` 装配，使用 `@lru_cache(maxsize=1)` 单例。测试时通过 `app.dependency_overrides[get_session_service]` 替换为桩服务。

### 异常映射

router 将领域异常映射为 HTTP 状态码：`SessionAccessDeniedError`→403、`SessionNotFoundError`→404、`AttachmentExpiredError`→410、`AttachmentNotFoundError`→404。

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/chat/stream` | 流式聊天（SSE） |
| GET | `/api/chat/sessions` | 获取会话列表 |
| POST | `/api/chat/sessions` | 创建新会话 |
| GET | `/api/chat/sessions/{id}` | 获取会话详情 |
| PUT | `/api/chat/sessions/{id}` | 保存会话快照 |
| PATCH | `/api/chat/sessions/{id}/title` | 修改会话标题 |
| DELETE | `/api/chat/sessions/{id}` | 删除会话 |
| GET | `/api/attachments/{id}/download` | 下载附件 |

## 核心流程

1. 前端发送 `POST /api/chat/stream`，携带消息和可选 Skill ID
2. 后端做请求防护（限流、并发控制）
3. 加载会话级 Agent 状态
4. 检索上下文（BM25 + embedding 混合召回）
5. 流式调用 Ollama，若有工具调用则进入执行器
6. 结束后落盘 trace 审计记录

## 附件管理

- 文件落到 `backend/generated-attachments/`
- 该目录已加入 `.gitignore`
- 默认有效期 7 天
- 过期文件会在启动时、生成新文件时、下载文件前自动清理
- 统一下载接口：`GET /api/attachments/{attachment_id}/download`

## 跨域依赖

- `skill.service.registry` — Skill 发现与选择
- `skill.service.context` — 上下文检索
- `skill.service.tool_loop` — 工具执行循环
- `system.service.executor` — DAG 执行器
- `system.service.trace_store` — trace 审计
- `core.ollama` — Ollama 调用
- `core.request_guard` — 请求防护

## 开发注意

- 流式响应使用 SSE 格式，事件类型定义在 `service/streaming/` 中
- 会话数据存储在 PostgreSQL，使用 `session_store.py` 重新导出 `db_session_store` 中的函数
- 不要在 `router/` 中写业务逻辑，所有编排逻辑放 `service/`
- Pydantic 数据模型统一放在 `schemas/` 目录，`models/` 仅保留 ORM 模型
- 服务层异常处理使用 `logging` 记录上下文信息（如 trace_id、model 名称），与 `AgentTraceRecorder` 审计日志互补
