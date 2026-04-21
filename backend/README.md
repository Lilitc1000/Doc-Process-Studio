# doc_process_studio 后端

## 配置
后端现在按环境分文件读取配置。
运行时会先读取环境变量 `ENV`，再加载对应的配置文件：

- `ENV=dev` -> `backend/.env.dev`
- `ENV=prod` -> `backend/.env.prod`

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

## 测试文件开发指南
为了保证后续维护可控，建议新增测试时遵循“通用能力优先、skill 专项最小化补充”的原则。

### 目录与分层
- `tests/test_*_api.py`
  放接口行为测试（请求参数、状态码、返回结构、流式事件序列）。
- `tests/test_*_service.py` / `tests/test_*_tool_loop.py`
  放纯业务或工具循环逻辑测试，尽量避免走完整 HTTP。
- `tests/test_skill_registry_smoke.py`
  放全局 skill 冒烟校验（目录可发现、`agents/openai.yaml` 可读、`tools.json`/`agents/interaction.json` 可解析）。
- `tests/skills/<skill_id>/test_*_contract.py`
  放单个 skill 的契约测试（脚本参数、工具链输入输出、关键产物结构）。

### 命名建议
- `*_api.py`：接口与流式链路。
- `*_contract.py`：skill/tool/script 契约。
- `*_smoke.py`：注册与基础可用性。

### 编写约定
- 优先复用 `tests/conftest.py` 的 fixture，不要在每个文件重复搭环境。
- 外部依赖（远端 Ollama、真实 Redis、文件系统副作用）默认用可控替身或临时目录隔离。
- 流式接口测试建议断言事件顺序和关键事件类型（如 `tool-status`、`attachment`、`done`），不要只断言最终文本。
- skill 相关测试优先走真实 `tools.json` 声明链路，避免在测试里硬编码一套与生产不同的执行分支。

### 新增 skill 时的最小测试清单
1. 通过 `test_skill_registry_smoke.py`（无需特判即可被发现并解析配置）。
2. 在 `tests/skills/<skill_id>/` 下至少增加 1 条工具链契约测试（输入 -> 工具调用 -> 输出结构）。
3. 如果该 skill 是工作区专用类型（例如 incident-report），补 1 条“表单校验 + 生成附件 + 状态落盘 + trace 回放”的链路测试。

## 目录结构
当前后端按职责分组，不再使用扁平目录。

```text
backend/src/doc_process_studio
├── main.py
├── settings.py
├── models
│   ├── conversation
│   ├── skill
│   └── system
├── routers
│   ├── conversation
│   ├── skill
│   └── system
├── services
│   ├── agent
│   ├── chat
│   ├── infra
│   └── skill
└── skills
    └── <skill-id>
```

各层职责约定如下：

- `models`
  只放 Pydantic 模型和纯数据结构，不放业务逻辑。
- `routers`
  只处理 HTTP 入参、出参、状态码和路由注册，不在这里写复杂业务。
- `services`
  放真正的业务逻辑。
- `services/infra`
  放 Ollama、Redis 这类基础设施访问逻辑。
- `skills`
  放本地 skill 定义、提示词和参考资料，不属于普通 Python 业务模块。

## 子包说明
### `models/conversation`
负责聊天流式请求、历史会话快照、附件展示信息等和“会话”有关的数据结构。

### `models/skill`
负责 skill 注册信息、skill chunk、skill 会话状态、skill 缓存响应模型。

### `models/system`
负责系统级模型，目前主要是远端 Ollama 模型列表相关结构。

### `services/chat`
负责聊天主链路：

- 上传文件内容抽取
- 聊天流式编排（入口在 `services/chat/stream.py`，子模块在 `services/chat/streaming/`）
- 历史会话读写
- 标题生成
- 生成文件产物保存与下载

### `services/skill`
负责 skill 主链路：

- 读取 skill 注册信息
- 拆分 `SKILL.md` 和 references
- 对 skill chunk 做检索
- 暴露受控工具给远端模型
- 管理 skill 会话缓存
- 组装 skill 上下文
- 执行 skill 脚本型工具

### `services/infra`
负责与外部依赖交互和跨模块共享基础设施：

- Ollama HTTP 调用
- Redis 读写
- 通用会话存储基类
- 跨模块共享工具函数

如果某个函数在两个及以上业务模块里重复出现，优先收敛到这里。

### `routers/*`
每个子包负责一组 HTTP 路由，最终由总入口统一收集。

