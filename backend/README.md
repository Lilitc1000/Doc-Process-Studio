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
后端改动完成后，至少执行下面两步：

```bash
cd backend
ENV=dev /workspace/backend/.venv/bin/python -m pytest
ENV=dev /workspace/backend/.venv/bin/python -m compileall /workspace/backend/src/doc_process_studio
```

第一条用于回归行为，第二条用于快速发现导入错误和语法错误。

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
- 流式接口测试建议断言事件顺序和关键事件类型（如 `interaction`、`tool-status`、`attachment`、`done`），不要只断言最终文本。
- skill 相关测试优先走真实 `tools.json` 声明链路，避免在测试里硬编码一套与生产不同的执行分支。

### 新增 skill 时的最小测试清单
1. 通过 `test_skill_registry_smoke.py`（无需特判即可被发现并解析配置）。
2. 在 `tests/skills/<skill_id>/` 下至少增加 1 条工具链契约测试（输入 -> 工具调用 -> 输出结构）。
3. 如果该 skill 启用交互式步骤（`interaction.json`），补 1 条“触发交互 + 提交答案后完成工具调用”的链路测试。

### 推荐本地命令
```bash
cd backend
ENV=dev /workspace/backend/.venv/bin/python -m pytest -q
ENV=dev /workspace/backend/.venv/bin/python -m compileall /workspace/backend/src/doc_process_studio
```

如果本地环境会因为 `pyc` 写入权限导致报错，可临时加：

```bash
PYTHONDONTWRITEBYTECODE=1 ENV=dev /workspace/backend/.venv/bin/python -m pytest -q
```

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
负责与外部依赖交互：

- Ollama HTTP 调用
- Redis 读写

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
这个项目当前更适合“轻分层 + 清晰职责”，不建议一上来做：

- 很重的 DDD 分层
- 每个 service 再套 interface
- 为了抽象而抽象出多层空壳

如果一个能力只在一个地方用到，而且逻辑不复杂，直接放在当前职责文件里通常更合适。

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

## 交互式 Skill
新增了一套通用交互式采集链路，可供任意 skill 按声明启用，不再是单一 skill 特化逻辑。

- skill 可在 `agents/interaction.json` 声明分步采集（single/multi/text）。
- 交互向导默认是“可调用能力”而不是入口强制流程：模型可通过 `start_skill_interaction` 工具在信息不足时主动进入向导；信息充足时可直接调用生成工具。
- 交互向导当前只支持“单一目标 skill”模式；当本轮同时激活多个 skill 时，后端会拒绝 `start_skill_interaction` 并提示用户缩小到单 skill。
- 若某个会话已处于进行中的向导状态，后端会优先恢复当前步骤，避免状态丢失。
- 后端流式接口会按步骤返回 `interaction` 事件，步骤完成后继续执行声明式工具并返回 `tool-status`、`attachment`、`done`。
- 交互状态默认走 Redis，会话维度缓存；测试时可用内存替身避免环境依赖。

推荐在改动交互链路后至少做一次完整回归：  
`发起请求 -> 收到步骤 -> 提交全部步骤 -> 返回附件 -> 验证附件可下载`。

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
- 规划：`services/skill/planner.py`
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
  - 状态迁移兼容（旧快照字段可读）
  - 工具签名并发去重
  - 工具参数白名单与敏感策略
  - 请求限流/队列保护
- 集成覆盖：
  - 流式事件序列断言（`tool-status / interaction / attachment / done`）
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
5. `pytest` 和 `compileall` 通过。

## 维护建议
如果后面继续迭代，建议遵循下面这条简单原则：

`优先收口重复逻辑，再考虑抽象；优先保持目录职责清楚，再考虑扩展能力。`

这样比较适合这个项目当前的规模，也能避免后期维护时出现“层很多，但没人记得该改哪里”的情况。
