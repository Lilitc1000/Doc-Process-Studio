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
- 聊天流式编排
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

- `agents/openai.yml` 或 `agents/openai.yaml`
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

## Tool Calling 与 Skill 上下文
当前 skill 主链已经改成“流式 tool calling + Redis 会话缓存”，不再使用旧版“先 planner 再一次性补 chunk”的思路。

一次 `/api/chat/stream` 请求的大致流程如下：

1. 读取当前会话绑定的 `skill_id`
2. 注入该 skill 的 `default_prompt`
3. 从 Redis 读取当前会话已经加载过的 skill chunk 状态
4. 使用 `stream=true + tools` 调远端 Ollama
5. 如果模型在流中返回 `tool_calls`
6. 后端执行对应工具，例如：
   - `list_skill_directory`
   - `read_skill_file`
   - `search_skill_context`
   - `read_skill_context`
   - skill 在 `tools.json` 中声明的脚本型工具，例如 `generate_document`
7. 工具结果以 `assistant/tool` 消息形式回填，再继续下一轮流式请求
8. 直到模型不再继续调工具，才自然结束这次回答

也就是说：

- `SKILL.md` 和 `references/` 不会在每轮请求时被一次性全塞进提示词
- 模型会按需读取 skill 片段
- 模型也可以按需读取 skill 内的具体文件，如 `SKILL.md`、`references/*`、`scripts/*`
- 已读取的 chunk 会缓存在 Redis 会话状态中
- 重复的相同工具调用会被后端自动去重，避免模型反复读取同一文件或同一批 chunk
- 如果某一轮工具调用没有带来任何新信息，后端会自动收束到“直接回答”，而不是继续空转
- 生成类 skill 可以通过 `tools.json` 声明的脚本型工具产出可下载附件

因此在维护时要注意：

- 如果要改 skill 渐进式读取逻辑，优先看 `services/skill/tool_loop.py`
- 如果要改 skill 上下文压缩与注入策略，优先看 `services/skill/runtime.py` 和 `services/skill/context_packer.py`
- 如果要改流式编排，优先看 `services/chat/stream.py`
- 不要在路由层直接操作这些缓存和工具细节

## 生成文件与下载
当前 backend 已支持 skill 在工具调用中生成受控附件，也支持把用户上传文件统一落成会话附件：

- 文件落到 `backend/generated-attachments/`
- 该目录已加入 `.gitignore`
- 默认有效期 7 天
- 过期文件会在启动时、生成新文件时、下载文件前自动清理
- 当前统一下载接口为：
  - `GET /api/attachments/{attachment_id}/download`
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
