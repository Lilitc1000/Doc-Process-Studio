# Frontend 开发指南

本项目是基于 `Vue 3 + Vite + TypeScript + Pinia` 的单页聊天前端。

这份文档的目标不是介绍通用 Vue 用法，而是说明当前 `frontend` 目录里这套代码是如何组织的、后续应该按什么方式继续维护，避免把这次已经整理好的结构再慢慢堆回单文件大组件。

## 启动与校验

常用命令：

```bash
npm install
npm run dev
npm run build
npm run lint
npm run test
npx -y vue-tsc --noEmit
```

开发时建议至少保证下面 3 项通过：

```bash
npm run lint
npx -y vue-tsc --noEmit
npm run build
```

提交前建议再补一遍：

```bash
npm run test
```

说明：

- `npm run test`：Vitest 单元测试
- `npm run lint`：ESLint 规则检查
- `vue-tsc --noEmit`：TypeScript 类型检查
- `npm run build`：生产构建可用性检查

## 目录约定

当前前端目录按"组件 / 类型 / API / 工具 / 样式 / 组合式逻辑 / 状态管理"分层：

```text
frontend/
  src/
    api/            # 所有 HTTP 请求封装
    components/     # 页面组件与 UI 组件
    composables/    # 可复用状态逻辑
    stores/         # Pinia 全局状态管理
    styles/         # 全局样式与组件样式
    types/          # 跨组件共享类型
    utils/          # 纯函数、渲染工具、格式化工具
    env.d.ts        # Vue / CSS 模块声明
    main.ts         # 应用入口
    App.vue         # 根组件
  tests/            # Vitest 测试
```

后续新增代码时，优先遵守下面这几个边界：

- `components/` 放界面和交互，不要把大量 API 请求和复杂数据处理继续塞回组件。
- `api/` 只负责请求与响应映射，不负责页面状态。
- `types/` 只放跨文件共享的类型；组件内部临时类型不必硬抽。
- `utils/` 放无状态纯函数，避免依赖 Vue 生命周期。
- `composables/` 放"和页面状态有关，但已经重到不适合继续留在组件里"的逻辑。
- `stores/` 放跨组件共享的响应式状态，使用 Pinia 管理。
- `styles/components/` 放组件对应的样式文件，避免超长 `<style>` 继续堆在 `.vue` 里。

## 状态管理（Pinia）

