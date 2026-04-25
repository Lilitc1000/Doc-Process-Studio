# doc_process_studio 后端

## 配置
后端按环境分文件读取配置。运行时会先读取环境变量 `ENV`，再加载对应的配置文件：

- `ENV=dev` → `backend/.env.dev`
- `ENV=prod` → `backend/.env.prod`

如果没有显式设置 `ENV`，默认按 `dev` 处理。

启动前请先确认 `ENV` 和对应配置文件一致。

当前常用配置项直接按配置名读取，不再自动追加任何前缀。

建议把后端运行相关配置都写到对应的 `.env.<env>` 文件里，不要在代码里写死。

## 开发
```bash
cd backend
uv sync --group dev
uv run uvicorn doc_process_studio.main:app --reload --host 0.0.0.0 --port 8000
```

如果你要显式指定环境，可以这样启动：

```bash
cd backend
ENV=dev uv run uvicorn doc_process_studio.main:app --reload --host 0.0.0.0 --port 8000
```

## 数据库迁移

项目使用 Alembic 管理 PostgreSQL 数据库迁移，迁移配置位于 `backend/alembic.ini` 和 `backend/migrations/`。

```bash
cd backend

# 生成迁移脚本（根据 ORM 模型变更自动生成）
env ENV=dev uv run alembic revision --autogenerate -m "描述变更内容"

# 执行迁移（升级到最新版本）
env ENV=dev uv run alembic upgrade head

# 回退一个版本
env ENV=dev uv run alembic downgrade -1

# 查看当前迁移状态
env ENV=dev uv run alembic current

# 查看迁移历史
env ENV=dev uv run alembic history
```

注意事项：

- Alembic 使用异步引擎（asyncpg），`migrations/env.py` 已配置 `run_async_migrations`
- 新增 ORM 模型后，务必执行 `alembic revision --autogenerate` 生成迁移脚本
- 生成后请检查迁移脚本内容，确认自动检测的变更符合预期
- 生产环境部署前必须执行 `alembic upgrade head`

## 测试

后端改动完成后，使用 `uv` 作为统一入口：

```bash
cd backend
env ENV=dev uv run --no-sync pytest -q -p no:cacheprovider
env ENV=dev uv run --no-sync python -m compileall src/doc_process_studio
```

说明：

- 第一条是后端全量测试。
- 第二条是语法与导入完整性检查。
- 如果本机存在缓存目录权限问题，可附加：
  `UV_CACHE_DIR=/tmp/uv-cache TMPDIR=/tmp PYTHONDONTWRITEBYTECODE=1`

详细测试开发指南见 `tests/DEVELOPMENT.md`。

测试按业务域组织，每个域内再区分测试类型：

```text
backend/tests/
├── DEVELOPMENT.md      # 测试开发指南（必读）
├── conftest.py         # 全局 autouse fixture
├── auth/               # 认证域（unit/ + integration/）
├── chat/               # 对话域（unit/ + integration/）
├── incident_report/    # 事故报告域（unit/ + integration/ + contract/）
├── skill/              # 技能域（unit/ + integration/，含域级 conftest.py）
├── system/             # 系统域（unit/ + integration/）
└── core/               # 核心基础设施域（unit/）
```

## 目录结构

后端采用混合架构模式，按业务域组织代码。每个业务域内部强制包含 `router/`、`service/`、`models/`、`schemas/` 四个子文件夹。

