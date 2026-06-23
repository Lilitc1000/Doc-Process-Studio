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

# 语法与代码规范检查
env ENV=dev uv run --no-sync ruff check src/doc_process_studio

# 自动格式化代码
env ENV=dev uv run --no-sync ruff format src/doc_process_studio

# 类型检查
env ENV=dev uv run --no-sync mypy src/doc_process_studio

# 只跑某个域
env ENV=dev uv run --no-sync pytest tests/auth/ -q
```

详细测试开发指南见 [tests/DEVELOPMENT.md](tests/DEVELOPMENT.md)。

## 目录结构

```text
backend/src/doc_process_studio/
├── main.py                     # FastAPI 应用入口
├── core/                       # 基础设施（配置、数据库、安全、缓存、Ollama、Qdrant）
├── shared/                     # 跨模块共享工具
├── auth/                       # 业务域：认证
├── chat/                       # 业务域：对话
├── incident_report/            # 业务域：事故报告
├── knowledge_base/             # 业务域：知识库
├── skill/                      # 业务域：Skill 管理
├── system/                     # 业务域：系统
└── skills/                     # Skill 定义目录
```

各目录的详细说明见下方「目录开发文档」。

### DDD 分层架构

所有业务域（auth、chat、incident_report、knowledge_base、skill、system）均采用 DDD 分层架构，在 4 子文件夹基础上新增 `domain/`、`application/`、`infrastructure/` 三层：

| 子文件夹 | 职责 | 约束 |
|---------|------|------|
| `domain/` | 领域层：领域异常（复杂域可含聚合根、值对象、领域事件） | 不依赖任何框架和其他层 |
| `application/` | 应用层：用例编排、端口定义 | 依赖 domain + 端口抽象，不依赖 infrastructure 实现 |
| `infrastructure/` | 基础设施层：端口实现（仓储、外部服务适配器）、依赖装配 | 实现 application 端口，依赖 ORM 和外部服务 |
| `router/` | API 路由 | 通过 `Depends` 注入 application 服务，仅做参数解析与异常映射 |
| `service/` | 保留的工具层 | 纯函数工具，被 infrastructure 委托，也可被跨域直接调用 |
| `models/` | ORM / 数据模型 | 禁止引入 Pydantic |
| `schemas/` | Pydantic 模型 | HTTP DTO |

各域分层深度按业务复杂度调整：incident_report 含完整聚合根与领域事件；auth/system/chat/knowledge_base/skill 采用轻量分层（domain 仅含领域异常，application 定义端口+用例服务，infrastructure 委托 service/ 工具层）。

### 跨层依赖方向

DDD 业务域：
```
router → application → domain
router → schemas
infrastructure → application（实现端口） → domain
infrastructure → models
infrastructure → service（委托工具函数）
```

禁止反向依赖：
- 不要让 `domain` 依赖任何其他层
- 不要让 `application` 依赖 `infrastructure` 具体实现（只依赖端口）
- 不要让 `models` 依赖 `services`
- 不要让 `router` 直接写 Redis 或 Ollama 调用
- 不要在 `models` 里引入 Pydantic

### 依赖注入

应用服务通过 `infrastructure/dependencies.py` 装配，使用 `@lru_cache(maxsize=1)` 单例。router 通过 `Depends(get_xxx_service)` 注入。测试时通过 `app.dependency_overrides[get_xxx_service]` 替换为桩服务。

### 异常映射

router 将领域异常映射为 HTTP 状态码（如 `NotFoundError`→404、`AccessDeniedError`→403、`ExpiredError`→410），不向客户端暴露内部异常。

### 单文件拆分

单文件超过 300 行时，在子文件夹内继续拆分。例如 `chat/service/streaming/` 就是从 `stream.py` 拆出的子包。

## 开发约定

### Pydantic 模型只用 snake_case

所有 Pydantic 模型的字段统一使用 `snake_case`，不要引入 `AliasChoices`、`serialization_alias` 或 `by_alias=True`。前端已全部对齐 snake_case，后端序列化直接用 `model.model_dump()` 即可。

### 异步优先

所有 I/O 操作（数据库、HTTP、文件系统）统一使用 `async/await`。

### 类型注解

类型注解覆盖率 > 90%。

- ORM 模型统一使用 SQLAlchemy 2.0 的 `Mapped[]` + `mapped_column()` 声明式类型注解
- 每个 `models/` 目录包含 `__init__.py`，通过包级导入将 ORM 模型注册到 `Base.metadata`，供 Alembic 迁移自动发现
- mypy 配置启用 `sqlalchemy.ext.mypy.plugin` 插件，配置项见 `pyproject.toml`

## 提交改动前建议自查

1. 新代码放在了正确的职责目录下（`router/` 不写业务，`service/` 不操作 HTTP，`models/` 不引入 Pydantic）
2. 没有重复写新的 Ollama/Redis 调用，而是复用了 `core/` 或 `shared/`
3. 涉及会话或 skill 的改动时，检查对应模型是否需要同步调整
4. 没有在 Pydantic 模型里引入 `AliasChoices`、`serialization_alias` 或 `by_alias=True`
5. `pytest`、`ruff check`、`ruff format` 和 `mypy` 通过

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
| KnowledgeBase | [src/doc_process_studio/knowledge_base/DEVELOPMENT.md](src/doc_process_studio/knowledge_base/DEVELOPMENT.md) | 知识库管理 |
| Skill | [src/doc_process_studio/skill/DEVELOPMENT.md](src/doc_process_studio/skill/DEVELOPMENT.md) | Skill 管理 |
| System | [src/doc_process_studio/system/DEVELOPMENT.md](src/doc_process_studio/system/DEVELOPMENT.md) | 系统功能 |