## 路由注册约定
路由不是在 `main.py` 里手动逐个导入，而是走聚合注册。

- 每个路由子包在自己的 `__init__.py` 中维护 `routers`
- 总入口 [routers/__init__.py](/backend/src/doc_process_studio/routers/__init__.py) 统一汇总
- [main.py](/backend/src/doc_process_studio/main.py) 只负责遍历注册

如果你要新增一个路由模块，建议按下面步骤做：

1. 把路由文件放到对应子包，例如 `routers/conversation/xxx.py`
2. 在该子包的 `__init__.py` 里把新的 `router` 加入 `routers`
3. 不要再去 `main.py` 里单独手写注册

这样可以保证入口结构始终一致。

## 开发约定
### 1. 跨层依赖方向
建议保持下面这个方向：

- `routers -> services -> infra`
- `routers -> models`
- `services -> models`

尽量不要反过来依赖，比如：

- 不要让 `models` 依赖 `services`
- 不要让 `infra` 反向依赖业务层
- 不要在 `routers` 里直接写 Redis 或 Ollama 调用

### 2. 导入习惯
推荐优先从明确的模块文件导入，而不是为了省事到处从包根导入。

例如：

```python
from doc_process_studio.services.chat.stream import stream_remote_chat_completion
from doc_process_studio.services.skill.runtime import ensure_skill_context_for_request
```

这样更利于定位实现位置，也能减少子包导出变化带来的影响。

### 3. `__init__.py` 的定位
子包的 `__init__.py` 现在只暴露“推荐使用的公开入口”，不会把所有内部 helper 都导出来。

如果你需要使用内部细节函数，比如某个调度器或某个打包器的私有辅助方法，优先直接从对应文件导入，不要强行塞回 `__init__.py`。

### 4. 不要过度设计
这个项目当前更适合"轻分层 + 清晰职责"，不建议一上来做：

- 很重的 DDD 分层
- 每个 service 再套 interface
- 为了抽象而抽象出多层空壳

如果一个能力只在一个地方用到，而且逻辑不复杂，直接放在当前职责文件里通常更合适。

### 5. Pydantic 模型只用 snake_case
所有 Pydantic 模型的字段统一使用 `snake_case`，不要引入 `AliasChoices`、`serialization_alias` 或 `by_alias=True`。

前端已全部对齐 snake_case，后端序列化直接用 `model.model_dump()` 即可，不需要任何别名映射。

### 6. 重复逻辑收敛到 infra
如果同一个函数在两个及以上业务模块里重复出现，优先收敛到 `services/infra/` 下的对应模块，不要各自维护私有副本。

## 常见改动应该放哪里
### 新增聊天接口
放到：

- `models/conversation`
- `services/chat`
- `routers/conversation`

### 新增 skill 缓存逻辑
放到：

- `models/skill`
- `services/skill`

如果涉及 Redis 读写细节，再放一部分到：

- `services/infra`

### 新增远端 Ollama 调用方式
优先考虑收敛到：

- `services/infra/ollama_client.py`

不要在多个业务文件里各自手写一套 `httpx.AsyncClient` 调用。

### 新增历史会话字段
通常需要同步检查：

- `models/conversation/sessions.py`
- `services/chat/sessions.py`
- 前端对应的会话保存/恢复逻辑

### 新增会话存储
如果需要新增一种会话存储（例如新的工作区类型），优先复用 `services/infra/session_store.py` 的 `RedisSessionStore[TSummary, TSnapshot]` 泛型基类，只需定义自己的 Summary 和 Snapshot 模型即可，不要重新写一套 Redis 读写逻辑。

参考现有用法：[session_store](/backend/src/doc_process_studio/services/chat/session_store.py)、[incident_session_store](/backend/src/doc_process_studio/services/chat/incident_session_store.py)。

### 新增跨模块共享工具函数
如果某个工具函数在两个及以上业务模块里需要使用，放到 `services/infra/` 下对应模块：

- `dtutils.py`：日期时间（`utcnow`、`utcnow_iso`）
- `text_utils.py`：文本/JSON 解析（`parse_json_object`）
- `error_utils.py`：错误事件构建（`build_error_event_detail`）
- `tool_args.py`：工具参数解析与规整
- `request_guard.py`：请求防护与租户归一化（`normalize_tenant_id`）
- `model_context.py`：模型上下文长度估算与 prompt 预算

如果现有模块不合适，可以新建，但保持 `services/infra/` 下的模块职责单一。

