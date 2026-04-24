# Frontend 开发指南

本项目是基于 `Vue 3 + Vite + TypeScript + Pinia + Vue Router` 的单页聊天前端。

## 启动与校验

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

## 目录结构

前端采用混合架构模式，按业务域组织代码，组件按职责分层。

```text
frontend/src/
├── main.ts                     # 应用入口
├── App.vue                     # 根组件（<router-view />）
│
├── router/                     # 路由配置
│   └── index.ts
│
├── layouts/                    # 布局组件
│   ├── DefaultLayout.vue       # 默认布局：AppHeader + 内容区 + 路由页面切换动画
│   └── components/             # 布局专属组件
│       └── AppHeader.vue
│
├── views/                      # 页面级组件（按业务域，对应路由）
│   ├── home/
│   │   ├── HomeView.vue
│   │   └── styles/
│   │       └── home-page.css
│   ├── chat/
│   │   ├── ChatView.vue
│   │   ├── components/         # 页面级私有组件（仅当前页面用）
│   │   │   ├── ChatInput.vue
│   │   │   ├── ChatMessage.vue
│   │   │   └── message/        # 消息子组件
│   │   ├── composables/        # 页面级私有逻辑（仅当前页面用）
│   │   │   ├── useChatSessions.ts
│   │   │   ├── useChatStreaming.ts
│   │   │   ├── useMessageActions.ts
│   │   │   ├── useMessageEdit.ts
│   │   │   ├── useMessageRender.ts
│   │   │   └── useSkillMentionSelector.ts
│   │   └── styles/             # 聊天域样式
│   │       ├── chat-page.css
│   │       ├── chat-input.css
│   │       ├── chat-message.css
│   │       └── chat-sidebar.css # SessionSidebar 复用该样式
│   ├── incident-report/
│   │   ├── IncidentReportView.vue
│   │   ├── components/         # 页面级私有组件
│   │   │   └── IncidentReportWorkspace.vue
│   │   ├── composables/        # 页面级私有逻辑
│   │   │   ├── useIncidentReportForm.ts
│   │   │   ├── useIncidentReportGeneration.ts
│   │   │   └── useIncidentReportSessions.ts
│   │   └── styles/             # 事故报告域样式
│   │       ├── incident-report-page.css
│   │       └── incident-report-workspace.css
│   └── settings/
│       ├── SettingsView.vue
│       └── styles/
│           └── settings-page.css
│
├── components/                 # 全局公共组件
│   ├── base/                   # 原子组件：纯 UI，无业务，到处复用
│   │   ├── BaseButton.vue      # 按钮（primary/secondary/danger/ghost）
│   │   ├── BaseDropdown.vue    # 下拉选择器
│   │   ├── BaseModal.vue       # 模态对话框
│   │   ├── BaseInput.vue       # 文本输入框
│   │   ├── BaseTextarea.vue    # 多行输入框
│   │   ├── BaseFileUpload.vue  # 文件上传
│   │   └── BaseDateTimePicker.vue # 日期/时间选择器
│   └── business/               # 业务组件：跨页面复用，带业务语义
│       ├── SessionSidebar.vue
│       ├── FloatingToast.vue
│       └── TraceReplayModal.vue
│
├── composables/                # 全局组合式函数
│   └── business/               # 跨页面业务逻辑复用
│       ├── useCatalogLoader.ts
│       ├── useCopyToast.ts
│       └── useTraceModal.ts
│
├── api/                        # HTTP 请求封装（按业务域）
│   ├── request.ts              # Axios 实例（含 camelCase ↔ snake_case 自动转换拦截器）
│   ├── catalog.ts              # 模型列表、skill 列表
│   ├── chat-stream.ts          # 聊天流式请求
│   ├── chat-sessions.ts        # 聊天会话接口
│   ├── chat-attachments.ts     # 附件下载接口
│   ├── incident-report.ts      # 事故报告接口
│   └── trace.ts                # 链路回放接口
│
├── stores/                     # Pinia 全局状态（按业务域）
│   ├── app.ts                  # 用户偏好（持久化）
│   ├── chat.ts                 # 聊天工作区状态
│   └── incident-report.ts      # 事故报告工作区状态
│
├── types/                      # 跨组件共享类型
│   ├── chat/
│   │   ├── chat.ts             # 消息节点、聊天请求、流式事件
│   │   └── session.ts          # 历史会话与快照
│   ├── incident-report/
│   │   └── incident-report.ts  # 事故报告类型
│   └── common/
│       ├── skill.ts            # Skill 选项与 catalog
│       └── trace.ts            # 链路回放数据
│
├── utils/                      # 纯工具函数
│   ├── chat/
│   │   ├── chat-stream.ts      # SSE 缓冲区解析
│   │   ├── message-tree.ts     # 消息树纯函数
│   │   └── session-groups.ts   # 会话按日期分组
│   ├── incident-report/
│   │   ├── date-normalization.ts # 日期/时间归一化
│   │   └── constants.ts        # 事故报告常量与归一化函数
│   └── common/
│       ├── catalog.ts          # 目录归一化
│       ├── file.ts             # 文件大小格式化
│       ├── file-type-visuals.ts # 文件类型视觉映射
│       ├── ids.ts              # ID 生成
│       └── render-markdown.ts  # Markdown 渲染引擎
│
├── styles/                     # 全局样式
│   └── base.css                # 全局变量、reset
│
└── assets/                     # 静态资源
```