项目使用 [Pinia](https://pinia.vuejs.org/) 作为全局状态管理方案，配合 [pinia-plugin-persistedstate](https://prazdevs.github.io/pinia-plugin-persistedstate/) 实现关键数据的 localStorage 持久化。

### 三个核心 Store

#### `useAppStore`（持久化）

文件：[stores/app.ts](/frontend/src/stores/app.ts)

存储用户偏好和配置缓存，**页面刷新后自动恢复**：

| 字段                    | 说明                                     | 持久化 |
| ----------------------- | ---------------------------------------- | ------ |
| `selectedModel`         | 当前选中的聊天模型                       | ✅     |
| `selectedRerankerModel` | 当前选中的重排序模型                     | ✅     |
| `activeWorkspaceId`     | 当前工作区（`chat` / `incident-report`） | ✅     |
| `availableModels`       | 可用模型列表缓存                         | ✅     |
| `processingModes`       | 可用 skill 列表缓存                      | ✅     |

持久化策略：所有字段均通过 `pinia-plugin-persistedstate` 写入 `localStorage`，页面打开时立即恢复上次选择，无需等待 API 返回即可渲染 UI。

#### `useChatStore`（不持久化）

文件：[stores/chat.ts](/frontend/src/stores/chat.ts)

聊天工作区的全部运行时状态，数据来源于后端 API 会话快照：

- 消息树状态（`messageNodes`、`rootChildIds`、`selectedRootChildId`、`selectedChildIdByParent`）
- 会话状态（`activeSessionId`、`conversationId`、`sessionSummaries`、`sessionViewKey`）
- 流式生成状态（`isLoading`、`activeGeneration`）
- 输入状态（`inputText`、`selectedFiles`、`selectedSkillIds`）
- 编辑状态（`editingMessageId`、`editingDraftText`、`editingDraftFiles`、`editingDraftSkillIds`）

核心计算属性（getters）：

- `displayedMessages`：当前可见消息列表
- `currentLeafMessageId`：当前叶子消息 ID
- `lastAssistantMessageId`：最后一条 assistant 消息 ID
- `activeStreamingAssistantMessage`：正在流式输出的 assistant 消息
- `latestLiveToolStatus`：最新实时工具状态
- `canConfirmEdit`：是否可确认编辑

核心方法（actions）：

- 消息树操作：`createMessageNode`、`findMessageById`、`updateMessageContent`、`appendMessageContent`、`switchMessageVersion` 等
- 会话快照：`hydrateSessionSnapshot`、`buildSessionSnapshotPayload`、`buildTitleSourceMessages`
- 状态重置：`resetChatState`、`resetConversationState`、`resetEditingState`
- 缓存预热：`prewarmVisibleConversationCache`

#### `useIncidentStore`（不持久化）

文件：[stores/incident.ts](/frontend/src/stores/incident.ts)

事故报告工作区的全部运行时状态：

- 会话状态（`activeIncidentSessionId`、`activeIncidentSession`、`incidentSessionSummaries`）
- 表单定义（`incidentSchema`）
- 生成状态（`isIncidentGenerating`、`generationState`、`generationTask`、`incidentErrorMessage`、`incidentGenerationTraceId`、`incidentGenerationProgress`）
- 附件预览状态（`incidentPreviewHtml`、`incidentPreviewPdfBase64`、`incidentPreviewLoading`、`incidentPreviewError`、`incidentPreviewVersion`）

计算属性：

- `incidentSidebarSessions`：侧栏会话列表（统一为 `ChatSessionSummary` 格式）

### Store 与 Composable 的关系

Store 负责**状态持有和基础操作**，Composable 负责**业务逻辑编排**：

```
ChatLayout.vue
  ├── useAppStore()          ← 用户偏好（持久化）
  ├── useChatStore()         ← 聊天状态
  ├── useIncidentStore()     ← 事故报告状态
  ├── useChatSessions()      ← 会话 CRUD（读写 chatStore/appStore）
  ├── useChatStreaming()     ← 流式生成（读写 chatStore）
  ├── useMessageActions()    ← 消息操作（读写 chatStore/appStore）
  ├── useCatalogLoader()     ← 目录加载（写入 appStore）
  └── useIncidentReportSessions() ← 事故报告会话（读写 incidentStore）
       ├── useIncidentForm()      ← 表单逻辑（读写 incidentStore）
       └── useIncidentGeneration() ← 生成逻辑（读写 incidentStore）
```

### 新增 Store 的原则

- 只有**跨组件共享**或**需要持久化**的状态才放入 Store。
- 组件局部 UI 状态（如弹窗开关、下拉展开）继续用 `ref()` 管理。
- 不要为了"统一"把所有状态都搬进 Store——局部状态留在组件里更清晰。
- 需要持久化的数据只限用户偏好和缓存，不要把运行时数据（如消息树、流式状态）持久化。

## 当前核心结构

### 1. 组件层

- [ChatLayout.vue](/frontend/src/components/ChatLayout.vue)
  页面主控组件，负责页面编排与事件串联。状态从 Pinia Store 读取，业务逻辑由 composables 提供。
- [ChatMessage.vue](/frontend/src/components/ChatMessage.vue)
  单条消息装配组件，负责拼装消息子组件与事件透传。
- [components/message/\*](/frontend/src/components/message)
  消息子组件集合：`MessageHeader`、`MessageFiles`、`MessageToolbar`、`MessageToolTimeline`、`MessageLiveToolStatus`。
- [ChatInput.vue](/frontend/src/components/ChatInput.vue)
  底部输入区、文件选择、`$skill` 多选输入。
- [ChatSidebar.vue](/frontend/src/components/ChatSidebar.vue)
  左侧历史会话与模型选择区域（包含"聊天模型"和"重排序模型"两个下拉）。
- [IncidentReportWorkspace.vue](/frontend/src/components/IncidentReportWorkspace.vue)
  事故报告工作区页面，包含手工首页 / AI 正文 / 附录分区、快填与完整模式、附件预览与版本下载。

### 2. 状态管理层

- [stores/app.ts](/frontend/src/stores/app.ts)
  用户偏好与配置缓存，使用 `pinia-plugin-persistedstate` 持久化到 localStorage。
- [stores/chat.ts](/frontend/src/stores/chat.ts)
  聊天工作区状态：消息树、会话、流式生成、输入、编辑。包含消息树操作、快照构建/恢复、缓存预热等核心逻辑。
- [stores/incident.ts](/frontend/src/stores/incident.ts)
  事故报告工作区状态：会话、表单定义、生成状态。

### 3. 组合式逻辑

- [useChatSessions.ts](/frontend/src/composables/useChatSessions.ts)
  历史会话加载、保存、重命名、删除、会话切换后的状态恢复。通过 `useChatStore` 和 `useAppStore` 管理状态。
- [useIncidentReportSessions.ts](/frontend/src/composables/useIncidentReportSessions.ts)
  事故报告会话加载、创建、重命名、删除。组合 `useIncidentForm` 和 `useIncidentGeneration`，对外提供统一接口。
- [useIncidentForm.ts](/frontend/src/composables/useIncidentForm.ts)
  事故报告表单 schema 加载、答案更新、debounce 快照保存。通过 `useIncidentStore` 管理状态。
- [useIncidentGeneration.ts](/frontend/src/composables/useIncidentGeneration.ts)
  事故报告正文生成、附件生成、停止生成、附件预览加载、版本下载。通过 `useIncidentStore` 管理状态。
- [useChatStreaming.ts](/frontend/src/composables/useChatStreaming.ts)
  流式生成、停止生成、流式内容回填。通过 `useChatStore` 管理状态。
- [useMessageActions.ts](/frontend/src/composables/useMessageActions.ts)
  发送、编辑、重生、附件下载、复制等消息操作聚合。通过 `useChatStore` 和 `useAppStore` 管理状态。
- [useTraceModal.ts](/frontend/src/composables/useTraceModal.ts)
  链路回放弹窗的打开/关闭/重试/复制逻辑，含 404 短轮询重试。
- [useCopyToast.ts](/frontend/src/composables/useCopyToast.ts)
  顶部复制成功提示。
- [useCatalogLoader.ts](/frontend/src/composables/useCatalogLoader.ts)
  模型与 skill 列表加载，负责 catalog 拉取与 system skill 过滤。通过 `useAppStore` 管理状态。
- [useSkillMentionSelector.ts](/frontend/src/composables/useSkillMentionSelector.ts)
  统一的 `$skill` 触发、候选过滤、键盘导航、token 删除逻辑，供输入框与编辑态复用。
- [composables/message/\*](/frontend/src/composables/message)
  消息局部逻辑：`useMessageRender`（懒渲染/缓存）、`useMessageEdit`（编辑态自适应输入）。

### 4. 请求层

- [api/client.ts](/frontend/src/api/client.ts)
  `axios` 实例。
- [api/catalog.ts](/frontend/src/api/catalog.ts)
  模型列表、skill 列表请求。
- [api/sessions.ts](/frontend/src/api/sessions.ts)
  历史会话接口。
- [api/chat.ts](/frontend/src/api/chat.ts)
  聊天流式请求封装（透传 `model` 与 `reranker_model`）。
- [api/incident-report.ts](/frontend/src/api/incident-report.ts)
  事故报告工作区接口封装（schema/sessions/body-generate/preview/title/delete）。
- [api/attachments.ts](/frontend/src/api/attachments.ts)
  附件下载接口封装（统一使用 `attachment` 语义）。
- [api/trace.ts](/frontend/src/api/trace.ts)
  链路回放查询接口封装（`/api/system/agent-traces/{trace_id}`）。

### 5. 类型层

- [types/chat.ts](/frontend/src/types/chat.ts)
  消息节点、聊天请求、流式事件等类型。
- [types/incident-report.ts](/frontend/src/types/incident-report.ts)
  事故报告表单、会话、生成响应等类型。
- [types/session.ts](/frontend/src/types/session.ts)
  历史会话与快照结构。
- [types/trace.ts](/frontend/src/types/trace.ts)
  链路回放数据结构。
- [types/skill.ts](/frontend/src/types/skill.ts)
  skill 选项与 catalog 结构。

### 6. 工具层

- [utils/render-markdown.ts](/frontend/src/utils/render-markdown.ts)
  Markdown 渲染、高亮语言按需加载、消息渲染缓存、预热逻辑。
- [utils/chat-stream.ts](/frontend/src/utils/chat-stream.ts)
  SSE 数据解析。
- [utils/session-groups.ts](/frontend/src/utils/session-groups.ts)
  历史会话分组。
- [utils/catalog.ts](/frontend/src/utils/catalog.ts)
  模型和 skill 响应归一化。
- [utils/file.ts](/frontend/src/utils/file.ts)
  文件大小格式化、文件类型视觉配置查找。
- [utils/file-type-visuals.ts](/frontend/src/utils/file-type-visuals.ts)
  文件类型视觉映射数据。
- [utils/ids.ts](/frontend/src/utils/ids.ts)
  前端会话 ID / 消息 ID 生成。
- [utils/message-tree.ts](/frontend/src/utils/message-tree.ts)
  消息树纯函数（可见路径、版本切换、路径回溯、附件 ID 收集）。

## TypeScript 配置说明

当前有 4 个 TS 配置文件，这属于正常拆分：

- [tsconfig.base.json](/frontend/tsconfig.base.json)
  公共编译选项。
- [tsconfig.json](/frontend/tsconfig.json)
  前端应用默认配置，编辑器主要吃这个。
- [tsconfig.app.json](/frontend/tsconfig.app.json)
  应用代码入口别名，和当前项目结构保持一致。
- [tsconfig.node.json](/frontend/tsconfig.node.json)
  给 `vite.config.mts`、`vitest.config.ts` 这类 Node 侧配置文件使用。

如果后续出现"命令行没报错，但编辑器局部红线"的情况，优先检查：

1. 新文件是否落在 `tsconfig.json` / `tsconfig.app.json` 的 `include` 范围内。
2. 是否缺少 `.d.ts` 模块声明。
3. 是否把 Node 配置文件误放进了应用配置里。

## 字段命名约定

前后端统一使用 `snake_case` 作为字段命名格式：

- `types/` 中的所有接口字段均为 `snake_case`（如 `trace_id`、`parent_id`、`request_skill_ids`）。
- `api/` 层直接透传后端返回的 `snake_case` 字段，不做任何 camelCase 转换。
- 不要在类型定义中引入 camelCase 别名或兼容字段（如 `traceId`、`parentId`）。
- 不要在 API 层写 `normalize` 函数做字段映射。

如果后端新增了字段，前端直接用 `snake_case` 对应即可，不需要额外转换。

## 样式约定

当前样式已经从大部分组件里拆出，放在：

- [base.css](/frontend/src/styles/base.css)
- [chat-layout.css](/frontend/src/styles/components/chat-layout.css)
- [chat-message.css](/frontend/src/styles/components/chat-message.css)
- [chat-input.css](/frontend/src/styles/components/chat-input.css)
- [chat-sidebar.css](/frontend/src/styles/components/chat-sidebar.css)

后续样式维护建议：

- 全局变量、页面底色、基础 reset 放 `base.css`
- 组件视觉样式放对应 `styles/components/*.css`
- 不要把几百行样式重新堆回单个 `.vue`
- 如果只是非常局部、非常短的小样式，再考虑留在组件里

## Markdown 渲染与性能优化

当前消息渲染已经做了几层优化，后续维护时不要轻易破坏这条链路：

### 1. 纯文本绕过 Markdown

普通用户纯文本消息不会默认触发 `markdown-it`。

### 2. 懒渲染

需要 Markdown 的消息只有在接近视口时，才真正执行 Markdown 渲染。

### 3. 高亮按需加载

`highlight.js` 使用的是 `core + 常用语言按需注册`，没有整包直接灌进主包。

### 4. 会话级共享缓存

消息渲染缓存以：

```text
cacheScopeId + messageId + role + contentHash
```

作为 key，不同会话不会乱串。

### 5. sessionStorage 短期复用

缓存会同步到 `sessionStorage`，页面刷新后可短期复用。

### 6. 历史会话预热

切换历史会话后，会后台预热当前可见消息的缓存。

### 7. 版本切换预热

当前可见路径上的消息，会额外预热相邻版本，提升上一版 / 下一版切换命中率。

如果后续还要继续优化这一块，优先顺序建议是：

1. 保持现有缓存链路稳定
2. 只扩大"预热范围"而不是推翻渲染结构
3. 真到超长会话明显卡顿时，再考虑消息列表虚拟滚动

## 消息展示约定

下面这几条属于当前聊天 UI 的稳定交互规则，后续改样式或拆组件时尽量保持不变：

### 1. 实时工具状态显示在当前 AI 消息内

- assistant 消息在流式生成期间，实时 `tool-status` 显示在"当前这条 AI 回复"的气泡内。
- 回答完成或主动停止后，实时状态不再单独悬浮显示，而是收敛到该消息自己的处理过程区。
- 不要再把实时工具状态做回页面底部全局提示条，否则用户在长消息生成时需要来回移动视线。

### 2. AI 附件默认显示在正文之后

- assistant 消息如果同时有正文和附件，先显示正文，再显示附件文件框。
- 这样可以避免附件把正文顶到下方，也能减少"模型正文里还在解释附件，但文件框已经跑到最前面"的视觉割裂感。
- 如果后续新增新的附件展示样式，优先保持这个顺序。

### 3. 附件图标按常见文件类型细分显示

- 当前附件图标不是单一通用图标，而是优先按常见扩展名识别，再回退到 MIME 类型。
- 例如 `md`、`vue`、`ts`、`js`、`py`、`json`、`yaml`、`pdf`、`docx` 会显示各自更具体的 badge。
- 这套规则统一收敛在 `src/utils/file-type-visuals.ts`（映射数据）和 `src/utils/file.ts`（查找逻辑），后续如果要补新的文件类型，优先改 `file-type-visuals.ts`，不要在组件里各自写判断。

### 4. 链路回放入口

- assistant 消息在收到后端 `trace` 事件后会绑定 `trace_id`，并在该条消息流式结束后显示"查看链路"按钮。
- 点击后会打开回放弹窗，调用 `api/trace.ts` 拉取详情；后端刚写入时若短暂 404，前端会做短轮询重试。
- 会话快照中统一持久化 `trace_id`，切换历史会话后仍可查看对应链路。

## Skill 选择输入约定

聊天输入框仍支持 `$` 触发 skill 选择，但只展示 `skill_type=chat` 的条目。

- 输入框和消息编辑态输入 `$` 时弹出候选列表。
- 支持方向键、`Enter`、`Tab`、鼠标点击选择。
- 一条用户消息可绑定多个 skill（`requestSkillIds`）。
- `document-assistant` 是 system skill，不在候选中显示。
- `incident-report` 属于 `workspace_incident` 类型，不会出现在聊天候选与隐式选择中。

## 事故报告工作区

事故报告走独立页面流程：

1. 侧栏切换到"事故报告"后显示欢迎向导。
2. 点击"开始"会创建事故报告会话，标题格式：`事故报告-YYYY/MM/DD HH:MM`。
3. 页面分区为：`手工首页 / AI 正文 / 附录 / 预览附件`。
4. 手工首页标签使用 `中文（English）`，字段键保持模板英文映射。
5. 自定义日期时间控件支持三种模式：`仅日期 / 仅时间 / 日期时间`，并带独立展开/收起图标。
6. AI 正文支持双模式：
   快填模式：单输入框 + 一键生成（支持“正在生成中”弹窗与停止）。
   完整模式：按段生成（事故简述、时间线、影响、根因、后续动作、时间线单条），同样显示“正在生成中”弹窗与停止。
7. 时间线使用结构化控件编辑：时间线条目为时间输入；受影响日期摘要为日期 + 从/至时间。
8. 完整模式中，时间线区域只保留“每条时间线的单独生成按钮”，不再保留时间线卡片右上角总生成按钮。
9. 每条时间线中，时间控件与后续输入/按钮按垂直居中对齐。
10. AI 回填后会同步更新时间线条目时间与内容（支持 `HH:MM`、单数字小时、AM/PM 等时间格式）。
11. 附录使用富文本输入框，可输入文本并插入图片（不再使用独立附录图片区）。
12. 预览区仅保留“预览附件”，不再暴露“生成附件（新增版本）”入口。
13. 打开预览弹窗后，表单编辑会实时刷新预览内容（草稿预览链路）。
14. 预览附件弹窗优先显示 PDF 风格预览（后端返回 `pdf_base64`），下载按钮始终下载“当前预览文档”。

### incident-report skill 渐进披露对接约定

- 前端在事故报告工作区触发正文生成时，始终视为显式调用 `incident-report` skill。
- 生成请求仍通过 `api/incident-report.ts` 的 `quick-generate` / `section-generate` 接口发送，关键参数为 `section_id` 与可选 `timeline_index`。
- 后端会基于 `section_id` 做“参考选择 -> 分段生成”两阶段处理，且参考选择与对话工作区共用统一选择服务（`services/skill/selector.py`，按场景模板分别走 `select_for_workspace_reference` / `select_for_chat_skills`，内部调用 planner），前端无需硬编码参考文档映射。
- 新增 section 时，前端只需补 `section_id` 触发入口；参考文档选择规则由 skill 文档与后端选择器负责。

## 新功能开发建议

### 新增接口

如果新增后端接口：

1. 先在 `src/api/` 增加请求函数
2. 再在 `src/types/` 补共享响应类型
3. 最后在组件或 composable 中消费

不要在组件里直接散写 `axios.get(...)` / `fetch(...)`。

### 新增共享状态逻辑

如果某段逻辑已经同时满足下面两条，就优先抽 composable：

- 超过一个组件会用
- 或者虽然只有一个组件在用，但状态和副作用已经明显让组件变重

如果状态需要跨组件共享或需要持久化，优先放入 Pinia Store。

### 新增工具函数

如果是纯格式化、纯映射、纯解析逻辑，优先放 `src/utils/`，不要放进组件。

## 测试约定

当前测试使用：

- `Vitest`
- `@vue/test-utils`
- `happy-dom`

测试目录在 [tests](/frontend/tests)。

测试环境通过 [tests/setup.ts](/frontend/tests/setup.ts) 自动初始化 Pinia，确保组件挂载时 Store 可用。

目前已经覆盖的方向包括：

- catalog 映射
- 历史会话分组
- 聊天流事件解析
- 附件上传/下载与 `attachment` 流事件
- `ChatSidebar` 基础交互
- 事故报告工作区（欢迎页/建会话/表单生成）流程

后续如果继续补测试，优先补这些高价值点：

1. 历史会话切换
2. 消息版本切换
3. 编辑后重新发送
4. Markdown 缓存 / 预热逻辑
5. 流式输出回填
6. Pinia Store 状态持久化与恢复

## 维护时尽量避免的事

- 不要把 API 请求重新塞回 `.vue`
- 不要把共享类型重新写回组件内部
- 不要把长样式块再塞回 SFC
- 不要在消息渲染链路里随意去掉缓存、懒渲染和按需加载
- 不要在类型或 API 层重新引入 camelCase 兼容代码（normalize 函数、别名双写字段）
- 不要把组件局部 UI 状态（如弹窗开关、下拉展开）搬进 Store
- 不要把运行时数据（消息树、流式状态）持久化到 localStorage

## 当前建议的维护顺序

如果以后继续整理前端，建议优先级如下：

1. 保持 `ChatLayout.vue` 不再回涨
2. 新逻辑优先落到 `api / utils / composables / stores`
3. 补测试而不是堆更多手工回归
4. 真出现长会话性能瓶颈时，再考虑虚拟滚动

这份 README 应该和当前代码实现保持同步。如果后续目录结构或渲染链路有明显变动，请一起更新这份文档。