## Skill 开发约定
Skill 内容来自 [skills](/backend/src/doc_process_studio/skills) 目录。

每个 skill 至少应包含：

- `agents/openai.yaml`
- `interface.display_name`
- `interface.default_prompt`

如果要补充大体量参考资料，优先放到：

- `references/`

不要把很大的正文直接硬编码进 Python 文件。

如果 skill 需要声明可执行工具，推荐在 skill 目录下增加：

- `tools.json`

当前推荐模式是：

- `SKILL.md`
  负责给模型看的自然语言工作流程
- `references/`
  负责补充说明、规则、模板等资料
- `tools.json`
  负责给 backend 提供机器可读的声明式工具配置

对于当前只需要“读取文档 / 检索资料 / 输出分析结果”的 skill，也建议保留一个最小模板：

```json
{
  "tools": []
}
```

这样可以让所有 skill 维持统一结构，但不会因为空模板而额外暴露可执行工具。

也就是说：

- 模型先按需读取 `SKILL.md`
- 再根据 `SKILL.md` 决定是否继续读取 `references/`
- 若确实需要执行脚本或生成文件，则优先调用 `tools.json` 中声明的工具

如果 skill 需要更业务化的工具状态文案，也可以在 `tools.json` 的单个工具里补：

```json
{
  "name": "generate_document",
  "description": "根据已整理好的 doc_plan 生成文件产物，并返回可下载文件信息。",
  "status": {
    "label": "生成文档文件",
    "start": "正在根据已整理的文档结构生成可下载文件。",
    "success": "文档文件已生成，可直接下载。",
    "failure": "文档文件生成失败。"
  }
}
```

前端展示的 `tool-status` 会优先使用这里声明的业务文案，而不是再在前端按函数名做硬编码翻译。

不要继续在 Python 业务代码里为单个 skill 手写专用工具链路。

## 事故报告工作区
当前 `incident-report` 已调整为工作区专用能力。

- `incident-report` 在注册中心标记为 `skill_type=workspace_incident`。
- 聊天通道只允许 `skill_type=chat` 的 skill 进入规划与执行。
- 前端侧栏新增工作区切换：`对话` 与 `事故报告`。
- 事故报告会话与聊天会话分开存储、分开展示、分开状态管理。

事故报告后端接口：

- `GET /api/incident-report/schema`：获取事故报告工作区内建欢迎文案与表单定义（当前 `steps` 固定为空，由前端新表单逻辑驱动）。
- `GET /api/incident-report/sessions`：获取事故报告会话列表。
- `POST /api/incident-report/sessions`：创建事故报告会话，并自动生成可预览/可下载的 `V1` 初始历史版本。
- `GET /api/incident-report/sessions/{session_id}`：读取会话详情与表单快照。
- `PUT /api/incident-report/sessions/{session_id}`：实时保存表单答案。
- `POST /api/incident-report/sessions/{session_id}/body/quick-generate`：快填正文生成（返回可直接回填完整模式的字段）。
- `POST /api/incident-report/sessions/{session_id}/body/section-generate`：完整模式分段生成（支持 timeline_item 按条生成）。
- `POST /api/incident-report/sessions/{session_id}/preview`：预览附件（未传版本号时按当前草稿实时生成预览并返回可下载 DOCX；传版本号时预览对应历史版本）。
- `PATCH /api/incident-report/sessions/{session_id}/title`：修改标题。
- `DELETE /api/incident-report/sessions/{session_id}`：删除会话并清理附件/trace。

正文生成链路（涉及 LLM）：

1. 快填模式仅输入简述文本，调用 `body/quick-generate`。
2. 模型返回 JSON（事故简述、时间线、影响、根因、后续动作等），后端统一回填到完整模式字段。
3. 完整模式支持 `description/timeline/impact/root_cause/follow_up/timeline_item` 分段生成。
4. 每次正文生成都会记录 `trace_id` 并落入 `section_trace_ids`，前端可就近回放链路。

预览与导出链路：

1. 后端从当前表单快照构建 `report_data`。
2. 若正文/附录包含中文，使用当前请求模型将内容翻译为英文（保持日期/时间/ID 不变）。
3. 使用 `generate_incident_report` 脚本按参考模板生成 DOCX（清理模板示例正文，仅保留章节标题与用户填写内容；Impact 附表默认清空）。
4. 预览接口默认走草稿实时链路：直接返回本次预览 DOCX（base64）和 PDF/HTML 预览内容，前端下载与预览保持一致。
5. 新建会话仍会初始化 `V1` 历史版本，供需要时回看。

