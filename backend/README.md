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
├── common/                     # 共享内核（跨域通用基础设施）
│   ├── infrastructure/         #   配置、数据库、缓存、Ollama、Qdrant、异常
│   ├── security/               #   JWT、密码哈希、认证
│   ├── middleware/             #   请求日志、请求ID、请求防护
│   └── utils/                  #   日期工具、文本工具、错误工具、参数工具
├── auth/                       # 业务域：认证
├── chat/                       # 业务域：对话
├── incident_report/            # 业务域：事故报告
├── knowledge_base/             # 业务域：知识库
├── skill/                      # 业务域：Skill 管理
├── system/                     # 业务域：系统
└── skills/                     # Skill 定义目录
```

各目录的详细说明见下方「目录开发文档」。

### DDD 四层架构（端口与适配器模式）

所有业务域均采用 DDD 四层架构，遵循端口与适配器（六边形）模式：

| 层 | 子目录 | 职责 | 约束 |
|----|--------|------|------|
| 领域层 | `domain/` | 领域异常、聚合根、值对象、领域事件 | 不依赖任何框架和其他层 |
| 应用层 | `application/` | 用例编排、端口定义、DTO | 依赖 domain + 端口抽象，不依赖 infrastructure 实现 |
| 基础设施层 | `infrastructure/` | 端口实现（仓储、适配器）、ORM、依赖装配 | 实现 application 端口，依赖 ORM 和外部服务 |
| 用户接口层 | `router/` | API 路由、请求/响应 Schema | 通过 `Depends` 注入 application 服务，仅做参数解析与异常映射 |

各域分层深度按业务复杂度调整：
- **incident_report**（复杂域）：完整四层 + 子文件夹（domain/entities|events|values、application/services|ports|dtos、infrastructure/repositories|adapters|persistence|utils）
- **auth/chat/knowledge_base/skill/system**（轻量域）：四层扁平结构（domain 含领域异常，application 含端口+用例+DTO，infrastructure 含实现+依赖装配）

### 跨层依赖方向

```
router → application → domain
infrastructure → application（实现端口） → domain
common → 无依赖（被所有域引用）
```

禁止反向依赖：
- 不要让 `domain` 依赖任何其他层
- 不要让 `application` 依赖 `infrastructure` 具体实现（只依赖端口）
- 不要让 `router` 直接写 Redis 或 Ollama 调用
- 跨域调用必须通过端口抽象（`application/ports.py`），由 infrastructure 层提供适配器实现

### 依赖注入

应用服务通过 `infrastructure/dependencies.py` 装配，使用 `@lru_cache(maxsize=1)` 单例。router 通过 `Depends(get_xxx_service)` 注入。测试时通过 `app.dependency_overrides[get_xxx_service]` 替换为桩服务。

### 异常映射

router 将领域异常映射为 HTTP 状态码（如 `SessionNotFoundError`→404、`AccessDeniedError`→403、`AttachmentExpiredError`→410），不向客户端暴露内部异常。

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
- ORM 模型归属各域的 `infrastructure/persistence/` 目录，通过 `Base.metadata` 注册供 Alembic 迁移自动发现
- mypy 配置启用 `sqlalchemy.ext.mypy.plugin` 插件，配置项见 `pyproject.toml`

## 提交改动前建议自查

1. 新代码放在了正确的职责目录下（`router/` 不写业务，`infrastructure/` 不跨域直接调用，`domain/` 不依赖框架）
2. 没有重复写新的 Ollama/Redis 调用，而是复用了 `common/` 中的基础设施
3. 跨域调用通过 `application/ports.py` 端口抽象，不直接 import 其他域的 service 或 infrastructure
4. 涉及会话或 skill 的改动时，检查对应模型是否需要同步调整
5. 没有在 Pydantic 模型里引入 `AliasChoices`、`serialization_alias` 或 `by_alias=True`
6. `pytest`、`ruff check`、`ruff format` 和 `mypy` 通过

## 目录开发文档

| 目录 | 文档 | 说明 |
|------|------|------|
| `src/doc_process_studio/common/` | [common/DEVELOPMENT.md](src/doc_process_studio/common/DEVELOPMENT.md) | 共享内核（配置、安全、中间件、工具） |
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