测试目录结构：

```text
frontend/tests/
├── unit/                       # Vitest：纯函数、composables、store
│   ├── chat/
│   ├── incident-report/
│   └── common/
├── integration/                # Vitest + @vue/test-utils：组件渲染 + API mock
└── e2e/                        # Playwright：真实浏览器端到端测试
    ├── home.spec.ts            # 首页导航
    ├── chat.spec.ts            # 对话页面（含发送消息场景）
    ├── incident-report.spec.ts # 事故报告页面（含创建报告场景）
    ├── settings.spec.ts        # 设置页面
    └── navigation.spec.ts      # 全局导航
```

## 业务域开发文档

每个业务域有独立的前端和后端开发文档：

| 业务域         | 前端文档                                   | 后端文档                                                        |
| -------------- | ------------------------------------------ | --------------------------------------------------------------- |
| Chat           | `src/views/chat/DEVELOPMENT.md`            | `backend/src/doc_process_studio/chat/DEVELOPMENT.md`            |
| IncidentReport | `src/views/incident-report/DEVELOPMENT.md` | `backend/src/doc_process_studio/incident_report/DEVELOPMENT.md` |
| Home           | `src/views/home/DEVELOPMENT.md`            | —                                                               |
| Settings       | `src/views/settings/DEVELOPMENT.md`        | —                                                               |

## 组件分层规则

| 层级         | 目录                     | 职责                                        | 约束                                                           |
| ------------ | ------------------------ | ------------------------------------------- | -------------------------------------------------------------- |
| 布局         | `layouts/`               | 控制页面骨架，通过 `<router-view>` 注入内容 | 禁止写业务逻辑                                                 |
| 页面         | `views/`                 | 直接对应路由，负责数据获取和页面级状态      | 可组合多个 components                                          |
| 页面私有组件 | `views/xxx/components/`  | 仅当前页面用                                | 禁止被其他页面导入                                             |
| 页面私有逻辑 | `views/xxx/composables/` | 仅当前页面用                                | 禁止被其他页面导入                                             |
| 原子组件     | `components/base/`       | 纯 UI，无业务，到处复用                     | 禁止依赖 API，props/emit 通信                                  |
| 业务组件     | `components/business/`   | 跨页面复用，带业务语义                      | 可依赖特定 API 类型，但禁止直接调用 API（通过 props 传入数据） |
| 全局逻辑     | `composables/`           | 逻辑复用                                    | base 级纯逻辑，business 级可调用 API                           |

## 命名规范

| 使用场景                              | 推荐风格   | 示例                            |
| ------------------------------------- | ---------- | ------------------------------- |
| JS 变量 / 函数                        | camelCase  | `incidentReportStore`           |
| Vue props / data / computed / methods | camelCase  | `activeIncidentReportSessionId` |
| Vue 组件定义（JS 中）                 | PascalCase | `IncidentReportWorkspace.vue`   |
| 模板中的组件名（SFC）                 | kebab-case | `<incident-report-workspace />` |
| DOM 模板中的组件名                    | kebab-case | `<incident-report-workspace />` |
| 模板中的 prop 绑定                    | kebab-case | `:is-generating="..."`          |
| 自定义事件名（模板监听）              | kebab-case | `@quick-generate-body="..."`    |
| CSS 类名 / ID                         | kebab-case | `.incident-report-workspace`    |
| 文件名                                | kebab-case | `incident-report-page.css`      |
| API 路径                              | kebab-case | `/incident-report/sessions`     |