表单与模板映射约定：

- 手工首页前端标签可中文化，但后端 `report_data` 仍按英文模板字段写入，确保生成文档与参考模板一致。
- 所有日期字段统一归一为 `DD/MM/YYYY`；时间线时间支持 `HH:MM`、`YYYY-MM-DDTHH:MM`、`DD/MM/YYYY HH:MM`、`AM/PM` 等格式。
- 附录支持富文本（HTML + 内嵌图片 data URL），后端会解析为：
  - `appendix.notes`（纯文本）
  - `appendix.images`（图片列表）

## incident-report 正文生成机制（开发约定）
`incident-report` 工作区正文生成采用“显式 skill + 渐进披露”两阶段：

1. 生成请求进入 `services/chat/incident_reports.py` 后，先识别本次目标 section（`quick` / `description` / `timeline` / `timeline_item` / `impact` / `root_cause` / `follow_up`）。
2. 第一阶段做参考选择：
   - 输入：`incident-report/SKILL.md` + `references/body-sections/*.md` 的目录摘要 + 本次 section 上下文。
   - 实现：统一走 `services/skill/selector.py` 的场景模板 `select_for_workspace_reference`，内部再复用 `plan_skill_activation`（统一词法召回 + 模型重排范式）。
   - 输出：本次实际加载的 reference 文件列表（1~4 个）。
   - 异常时：回退到后端启发式选择，保证生成不中断。
3. 第二阶段做正文生成：
   - 仅注入第一阶段选中的 reference 正文（不再一次性注入全量参考）。
   - 快填模式生成并回填完整模式全部字段；完整模式仅更新当前 section。
   - 语言策略采用“两阶段模型判定”：
     第一步由模型先输出 `zh/en` 目标语言；
     第二步正文生成严格按该语言输出，并由模型二次校验，必要时自动重试一次。
   - 语言输出不做字符计数硬编码；系统级 `document-assistant` 提示会注入到正文生成 system prompt。
4. trace 中会记录本次 reference 选择结果，便于回放与排查。

扩展要求：
- 新增正文分段时，优先新增 `references/body-sections/*.md` 文档并在 `SKILL.md` 写清用途，不要在 Python 里新增硬编码映射。
- 保持 reference 文档“单一职责”：每个文件只描述一个分段或通用规则。
- 若要调整选择策略，优先修改统一规划器参数（候选上限、置信度阈值、显式项）而不是分叉新实现。
- 聊天工作区与 incident-report 工作区都必须通过 `services/skill/selector.py` 的场景模板进入选择流程：
- `select_for_chat_skills`
- `select_for_workspace_reference`
- 不要在业务模块里直接散落调用 planner。

## Tool Calling 与 Skill 上下文
当前主链路已升级为“分层规划 + 会话级 Agent 状态 + 执行器调度 + 生产级可靠性防护（阶段4）”。

### 主链路流程
1. 入口接收 `/api/chat/stream` 请求，生成/复用 `trace_id`，并做请求防护：
   - 租户级速率限制
   - 全局并发 + 租户并发队列控制
   - 请求级超时保护
2. 按 feature flag 决定是否启用规划器灰度：
   - 开启：走 `services/skill/planner.py`
   - 关闭：回退到“显式 skill + system skill”直连策略
3. 加载会话级 Agent 状态（Redis，按 `tenant_id + conversation_id` 隔离）：
   - `skills_state`
   - `planner_trace`
   - `tool_history`
4. 检索与上下文组装：
   - BM25 + embedding 混合召回
   - 候选融合后用 `reranker_model` 做 chunk 重排
   - 层级记忆（`skill_memory / episodic_memory / short_term_memory`）+ 正文片段打包
5. 流式调用 Ollama `/api/chat`，若有工具调用则进入执行器：
   - 执行器灰度开关（feature flag）
   - DAG 调度、并行读、重试补救、预算收束
6. 结束后落盘 trace 审计记录，可按 `trace_id` 回放。

### 安全策略
- 参数白名单：
  - 内置工具和声明式工具都在后端按 JSON Schema 校验参数，拒绝未声明字段和类型不匹配。
- 路径沙箱：
  - 仅允许访问 skill 根目录内路径，禁止越界读取。
- 脚本资源限制：
  - 运行目录固定在 skill 根目录。
  - 子进程限制 CPU 时间、内存、输出文件大小，并配置执行超时。
