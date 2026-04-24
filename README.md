# doc_process_studio 全栈项目

目录：
- backend/  Python 3.13 + FastAPI
- frontend/ Vue3 + Vite + TypeScript

启动（在 DevContainer 内）：
```bash
cd backend && uv sync --group dev && uv run uvicorn doc_process_studio.main:app --reload --host 0.0.0.0 --port 8000
cd frontend && sudo npm install && npm run dev -- --host --port 5173
```
