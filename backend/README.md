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

## 测试
后端改动完成后，使用 `uv` 作为统一入口，推荐本地这样跑：

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

### 测试目录约定

```text
backend/tests/
├── conftest.py                 # 全局 autouse fixture（Redis 状态重置等）
├── unit/                       # 单元测试
│   ├── chat/
│   ├── incident_report/
│   ├── skill/
│   │   ├── conftest.py         # Skill 域共享 fixture（build_skill, build_plan_decision）
│   │   ├── test_selector.py
│   │   ├── test_tool_loop.py
│   │   └── test_conversation_store.py
│   └── agent/
│       └── test_executor.py
├── integration/                # 集成测试
│   └── api/
└── skills/                     # Skill 契约测试
```

### 共享 Fixture 约定

- **全局 fixture**（`tests/conftest.py`）：`autouse`，用于重置全局状态（如 Redis 连接池），每个测试后自动执行
- **域级 fixture**（`tests/unit/<domain>/conftest.py`）：同一业务域内多个测试文件共用的 fixture，如 `build_skill`、`build_plan_decision`
- 新增测试时，如果构造数据的逻辑在 2 个以上测试文件中重复出现，应提取为域级 fixture

## 目录结构

后端采用混合架构模式，按业务域组织代码。每个业务域内部强制包含 `router/`、`service/`、`models/`、`schemas/` 四个子文件夹。

```text
backend/src/doc_process_studio/
├── main.py                     # FastAPI 应用入口
│
├── core/                       # 基础设施
│   ├── config.py               # 配置管理（Settings）
│   ├── db.py                   # Redis 连接池
│   ├── cache.py                # Redis 缓存操作
│   ├── exceptions.py           # 全局异常层级
│   ├── ollama.py               # Ollama HTTP 调用
│   ├── model_context.py        # 模型上下文长度缓存
│   ├── language_policy.py      # 语言检测与校验
│   ├── request_guard.py        # 请求防护（限流、并发）
│   └── session_store.py        # 通用 Redis 会话存储基类
│
├── shared/                     # 跨模块共享工具
│   ├── dtutils.py              # 日期时间（utcnow、utcnow_iso）
│   ├── text_utils.py           # 文本/JSON 解析（parse_json_object）
│   ├── tool_args.py            # 工具参数解析与规整
│   └── error_utils.py          # 错误事件构建
│
├── chat/                       # 业务域：对话
│   ├── router/
│   │   ├── stream.py           # 聊天流式 SSE 端点
│   │   ├── sessions.py         # 聊天会话 CRUD 端点
│   │   └── attachments.py      # 附件下载端点
│   ├── service/
│   │   ├── stream.py           # 流式聊天编排入口
│   │   ├── sessions.py         # 聊天会话 CRUD
│   │   ├── attachments.py      # 附件管理
│   │   ├── file_context.py     # 文件内容提取
│   │   ├── session_store.py    # 聊天会话 Redis 存储
│   │   └── streaming/          # SSE 格式化、工具调用合并、上下文构建
│   ├── models/
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
│   │   ├── generation.py       # AI 正文生成
│   │   ├── preview.py          # DOCX/PDF/HTML 预览
│   │   ├── translation.py      # 中英文翻译
│   │   ├── reference.py        # 参考文档选择
│   │   ├── normalization.py    # 日期/时间/状态归一化
│   │   ├── report_data.py      # 快照→report_data 构建
│   │   ├── constants.py        # 字段键常量
│   │   └── session_store.py    # 事故报告会话 Redis 存储
│   ├── models/
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

测试目录结构（详见上方"测试目录约定"）：

```text
backend/tests/
├── conftest.py                 # 全局 autouse fixture
├── unit/                       # 单元测试（纯逻辑，不依赖 HTTP）
│   ├── chat/                   # 对话域
│   ├── incident_report/          # 事故报告域
│   ├── skill/                  # Skill 域（含共享 conftest.py）
│   └── agent/                  # Agent 域
├── integration/                # 集成测试（HTTP 端到端）
│   └── api/                    # API 端点测试
└── skills/                     # Skill 契约测试
```

## 业务域开发文档

每个业务域有独立的开发文档，详细说明该域的 API、核心流程、跨域依赖和开发注意事项：

| 业务域 | 文档路径 | 说明 |
|--------|---------|------|
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
| `db.py` | Redis 连接池管理 |
| `cache.py` | Redis 缓存操作（get_json、set_json、build_cache_key 等） |
| `exceptions.py` | 全局异常层级（AppError、NotFoundError、ConflictError 等） |
| `ollama.py` | Ollama HTTP 调用（流式/非流式聊天、模型列表） |
| `model_context.py` | 模型上下文长度缓存与预热 |
| `language_policy.py` | 语言检测与校验（LLM 驱动） |
| `request_guard.py` | 请求防护（速率限制、并发控制） |
| `session_store.py` | 通用 `RedisSessionStore[TSummary, TSnapshot]` 泛型基类 |

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

## 提交改动前建议自查

1. 新代码放在了正确的职责目录下（`router/` 不写业务，`service/` 不操作 HTTP，`models/` 不引入 Pydantic）
2. 没有重复写新的 Ollama/Redis 调用，而是复用了 `core/` 或 `shared/`
3. 涉及会话或 skill 的改动时，检查对应模型是否需要同步调整
4. 没有在 Pydantic 模型里引入 `AliasChoices`、`serialization_alias` 或 `by_alias=True`
5. `pytest` 和 `compileall` 通过