```text
backend/src/doc_process_studio/
├── main.py                     # FastAPI 应用入口
│
├── core/                       # 基础设施
│   ├── config.py               # 配置管理（Settings）
│   ├── database.py             # PostgreSQL 异步连接池 + SQLAlchemy Base
│   ├── security.py             # JWT 令牌 + 密码哈希 + get_current_user_id 依赖
│   ├── cache_client.py         # Redis 连接池
│   ├── cache.py                # Redis 缓存操作
│   ├── exceptions.py           # 全局异常层级
│   ├── ollama.py               # Ollama HTTP 调用
│   ├── model_context.py        # 模型上下文长度缓存
│   ├── language_policy.py      # 语言检测与校验
│   └── request_guard.py        # 请求防护（限流、并发）
│
├── shared/                     # 跨模块共享工具
│   ├── dtutils.py              # 日期时间（utcnow、utcnow_iso）
│   ├── text_utils.py           # 文本/JSON 解析（parse_json_object）
│   ├── tool_args.py            # 工具参数解析与规整
│   └── error_utils.py          # 错误事件构建
│
├── auth/                       # 业务域：认证与用户管理
│   ├── router/
│   │   └── auth.py             # 认证端点（注册、登录、刷新令牌、用户信息、登出）
│   ├── service/
│   │   └── auth.py             # 认证业务逻辑（JWT、密码哈希、令牌管理）
│   ├── models/
│   │   └── user.py             # SQLAlchemy ORM 模型（User）
│   └── schemas/
│       ├── request.py          # 入参 Pydantic 模型
│       └── response.py         # 出参 Pydantic 模型
│
├── chat/                       # 业务域：对话
│   ├── router/
│   │   ├── stream.py           # 聊天流式 SSE 端点
│   │   ├── sessions.py         # 聊天会话 CRUD 端点
│   │   └── attachments.py      # 附件下载端点
│   ├── service/
│   │   ├── stream.py           # 流式聊天编排入口
│   │   ├── sessions.py         # 聊天会话 CRUD
│   │   ├── db_session_store.py # 聊天会话 PostgreSQL 存储
│   │   ├── attachments.py      # 附件管理
│   │   ├── file_context.py     # 文件内容提取
│   │   └── streaming/          # SSE 格式化、工具调用合并、上下文构建
│   ├── models/
│   │   ├── chat_session_orm.py # ChatSession ORM 模型
│   │   ├── session.py          # 会话摘要、快照模型
│   │   ├── message.py          # 消息输入、流式请求模型
│   │   ├── attachment.py       # 附件模型
│   │   └── file_context.py     # 上传文件上下文模型
│   └── schemas/
│       ├── request.py          # 入参 Pydantic 模型
│       ├── response.py         # 出参 Pydantic 模型
│       └── common.py           # 共享基类
│
├── incident_report/            # 业务域：事故报告
│   ├── router/
│   │   └── incident_reports.py # 事故报告端点
│   ├── service/
│   │   ├── session.py          # 会话 CRUD
│   │   ├── db_session_store.py # 事故报告会话 PostgreSQL 存储
│   │   ├── generation.py       # AI 正文生成
│   │   ├── preview.py          # DOCX/PDF/HTML 预览
│   │   ├── translation.py      # 中英文翻译
│   │   ├── reference.py        # 参考文档选择
│   │   ├── normalization.py    # 日期/时间/状态归一化
│   │   ├── report_data.py      # 快照→report_data 构建
│   │   └── constants.py        # 字段键常量
│   ├── models/
│   │   ├── incident_report_session_orm.py # IncidentReportSession ORM 模型
│   │   └── incident_report.py  # 事故报告数据模型
│   └── schemas/
│       ├── request.py          # 入参 Pydantic 模型
│       ├── response.py         # 出参 Pydantic 模型
│       └── common.py           # 共享基类
│
├── skill/                      # 业务域：Skill 管理
│   ├── router/
│   │   └── routes.py           # Skill 列表、交互、上下文端点
│   ├── service/
│   │   ├── registry.py         # 文件系统 Skill 发现
│   │   ├── planner.py          # LLM Skill 选择
│   │   ├── selector.py         # Skill 选择策略
│   │   ├── context.py          # BM25 + 语义上下文检索
│   │   ├── context_packer.py   # 层级记忆压缩
│   │   ├── conversation_store.py # 会话状态 Redis 存储
│   │   ├── tool_loop.py        # 工具执行循环
│   │   └── runtime.py          # 上下文状态同步
│   ├── models/
│   │   ├── catalog.py          # Skill 目录模型
│   │   ├── interaction.py      # 交互步骤模型
│   │   └── runtime.py          # 运行时状态模型
│   └── schemas/
│       ├── request.py          # 入参 Pydantic 模型
│       ├── response.py         # 出参 Pydantic 模型
│       └── common.py           # 共享基类
│
├── system/                     # 业务域：系统
│   ├── router/
│   │   ├── health.py           # 健康检查端点
│   │   ├── models.py           # Ollama 模型列表端点
│   │   └── agent_traces.py     # Agent trace 回放端点
│   ├── service/
│   │   ├── executor.py         # DAG 工具图执行器
│   │   ├── quality_gate.py     # 质量门控
│   │   ├── feature_flags.py    # SHA256 灰度发布
│   │   ├── trace_store.py      # Redis trace 存储
│   │   └── error_detail.py     # 异常详情构建
│   ├── models/
│   │   ├── agent_trace.py      # Agent trace 记录模型
│   │   └── ollama.py           # Ollama 模型记录
│   └── schemas/
│       ├── request.py          # 入参 Pydantic 模型
│       ├── response.py         # 出参 Pydantic 模型
│       └── common.py           # 共享基类
│
└── skills/                     # Skill 定义目录
    └── <skill-id>/
```

