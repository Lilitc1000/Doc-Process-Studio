# Backend 开发指南

基于 Python 3.13 + FastAPI 的后端服务。

## 启动

```bash
cd backend
uv sync --group dev
uv run uvicorn doc_process_studio.main:app --reload --host 0.0.0.0 --port 8000
```

显式指定环境：

```bash
ENV=dev uv run uvicorn doc_process_studio.main:app --reload --host 0.0.0.0 --port 8000
```

配置按环境分文件读取（`ENV=dev` → `.env.dev`，`ENV=prod` → `.env.prod`），未设置时默认 `dev`。

## 数据库迁移

```bash
cd backend

# 生成迁移脚本
env ENV=dev uv run alembic revision --autogenerate -m "描述变更内容"

# 执行迁移
env ENV=dev uv run alembic upgrade head

# 回退一个版本
env ENV=dev uv run alembic downgrade -1
```

Alembic 使用异步引擎（asyncpg）。新增 ORM 模型后务必生成迁移脚本，生产环境部署前必须执行 `alembic upgrade head`。

## 测试

```bash
cd backend

# 全量测试
env ENV=dev uv run --no-sync pytest -q -p no:cacheprovider

# 语法与导入完整性检查
env ENV=dev uv run --no-sync python -m compileall src/doc_process_studio

# 只跑某个域
env ENV=dev uv run --no-sync pytest tests/auth/ -q
```

详细测试开发指南见 [tests/DEVELOPMENT.md](tests/DEVELOPMENT.md)。

## 目录结构

```text
backend/src/doc_process_studio/
├── main.py                     # FastAPI 应用入口
├── core/                       # 基础设施（配置、数据库、安全、缓存、Ollama）
├── shared/                     # 跨模块共享工具
├── auth/                       # 业务域：认证
├── chat/                       # 业务域：对话
├── incident_report/            # 业务域：事故报告
├── skill/                      # 业务域：Skill 管理
├── system/                     # 业务域：系统
└── skills/                     # Skill 定义目录
```

各目录的详细说明见下方「目录开发文档」。

## 业务域规则

每个业务域内部强制包含 4 个子文件夹：

| 子文件夹 | 职责 | 约束 |
|---------|------|------|
| `router/` | API 路由 | 禁止写业务逻辑，只处理 HTTP 入参/出参/状态码 |
| `service/` | 业务逻辑 | 禁止操作 HTTP，只负责业务编排 |
| `models/` | ORM / 数据模型 | 禁止引入 Pydantic |
| `schemas/` | Pydantic 模型 | 入参 `request.py`、出参 `response.py`、共享基类 `common.py` |

### 跨层依赖方向

```
router → service → models
router → schemas
service → models
```

禁止反向依赖：
- 不要让 `models` 依赖 `services`
- 不要让 `router` 直接写 Redis 或 Ollama 调用
- 不要在 `models` 里引入 Pydantic

### 单文件拆分

单文件超过 300 行时，在子文件夹内继续拆分。例如 `chat/service/streaming/` 就是从 `stream.py` 拆出的子包。

## 开发约定

### Pydantic 模型只用 snake_case

所有 Pydantic 模型的字段统一使用 `snake_case`，不要引入 `AliasChoices`、`serialization_alias` 或 `by_alias=True`。前端已全部对齐 snake_case，后端序列化直接用 `model.model_dump()` 即可。

### 异步优先

所有 I/O 操作（数据库、HTTP、文件系统）统一使用 `async/await`。

### 类型注解

类型注解覆盖率 > 90%。

## 提交改动前建议自查

1. 新代码放在了正确的职责目录下（`router/` 不写业务，`service/` 不操作 HTTP，`models/` 不引入 Pydantic）
2. 没有重复写新的 Ollama/Redis 调用，而是复用了 `core/` 或 `shared/`
3. 涉及会话或 skill 的改动时，检查对应模型是否需要同步调整
4. 没有在 Pydantic 模型里引入 `AliasChoices`、`serialization_alias` 或 `by_alias=True`
5. `pytest` 和 `compileall` 通过

## 目录开发文档

| 目录 | 文档 | 说明 |
|------|------|------|
| `src/doc_process_studio/core/` | [core/DEVELOPMENT.md](src/doc_process_studio/core/DEVELOPMENT.md) | 基础设施（配置、数据库、安全、缓存、Ollama） |
| `src/doc_process_studio/shared/` | [shared/DEVELOPMENT.md](src/doc_process_studio/shared/DEVELOPMENT.md) | 跨模块共享工具 |
| `src/doc_process_studio/skills/` | [skills/DEVELOPMENT.md](src/doc_process_studio/skills/DEVELOPMENT.md) | Skill 定义与开发规范 |

## 业务域开发文档

| 业务域 | 文档路径 | 说明 |
|--------|----------|------|
| Auth | [src/doc_process_studio/auth/DEVELOPMENT.md](src/doc_process_studio/auth/DEVELOPMENT.md) | 认证与用户管理 |
| Chat | [src/doc_process_studio/chat/DEVELOPMENT.md](src/doc_process_studio/chat/DEVELOPMENT.md) | 对话功能 |
| IncidentReport | [src/doc_process_studio/incident_report/DEVELOPMENT.md](src/doc_process_studio/incident_report/DEVELOPMENT.md) | 事故报告 |
| Skill | [src/doc_process_studio/skill/DEVELOPMENT.md](src/doc_process_studio/skill/DEVELOPMENT.md) | Skill 管理 |
| System | [src/doc_process_studio/system/DEVELOPMENT.md](src/doc_process_studio/system/DEVELOPMENT.md) | 系统功能 |
