# doc_process_studio 后端

## 配置
后端现在按环境分文件读取配置。
运行时会先读取环境变量 `APP_ENV`，再加载对应的配置文件：

- `APP_ENV=dev` -> `backend/.env.dev`
- `APP_ENV=prod` -> `backend/.env.prod`

如果没有显式设置 `APP_ENV`，默认按 `dev` 处理。

启动前请先确认 `APP_ENV` 和对应配置文件一致。

## 开发
```bash
cd backend
uv sync --group dev
uv run uvicorn doc_process_studio.main:app --reload --host 0.0.0.0 --port 8000
```

如果你要显式指定环境，可以这样启动：

```bash
cd backend
APP_ENV=dev uv run uvicorn doc_process_studio.main:app --reload --host 0.0.0.0 --port 8000
```
