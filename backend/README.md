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
当前主链路已升级为“分层规划 + 会话级 Agent 状态 + 执行器调度（Executor）”。

### 阶段2流程
一次 `/api/chat/stream` 请求会走以下固定流程：

1. 解析显式 skill（`selected_skill_ids` + 消息中的 `$skill-id`）。
2. 执行分层规划（`services/skill/planner.py`）并产出 `SkillPlanDecision`。
3. 读取/初始化会话级 Agent 状态（Redis）：
   - `skills_state`：按 skill 维护上下文状态
   - `planner_trace`：规划轨迹
   - `tool_history`：工具执行轨迹
4. 构建上游消息并调用 Ollama `/api/chat`（stream=true）。
5. 收到 `tool_calls` 后交给 `services/agent/executor.py` 调度执行。

### 执行器（Executor）职责
执行器接口：
- 输入：`ExecutionInput`（含 `SkillPlanDecision`、当前会话状态、工具调用批次、预算）
- 输出：`ExecutionResult` + `ExecutionStateDiff`

执行器能力：
- 轻量 DAG 调度：
  - 节点类型：`read / search / load / declare_tool / interaction`
  - 依赖约束：优先完成检索/读取，再执行载入与声明式生成工具
- 并行执行：
  - `read/search` 节点可并发执行（受 `agent_executor_max_parallel_reads` 限制）
- 预算控制：
  - token 预算（按模型 context_length 推导）
  - tool 调用预算
  - 时间预算
  - 超预算自动收束并停止后续工具调用
- 重试与补救：
  - 指数退避重试（`agent_executor_tool_retry_*`）
  - 失败后回退次优路径（例如 `search_skill_context` 自动移除 `source_path` 后重试）

### 模型上下文预算（按模型动态）
为避免每轮请求都探测模型上下文，后端使用两段式策略：

1. 启动预热：
   - `main.py` 启动时调用 `warmup_model_context_cache()`
   - 基于 `/api/tags` + `/api/show` 预热模型 `context_length` 缓存
2. 对话期读取：
   - 每轮仅从缓存读取 context_length（`get_model_context_length`）
   - 用 `agent_executor_prompt_budget_ratio` 计算本轮 prompt token 预算
   - 超预算则进入“收束模式”（关闭工具调用，要求模型基于已有信息直接完成回答）

### 关键实现位置
- 规划：`services/skill/planner.py`
- 执行器：`services/agent/executor.py`
- 模型上下文缓存：`services/infra/model_context.py`
- 流式编排：`services/chat/stream.py`

### 常用配置（`settings.py`）
- 规划：`skill_planner_*`
- 执行器：`agent_executor_max_parallel_reads`、`agent_executor_max_tool_calls`、`agent_executor_time_budget_seconds`
- 重试：`agent_executor_tool_retry_max_attempts`、`agent_executor_tool_retry_base_delay_seconds`
- token 预算：`agent_executor_prompt_budget_ratio`、`agent_executor_default_context_length`
- context 缓存：`agent_executor_model_context_cache_ttl_seconds`、`agent_executor_model_context_warmup_concurrency`

另外当前的声明式工具参数还有一条重要约定：

- `tools.json` 中声明为 `json_file` 的参数，后端会先做规整再交给脚本执行。
- 默认情况下，`json_file` 支持模型直接传：
  - JSON 对象
  - JSON 数组
  - JSON / YAML 字符串
- 如果某个参数在 `execution.arg_bindings` 里额外声明了 `text_normalizer`，后端还会按该策略继续把 Markdown 结构稿或纯文本草稿规整成结构化对象，再写入临时文件。
- 当前这种做法的目的，是把“文本到结构化入参”的容错能力做成声明式能力，而不是在 Python 业务代码里为单个 skill 或单个参数名写特判。

这样可以降低模型工具调用时对“严格 JSON 格式”的依赖，也能让不同 skill 在需要时复用同一套参数规整机制。

当前 `text_normalizer` 的使用约定也建议一并记住：

- `text_normalizer` 只在 `serializer=json_file` 且模型实际传入的是字符串时生效。
- 如果模型本来就传了对象或数组，后端会直接使用，不会再额外做文本规整。
- 当前已支持的值只有：
  - `chaptered_document`
    用于把 Markdown 标题结构稿或纯文本草稿规整成通用章节树结构，输出形态类似 `{"chapters": [...]}`，每个章节节点包含 `title`、`content`、`sections`。
- 新增新的 `text_normalizer` 时，优先抽象成可复用的通用结构转换，不要为了单个 skill 的私有格式继续堆专用分支。

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
