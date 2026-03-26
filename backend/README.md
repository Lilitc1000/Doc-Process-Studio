# doc_process_studio 后端

## 开发
```bash
cd backend
uv sync --group dev
uv run uvicorn doc_process_studio.main:app --reload --host 0.0.0.0 --port 8000
```