测试目录结构详见上方"测试"章节。

## 业务域开发文档

每个业务域有独立的开发文档，详细说明该域的 API、核心流程、跨域依赖和开发注意事项：

| 业务域 | 文档路径 | 说明 |
|--------|---------|------|
| Auth | `src/doc_process_studio/auth/DEVELOPMENT.md` | 认证与用户管理：注册、登录、JWT 令牌、用户资料、密码修改 |
| Chat | `src/doc_process_studio/chat/DEVELOPMENT.md` | 对话功能：消息流式生成、会话管理、附件 |
| Incident | `src/doc_process_studio/incident_report/DEVELOPMENT.md` | 事故报告：表单、AI 生成、预览、翻译 |
| Skill | `src/doc_process_studio/skill/DEVELOPMENT.md` | Skill 管理：发现、选择、上下文检索、工具执行 |
| System | `src/doc_process_studio/system/DEVELOPMENT.md` | 系统功能：健康检查、模型管理、trace 审计、执行器 |

## 业务域规则

每个业务域（`chat/`、`incident_report/`、`skill/`、`system/`）内部强制包含 4 个子文件夹：

| 子文件夹 | 职责 | 约束 |
|---------|------|------|
| `router/` | API 路由 | 禁止写业务逻辑，只处理 HTTP 入参/出参/状态码 |
| `service/` | 业务逻辑 | 禁止操作 HTTP，只负责业务编排 |
| `models/` | ORM / 数据模型 | 禁止引入 Pydantic（models 是纯数据结构） |
| `schemas/` | Pydantic 模型 | 入参 `request.py`、出参 `response.py`、共享基类 `common.py` |

### 导入约定

- 外部调用统一通过 `__init__.py`：`from src.chat.service import create_token`
- `router/__init__.py` 聚合路由
- `service/__init__.py` 导出公共接口
- `models/__init__.py` 导出 ORM 模型
- `schemas/__init__.py` 导出 Pydantic 模型
- 推荐优先从明确的模块文件导入，而不是为了省事从包根导入

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

## 核心基础设施（core/）

| 模块 | 职责 |
|------|------|
| `config.py` | 所有配置参数（Settings 类），从环境变量 / `.env` 文件读取 |
| `database.py` | PostgreSQL 异步连接池（SQLAlchemy async engine + session） |
| `security.py` | JWT 令牌生成/验证、密码哈希/校验 |
| `db.py` | Redis 连接池管理 |
| `cache.py` | Redis 缓存操作（get_json、set_json、build_cache_key 等） |
| `exceptions.py` | 全局异常层级（AppError、NotFoundError、ConflictError 等） |
| `ollama.py` | Ollama HTTP 调用（流式/非流式聊天、模型列表） |
| `model_context.py` | 模型上下文长度缓存与预热 |
| `language_policy.py` | 语言检测与校验（LLM 驱动） |
| `request_guard.py` | 请求防护（速率限制、并发控制） |

## 跨模块共享（shared/）

如果某个函数在两个及以上业务模块里重复出现，优先收敛到 `shared/`：

| 模块 | 职责 |
|------|------|
| `dtutils.py` | 日期时间（`utcnow`、`utcnow_iso`） |
| `text_utils.py` | 文本/JSON 解析（`parse_json_object`） |
| `tool_args.py` | 工具参数解析与规整 |
| `error_utils.py` | 错误事件构建 |

## 路由注册

路由在 `main.py` 中统一注册，从各业务域的 `router/` 子包导入：

```python
from .chat.router.stream import router as chat_stream_router
from .chat.router.sessions import router as chat_sessions_router
from .incident_report.router.incident_reports import router as incident_reports_router
from .skill.router.routes import router as skill_routes_router
from .system.router.health import router as health_router
```