## 样式规范

### 样式归属原则

| 组件类型                              | 样式位置                              | 说明                           |
| ------------------------------------- | ------------------------------------- | ------------------------------ |
| 公共基础组件 (`components/base/`)     | 内联在 `.vue` 的 `<style scoped>` 中  | 组件自包含，外部无需关心样式   |
| 业务公共组件 (`components/business/`) | 优先内联；复杂样式可同目录 `src` 引入 | 保证可复用、可维护             |
| 布局组件 (`layouts/`)                 | 内联在 `.vue` 的 `<style scoped>` 中  | 同上                           |
| 页面级组件 (`views/xxx/`)             | 放在 `views/xxx/styles/` 目录下       | 业务域样式集中管理             |
| 全局样式                              | `styles/base.css`                     | 仅放 CSS 变量、reset、全局字体 |

### 样式文件引用方式

页面级组件通过 `<style scoped src="./styles/xxx.css">` 引用同域样式文件：

```html
<!-- ChatView.vue -->
<style scoped src="./styles/chat-page.css"></style>

<!-- ChatInput.vue（子组件） -->
<style scoped src="../styles/chat-input.css"></style>
```

### 设计 Token

全局 CSS 变量定义在 `styles/base.css` 中，所有组件统一使用：

| 变量                     | 用途     | 示例值    |
| ------------------------ | -------- | --------- |
| `--color-primary`        | 主色     | `#4f46e5` |
| `--color-primary-hover`  | 主色悬停 | `#4338ca` |
| `--color-text-primary`   | 主文本   | `#1f2937` |
| `--color-text-secondary` | 辅助文本 | `#6b7280` |
| `--color-text-tertiary`  | 占位文本 | `#9ca3af` |
| `--color-border`         | 边框     | `#d1d5db` |
| `--color-border-hover`   | 边框悬停 | `#9ca3af` |
| `--color-bg-hover`       | 背景悬停 | `#f3f4f6` |
| `--color-bg-disabled`    | 禁用背景 | `#f9fafb` |

### 新增样式时注意

1. **不要在 `styles/` 下新建组件样式文件**，业务域样式放在 `views/xxx/styles/`
2. **公共组件样式优先内联**；当样式体量较大时可拆到同目录并通过 `src` 引入
3. **使用 CSS 变量而非硬编码颜色**，保持风格统一
4. **不要引入第三方 CSS 框架**，所有样式手写
5. **scoped 样式优先**，避免全局污染
6. **按钮、输入框、下拉框等基础 UI 元素必须使用 `components/base/` 中的组件**，不要在业务组件中手写原生 `<button>`/`<input>`/`<select>` 再自定义样式

## 公共基础组件

### BaseButton

统一按钮样式，支持 `primary`/`secondary`/`danger`/`ghost` 四种变体和 `sm`/`md`/`lg` 三种尺寸。

跨业务域复用已落地到：`IncidentReportWorkspace`、`ChatInput`、`MessageToolbar`、`SessionSidebar`、`TraceReplayModal`、`AppHeader`。迁移时建议保留原业务 class（用于样式差异和 E2E 定位），只替换为 `BaseButton` 承载基础交互与主题。

```vue
<BaseButton variant="primary" size="md" @click="handleSave">
  保存
</BaseButton>
```

### BaseDropdown

统一下拉选择器，支持 `v-model` 双向绑定。视觉对齐事故报告表单字段（40px 高度、12px 圆角、统一 focus ring），当 `modelValue` 不在 `options` 中时显示 placeholder 样式。

```vue
<BaseDropdown
  v-model="selectedModel"
  :options="modelOptions"
  label-id="model-label"
/>
```

`options` 格式：`{ label: string; value: string }[]`

### BaseModal

统一模态对话框，支持 `header`/`default`/`footer` 三个插槽。

```vue
<BaseModal :visible="showDialog" title="确认删除" @close="showDialog = false">
  <p>确定要删除这条记录吗？</p>
  <template #footer>
    <BaseButton variant="secondary" @click="showDialog = false">取消</BaseButton>
    <BaseButton variant="danger" @click="confirmDelete">删除</BaseButton>
  </template>
</BaseModal>
```

