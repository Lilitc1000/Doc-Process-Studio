# Chat 业务域开发指南

## 概述

Chat 域负责对话功能，包括消息流式生成、会话管理、文件附件处理和 Skill 工具调用。

## 目录结构

```text
backend/src/doc_process_studio/chat/
├── router/
│   ├── stream.py           # POST /api/chat/stream
│   ├── sessions.py         # GET/POST/PUT/DELETE /api/chat/sessions
│   └── attachments.py      # GET /api/attachments/{id}/download
├── service/
│   ├── stream.py           # 流式聊天编排入口
│   ├── sessions.py         # 会话 CRUD
│   ├── attachments.py      # 附件管理
│   ├── file_context.py     # 上传文件上下文准备
│   ├── session_store.py    # Redis 会话存储实例
│   └── streaming/          # SSE 格式化、工具调用合并、上下文构建
├── models/
│   ├── session.py          # ChatSessionSummary, ChatSessionSnapshot
│   ├── attachment.py       # ChatAttachment, ChatAttachmentMetadata
│   └── file_context.py     # UploadedFileContext, PreparedUploadedFile
└── schemas/
    ├── request.py          # ChatStreamRequest, ChatMessageInput 等
    ├── response.py         # ChatSessionListResponse, ChatSessionDetail
    └── common.py           # 共享基类
```

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

## 跨域依赖

- `skill.service.registry` — Skill 发现与选择
- `skill.service.context` — 上下文检索
- `skill.service.tool_loop` — 工具执行循环（子包：tool_exec, tool_schema, tool_status, skill_files, tool_args）
- `system.service.executor` — DAG 执行器
- `system.service.trace_store` — trace 审计
- `core.ollama` — Ollama 调用
- `core.request_guard` — 请求防护

## 开发注意

- 流式响应使用 SSE 格式，事件类型定义在 `service/streaming/` 中
- 会话数据存储在 Redis，使用 `session_store.py` 中的 `RedisSessionStore` 实例
- 附件文件落到 `backend/generated-attachments/`，7 天过期自动清理
- 不要在 `router/` 中写业务逻辑，所有编排逻辑放 `service/`