新增路由模块时：
1. 把路由文件放到对应业务域的 `router/` 子包
2. 在 `main.py` 中导入并注册
3. 不要在 `router/` 里写业务逻辑

## 认证与用户管理

后端提供完整的 JWT 认证体系，所有业务 API 均需携带 `Authorization: Bearer <token>` 请求头。详细开发指南见 `src/doc_process_studio/auth/DEVELOPMENT.md`。

### 认证 API

| 端点 | 方法 | 说明 | 是否需要认证 |
|------|------|------|------------|
| `/api/auth/register` | POST | 用户注册 | 否 |
| `/api/auth/login` | POST | 用户登录（form-urlencoded） | 否 |
| `/api/auth/refresh` | POST | 刷新令牌 | 否 |
| `/api/auth/me` | GET | 获取当前用户信息 | 是 |
| `/api/auth/me` | PUT | 更新用户资料 | 是 |
| `/api/auth/password` | PUT | 修改密码 | 是 |
| `/api/auth/logout` | POST | 登出 | 是 |
| `/api/auth/users/{user_id}` | DELETE | 删除用户账号 | 是 |
| `/api/auth/users/by-prefix/{prefix}` | DELETE | 按用户名前缀批量删除（仅 dev） | 否 |
| `/api/auth/rate-limit-whitelist` | POST | 速率限制白名单（仅 dev） | 否 |
| `/api/auth/ensure-admin` | POST | 确保管理员用户存在（仅 dev） | 否 |

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `DATABASE_URL` | PostgreSQL 连接字符串 | `postgresql+asyncpg://admin:postgres_password@db:5432/master` |
| `JWT_SECRET_KEY` | JWT 签名密钥 | `your-super-secret-key-change-in-production-min-32-chars` |
| `JWT_ALGORITHM` | JWT 算法 | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | access_token 有效期（分钟） | `15` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | refresh_token 有效期（天） | `7` |
| `ADMIN_USERNAME` | 默认管理员用户名 | `admin` |
| `ADMIN_PASSWORD` | 默认管理员密码 | `admin123` |

## 事故报告工作区

`incident-report` 在注册中心标记为 `skill_type=workspace_incident`。

- 聊天通道只允许 `skill_type=chat` 的 skill 进入规划与执行。
- 事故报告会话与聊天会话分开存储、分开展示、分开状态管理。

事故报告后端接口：

- `GET /api/incident-report/schema`：获取事故报告表单定义
- `GET /api/incident-report/sessions`：获取事故报告会话列表
- `POST /api/incident-report/sessions`：创建事故报告会话
- `GET /api/incident-report/sessions/{session_id}`：读取会话详情
- `PUT /api/incident-report/sessions/{session_id}`：实时保存表单答案
- `POST /api/incident-report/sessions/{session_id}/body/quick-generate`：快填正文生成
- `POST /api/incident-report/sessions/{session_id}/body/section-generate`：完整模式分段生成
- `POST /api/incident-report/sessions/{session_id}/preview`：预览附件
- `PATCH /api/incident-report/sessions/{session_id}/title`：修改标题
- `DELETE /api/incident-report/sessions/{session_id}`：删除会话

正文生成链路（涉及 LLM）：

1. 快填模式仅输入简述文本，调用 `body/quick-generate`
2. 模型返回 JSON，后端统一回填到完整模式字段
3. 完整模式支持分段生成
4. 每次正文生成都会记录 `trace_id` 并落入 `section_trace_ids`

## Tool Calling 与 Skill 上下文

当前主链路已升级为"分层规划 + 会话级 Agent 状态 + 执行器调度 + 生产级可靠性防护"。

### 主链路流程

1. 入口接收 `/api/chat/stream` 请求，做请求防护（速率限制、并发控制、超时保护）
2. 按 feature flag 决定是否启用规划器灰度
3. 加载会话级 Agent 状态（Redis）
4. 检索与上下文组装（BM25 + embedding 混合召回 + 层级记忆）
5. 流式调用 Ollama，若有工具调用则进入执行器
6. 结束后落盘 trace 审计记录

### 关键实现位置