### BaseInput / BaseTextarea

统一输入框，支持 `label`、`required`、`invalid`、`errorMessage`。
其中 `BaseTextarea` 额外暴露 `getTextareaEl()`，便于在聊天输入等场景进行光标定位与自适应高度控制。

```vue
<BaseInput
  v-model="name"
  label="名称"
  :required="true"
  :invalid="!name"
  error-message="名称不能为空"
/>
```

### BaseFileUpload

统一文件上传触发器，隐藏原生 `<input type="file">`，通过 slot 自定义触发 UI。

已在 `ChatInput`、`MessageToolbar`、`IncidentReportWorkspace`（附录图片插入）中复用。

```vue
<BaseFileUpload accept="image/*" :multiple="true" @select="onFilesSelected">
  <BaseButton variant="ghost" size="sm">上传图片</BaseButton>
</BaseFileUpload>
```

### BaseDateTimePicker

日期/时间选择器，支持 `datetime`/`date`/`time` 三种模式，通过 `v-model` 绑定 ISO 格式字符串。

```vue
<BaseDateTimePicker
  v-model="incidentDate"
  mode="datetime"
  placeholder="请选择日期和时间"
/>
```

## 路由配置

使用 Vue Router 4 管理页面导航：

| 路由路径           | 组件                     | 说明           |
| ------------------ | ------------------------ | -------------- |
| `/`                | `HomeView.vue`           | 主页，入口卡片 |
| `/chat`            | `ChatView.vue`           | 对话页面       |
| `/incident-report` | `IncidentReportView.vue` | 事故报告页面   |
| `/settings`        | `SettingsView.vue`       | 设置页面       |

所有页面使用 `DefaultLayout` 布局，包含 `AppHeader` 和 `<router-view>`。

### 布局与页面交互约定

`DefaultLayout` 提供全局 `AppHeader`（首页按钮 + 页面标题），页面组件**不要**再内嵌自己的 `AppHeader`。

如果页面需要自定义 header 行为（如标题可点击、点击后执行特定逻辑），通过 `defineExpose` 暴露接口给 `DefaultLayout`：

```typescript
// IncidentReportView.vue 中暴露接口
const isTitleClickable = computed(
  () => !incidentReportStore.isIncidentReportGenerating,
);

defineExpose({
  onHeaderTitleClick, // 标题点击回调
  onGoHome, // 首页按钮回调
  isTitleClickable, // 标题是否可点击
});
```

`DefaultLayout` 会通过 `router-view` 的 `ref` 检测子组件是否暴露了这些接口，有则调用，无则使用默认行为。

## 状态管理（Pinia）

### `useAppStore`（持久化）

文件：[stores/app.ts](/frontend/src/stores/app.ts)

存储用户偏好和配置缓存，页面刷新后自动恢复：

| 字段                    | 说明                 | 持久化 |
| ----------------------- | -------------------- | ------ |
| `selectedModel`         | 当前选中的聊天模型   | ✅     |
| `selectedRerankerModel` | 当前选中的重排序模型 | ✅     |
| `availableModels`       | 可用模型列表缓存     | ✅     |
| `processingModes`       | 可用 skill 列表缓存  | ✅     |

### `useChatStore`（不持久化）

文件：[stores/chat.ts](/frontend/src/stores/chat.ts)

聊天工作区的全部运行时状态：

- 消息树状态（`messageNodes`、`rootChildIds`、`selectedRootChildId`）
- 会话状态（`activeSessionId`、`conversationId`、`sessionSummaries`）
- 流式生成状态（`isLoading`、`activeGeneration`）
- 输入状态（`inputText`、`selectedFiles`、`selectedSkillIds`）
- 编辑状态（`editingMessageId`、`editingDraftText`）

核心计算属性：`displayedMessages`、`currentLeafMessageId`、`latestLiveToolStatus`、`canConfirmEdit`

核心方法：`createMessageNode`、`switchMessageVersion`、`hydrateSessionSnapshot`、`prewarmVisibleConversationCache`

### `useIncidentReportStore`（不持久化）

文件：[stores/incident-report.ts](/frontend/src/stores/incident-report.ts)

事故报告工作区的全部运行时状态：