- 敏感操作策略：
  - 工具可声明 `security.requires_confirmation` / `risk_level`。
  - 后端按 `skill_sensitive_operation_policy` 执行 `allow / confirm / deny_high`。

### SLA 与隔离
- 请求级超时：`request_timeout_seconds`
- 队列等待超时：`request_queue_wait_timeout_seconds`
- 全局并发限制：`request_max_concurrent_global`
- 租户并发限制：`request_max_concurrent_per_tenant`
- 租户速率限制：`request_rate_limit_*`
- 会话缓存键按租户隔离：`conversation:{tenant_id}:{conversation_id}`

### 回放与审计
- 每次对话生成 trace 审计数据（规划结果、轮次、工具状态、错误、首包时延）。
- 新增回放接口：
  - `GET /api/system/agent-traces/{trace_id}?tenant_id=...`
- trace 会按 `conversation_id` 建立索引；删除历史会话时会同步清理该会话关联的 trace 回放数据。
- 可用于线上问题排查、回归比对和质量评估。

### 灰度发布
- 规划器灰度：
  - `feature_planner_enabled`
  - `feature_planner_rollout_ratio`
- 执行器灰度：
  - `feature_executor_enabled`
  - `feature_executor_rollout_ratio`
- 使用稳定哈希分桶，按 `tenant_id:conversation_id` 做一致性命中。

### 声明式参数规整约定
- `tools.json` 中 `serializer=json_file` 的参数会先规整再传给脚本。
- 支持模型传入：
  - JSON 对象
  - JSON 数组
  - JSON / YAML 字符串
- 若配置了 `text_normalizer`，会继续把 Markdown/纯文本草稿规整为结构化对象。
- 当前内置 `text_normalizer`：
  - `chaptered_document`（输出章节树结构）

### 关键实现位置
- 通用选择入口：`services/skill/selector.py`
- 规划核心：`services/skill/planner.py`
- 检索：`services/skill/context.py`
- 层级记忆：`services/skill/context_packer.py`
- 执行器：`services/agent/executor.py`
- 质量门控：`services/agent/quality_gate.py`
- 请求防护：`services/infra/request_guard.py`
- 审计追踪：`services/agent/trace_store.py`
- 流式编排：`services/chat/stream.py`

### 测试与评估体系
- 单测覆盖：
  - 规划器规则与灰度门控
  - 工具签名并发去重
  - 工具参数白名单与敏感策略
  - 请求限流/队列保护
- 集成覆盖：
  - 流式事件序列断言（`tool-status / attachment / done`）
  - trace 回放接口
- 基准集：
  - 当前在 `tests/skill_selection_cases.json` 提供小规模任务集（按当前 skills 数量设计，可扩展）。
- 回归门槛：
  - `test_skill_selection_precision_gate_from_benchmark_cases` 里强制 precision >= 0.85。
  - 阈值不达标时测试失败，即阻断发布流程。

## 生成文件与下载
当前 backend 已支持 skill 在工具调用中生成受控附件，也支持把用户上传文件统一落成会话附件：

- 文件落到 `backend/generated-attachments/`
- 该目录已加入 `.gitignore`
- 默认有效期 7 天
- 过期文件会在启动时、生成新文件时、下载文件前自动清理
- 当前统一下载接口为：
  - `GET /api/attachments/{attachment_id}/download`
- 同一 `conversation_id` 内，用户再次上传内容完全相同的文件时，会按文件内容哈希复用已有 `attachment_id`，避免重复存储。
- 删除历史会话时，后端会同步清理该会话关联的附件目录，避免遗留无主文件。

前端收到流式附件事件后，应把它展示成文件框或下载入口，而不是把文件路径写进模型正文。

## 提交改动前建议自查
每次改动后，建议至少确认下面几点：

1. 新代码放在了正确的职责目录下。
2. 没有把业务逻辑塞进 `routers`。
3. 没有重复写新的 Ollama/Redis 调用，而是复用了 `services/infra`。
4. 涉及会话或 skill 的改动时，检查对应模型是否需要同步调整。
5. 没有在 Pydantic 模型里引入 `AliasChoices`、`serialization_alias` 或 `by_alias=True`。
6. `pytest` 和 `compileall` 通过。

## 维护建议
如果后面继续迭代，建议遵循下面这条简单原则：

`优先收口重复逻辑，再考虑抽象；优先保持目录职责清楚，再考虑扩展能力。`

这样比较适合这个项目当前的规模，也能避免后期维护时出现“层很多，但没人记得该改哪里”的情况。