- 通用选择入口：`skill/service/selector.py`
- 规划核心：`skill/service/planner.py`
- 检索：`skill/service/context.py`
- 层级记忆：`skill/service/context_packer.py`
- 执行器：`system/service/executor.py`
- 质量门控：`system/service/quality_gate.py`
- 请求防护：`core/request_guard.py`
- 审计追踪：`system/service/trace_store.py`
- 流式编排：`chat/service/stream.py`

## Skill 开发约定

Skill 内容来自 `skills/` 目录。每个 skill 至少应包含：

- `agents/config.yaml`
- `interface.display_name`
- `interface.default_prompt`

如果要补充大体量参考资料，优先放到 `references/`。

如果 skill 需要声明可执行工具，推荐在 skill 目录下增加 `tools.json`。

## 生成文件与下载

- 文件落到 `backend/generated-attachments/`
- 该目录已加入 `.gitignore`
- 默认有效期 7 天
- 过期文件会在启动时、生成新文件时、下载文件前自动清理
- 统一下载接口：`GET /api/attachments/{attachment_id}/download`

## 开发约定

### Pydantic 模型只用 snake_case

所有 Pydantic 模型的字段统一使用 `snake_case`，不要引入 `AliasChoices`、`serialization_alias` 或 `by_alias=True`。

前端已全部对齐 snake_case，后端序列化直接用 `model.model_dump()` 即可。

### 异步优先

所有 I/O 操作（数据库、HTTP、文件系统）统一使用 `async/await`。

### 类型注解

类型注解覆盖率 > 90%。

### 认证开发注意事项

详细开发指南见 `src/doc_process_studio/auth/DEVELOPMENT.md`，以下为关键要点：

1. **bcrypt 版本兼容性**：passlib 的 bcrypt 后端与 `bcrypt>=5.0.0` 不兼容，`pyproject.toml` 中已锁定 `bcrypt>=4.0.1,<5.0.0`
2. **登录接口格式**：`/api/auth/login` 使用 `OAuth2PasswordRequestForm`，请求体必须是 `application/x-www-form-urlencoded` 格式，不是 JSON
3. **速率限制与白名单**：注册和登录接口有速率限制（5 次/60 秒/客户端 IP），E2E 测试应在 `beforeAll` 中调用 `POST /api/auth/rate-limit-whitelist` 加入白名单
4. **测试专用端点**：`by-prefix`、`rate-limit-whitelist`、`ensure-admin` 仅在 dev 环境注册，生产环境不可访问
5. **共享认证依赖**：`get_current_user_id` 定义在 `core/security.py`，其他域通过 `from ...core.security import get_current_user_id` 引用
6. **ORM 模型归属**：每个业务域的 ORM 模型放在自己的 `models/` 目录下，`Base` 定义在 `core/database.py`

### 测试开发注意事项

1. **异步引擎清理**：`tests/conftest.py` 中有 `_dispose_async_engine` autouse fixture，每个测试后自动调用 `engine.dispose()` 释放连接池，避免异步测试间的连接泄漏
2. **缓存客户端重置**：`_reset_cache_client` autouse fixture 会在每个测试后清空 Redis 客户端和连接池
3. **速率限制器重置**：`_reset_rate_limiter` autouse fixture 会在每个测试后清空 `_auth_rate_windows` 和 `_RATE_LIMIT_WHITELIST`，防止速率限制状态在测试间泄漏
4. **认证测试隔离**：集成测试中使用 `monkeypatch` 替换 service 层函数，避免测试依赖真实数据库；Pydantic 响应模型字段使用 snake_case（如 `avatar_color` 不是 `avatarColor`）
5. **auth_headers fixture**：`conftest.py` 提供 `auth_headers` fixture，生成包含有效 JWT 的 `Authorization` 请求头，用于需要认证的 API 测试

## 提交改动前建议自查

1. 新代码放在了正确的职责目录下（`router/` 不写业务，`service/` 不操作 HTTP，`models/` 不引入 Pydantic）
2. 没有重复写新的 Ollama/Redis 调用，而是复用了 `core/` 或 `shared/`
3. 涉及会话或 skill 的改动时，检查对应模型是否需要同步调整
4. 没有在 Pydantic 模型里引入 `AliasChoices`、`serialization_alias` 或 `by_alias=True`
5. `pytest` 和 `compileall` 通过