- 会话状态（`activeIncidentReportSessionId`、`activeIncidentReportSession`、`incidentReportSessionSummaries`）
- 表单定义（`incidentReportSchema`）
- 生成状态（`isIncidentReportGenerating`、`generationState`、`generationTask`）
- 附件预览状态（`incidentReportPreviewHtml`、`incidentReportPreviewPdfBase64`、`incidentReportPreviewLoading`）

### Store 与 Composable 的关系

Store 负责**状态持有和基础操作**，Composable 负责**业务逻辑编排**：

```
ChatView.vue
  ├── useChatStore()          ← 聊天状态
  ├── useChatSessions()       ← 会话 CRUD（读写 chatStore/appStore）
  ├── useChatStreaming()      ← 流式生成（读写 chatStore）
  ├── useMessageActions()     ← 消息操作（读写 chatStore/appStore）
  └── useCatalogLoader()      ← 目录加载（写入 appStore）

IncidentReportView.vue
  ├── useIncidentReportStore()      ← 事故报告状态
  ├── useIncidentReportSessions()   ← 事故报告会话
  │     ├── useIncidentReportForm()      ← 表单逻辑
  │     └── useIncidentReportGeneration() ← 生成逻辑
  └── useCatalogLoader()            ← 目录加载
```

## 请求层

`api/` 目录按业务域组织，每个文件负责一组 API 请求：

| 文件                  | 职责                                                                            |
| --------------------- | ------------------------------------------------------------------------------- |
| `request.ts`          | Axios 实例（baseURL: `/api`），含请求/响应拦截器自动转换 camelCase ↔ snake_case |
| `catalog.ts`          | 模型列表、skill 列表                                                            |
| `chat-stream.ts`      | 聊天流式请求（使用原生 fetch，支持 SSE ReadableStream）                         |
| `chat-sessions.ts`    | 聊天会话 CRUD                                                                   |
| `chat-attachments.ts` | 附件下载                                                                        |
| `incident-report.ts`  | 事故报告工作区全部接口                                                          |
| `trace.ts`            | 链路回放查询                                                                    |

`api/` 只负责请求与响应映射，不负责页面状态。

### HTTP 拦截器（camelCase ↔ snake_case 自动转换）

`request.ts` 中已配置 Axios 拦截器，使用 `humps` 库实现自动转换：

- **请求拦截器**：将 `config.data` 和 `config.params` 中的 camelCase 字段自动转换为 snake_case
- **响应拦截器**：将 `response.data` 中的 snake_case 字段自动转换为 camelCase

前端代码统一使用 camelCase，后端接口统一使用 snake_case，无需在业务代码中手动转换。

## 字段命名约定

前端代码统一使用 **camelCase**：

- `types/` 中的所有接口字段使用 camelCase
- `api/` 层通过拦截器自动转换，业务代码无需关心 snake_case
- `stores/` 中的状态字段使用 camelCase
- `composables/` 和组件中的变量/函数使用 camelCase

后端接口使用 snake_case，由 `request.ts` 中的拦截器自动处理转换。

## Markdown 渲染与性能优化

当前消息渲染已做多层优化，后续维护时不要轻易破坏：

1. **纯文本绕过 Markdown**：普通用户纯文本消息不触发 markdown-it
2. **懒渲染**：需要 Markdown 的消息只有在接近视口时才真正渲染
3. **高亮按需加载**：highlight.js 使用 core + 常用语言按需注册
4. **会话级共享缓存**：缓存以 `cacheScopeId + messageId + role + contentHash` 为 key
5. **sessionStorage 短期复用**：缓存同步到 sessionStorage，页面刷新后可短期复用
6. **历史会话预热**：切换历史会话后，后台预热当前可见消息的缓存

## 消息展示约定

1. 实时工具状态显示在当前 AI 消息内（不要做回页面底部全局提示条）
2. AI 附件默认显示在正文之后
3. 附件图标按常见文件类型细分显示（规则收敛在 `utils/common/file-type-visuals.ts`）
4. 链路回放入口：assistant 消息绑定 `traceId` 后显示"查看链路"按钮

## Skill 选择输入约定

聊天输入框支持 `$` 触发 skill 选择，只展示 `skillType=chat` 的条目：

- 输入 `$` 时弹出候选列表
- 支持方向键、Enter、Tab、鼠标点击选择
- 一条用户消息可绑定多个 skill
- `document-assistant` 是 system skill，不在候选中显示
- `incident-report` 属于 `workspace_incident` 类型，不会出现在聊天候选

