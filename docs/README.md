# doc_process_studio

全栈 AI 文档处理工作室，支持文档生成、事故报告管理等功能。

## 技术栈

- **前端**：Vue 3 + Vite + TypeScript + Pinia + Vue Router
- **后端**：Python 3.13 + FastAPI + SQLAlchemy + Alembic
- **数据库**：PostgreSQL + Redis
- **AI**：Ollama（本地 LLM）

## 目录结构

```text
.
├── backend/          # 后端服务
├── frontend/         # 前端应用
└── requirements/     # 需求文档
```

## 快速启动（DevContainer 内）

```bash
# 后端
cd backend && uv sync --group dev && uv run uvicorn doc_process_studio.main:app --reload --host 0.0.0.0 --port 8000

# 前端
cd frontend && npm install && npm run dev -- --host --port 5173
```

## 开发文档索引

| 文档 | 说明 |
|------|------|
| [frontend/README.md](frontend/README.md) | 前端开发指南（目录结构、命名规范、组件分层） |
| [backend/README.md](backend/README.md) | 后端开发指南（目录结构、业务域规则、开发约定） |
| [frontend/tests/DEVELOPMENT.md](frontend/tests/DEVELOPMENT.md) | 前端测试开发指南 |
| [backend/tests/DEVELOPMENT.md](backend/tests/DEVELOPMENT.md) | 后端测试开发指南 |