## 事故报告工作区

1. 主页点击"事故报告"卡片进入事故报告页面
2. 侧栏显示历史会话列表
3. 页面分区为：手工首页 / AI 正文 / 附录 / 预览附件
4. AI 正文支持双模式：快填模式（单输入框 + 一键生成）和完整模式（按段生成）
5. 时间线使用结构化控件编辑
6. 附录使用富文本输入框，可输入文本并插入图片
7. 预览区仅保留"预览附件"
8. 打开预览弹窗后，表单编辑会实时刷新预览内容

## 新功能开发建议

### 新增接口

1. 先在 `src/api/` 增加请求函数
2. 再在 `src/types/` 补共享响应类型
3. 最后在组件或 composable 中消费

不要在组件里直接散写 `axios.get(...)` / `fetch(...)`。

### 新增共享状态逻辑

如果某段逻辑已经同时满足下面两条，就优先抽 composable：

- 超过一个组件会用
- 或者虽然只有一个组件在用，但状态和副作用已经明显让组件变重

如果状态需要跨组件共享或需要持久化，优先放入 Pinia Store。

### 新增 UI 元素

1. **按钮** → 使用 `BaseButton`
2. **输入框** → 使用 `BaseInput`
3. **多行输入** → 使用 `BaseTextarea`
4. **下拉选择** → 使用 `BaseDropdown`
5. **文件上传** → 使用 `BaseFileUpload`
6. **日期/时间选择** → 使用 `BaseDateTimePicker`
7. **弹窗/对话框** → 使用 `BaseModal`

如果现有基础组件不满足需求，先在 `components/base/` 中扩展或新增，不要在业务组件中直接写原生 HTML 元素再自定义样式。

### 新增工具函数

如果是纯格式化、纯映射、纯解析逻辑，优先放 `src/utils/`，不要放进组件。

## 测试约定

当前测试使用 Vitest + @vue/test-utils + happy-dom + Playwright。

### 单元测试与集成测试

- **单元测试**：纯函数输入输出，composables 不 mock API（测逻辑分支），utils 全覆盖
- **集成测试**：组件用 @vue/test-utils mount，API 用 vi.mock，不测真实后端

### E2E 测试

使用 Playwright 在真实浏览器中测试用户常用场景：

```bash
# 先启动后端（E2E 测试需要后端运行）
cd backend && env ENV=dev uv run uvicorn doc_process_studio.main:app --host 0.0.0.0 --port 8000

# 再运行 E2E 测试
npm run test:e2e       # 运行 E2E 测试
npm run test:e2e:ui    # 带 UI 界面运行
```

E2E 测试覆盖：

- 首页加载与导航卡片跳转
- 对话页面：渲染、发送消息、AI 回复、会话管理
- 事故报告页面：渲染、创建报告、填写表单、AI 生成正文
- 设置页面：模型选择交互
- 全局导航（header 首页按钮、浏览器前进后退）

E2E 测试通过 `playwright.config.ts` 配置，会自动启动 Vite 开发服务器。**对话和事故报告的 E2E 测试需要后端运行**，纯 UI 测试则不需要。

### 新增 E2E 测试注意

1. 测试文件放在 `tests/e2e/` 目录，文件名以 `.spec.ts` 结尾
2. 使用 `page.goto()` 导航，用 CSS 选择器定位元素
3. 需要后端的测试用 `test.describe` 标注，并在测试前确认后端可用
4. 使用 `expect().toBeVisible()` / `toHaveText()` / `toHaveURL()` 等断言
5. 涉及 AI 生成的测试需要较长超时时间（建议 30s+）

## 维护时尽量避免的事

- 不要把 API 请求重新塞回 `.vue`
- 不要把共享类型重新写回组件内部
- 不要把长样式块再塞回 SFC（业务域样式放 `views/xxx/styles/`）
- 不要在消息渲染链路里随意去掉缓存、懒渲染和按需加载
- 不要在类型或 API 层重新引入 camelCase 兼容代码
- 不要把组件局部 UI 状态（如弹窗开关、下拉展开）搬进 Store
- 不要把运行时数据（消息树、流式状态）持久化到 localStorage
- 不要在 `views/xxx/components/` 中的组件被其他页面导入
- 不要在业务组件中直接写原生 `<button>`/`<input>`/`<select>` 再自定义样式，应使用 `components/base/` 中的基础组件
