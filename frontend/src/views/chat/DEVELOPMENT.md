# Chat 页面开发指南

## 目录结构

```text
frontend/src/views/chat/
├── ChatView.vue                 # 对话页面主组件
├── components/
│   ├── ChatInput.vue            # 输入区域（文本框 + 文件上传 + Skill 选择）
│   ├── ChatMessage.vue          # 单条消息渲染
│   └── message/                 # 消息子组件（header / toolbar / files / timeline）
├── composables/
│   ├── useChatSessions.ts       # 会话列表 CRUD
│   ├── useChatStreaming.ts      # SSE 流式发送与事件处理
│   ├── useMessageActions.ts     # 消息操作（复制、下载、编辑、重新生成）
│   ├── useMessageEdit.ts        # 消息编辑状态
│   ├── useMessageRender.ts      # 消息渲染辅助
│   └── useSkillMentionSelector.ts # Skill @选择器
└── styles/
    ├── chat-page.css
    ├── chat-input.css
    └── chat-message.css

frontend/src/components/business/
├── SessionSidebar.vue           # 跨域复用会话侧边栏（Chat/Incident 共用）
├── FloatingToast.vue            # 跨域复用顶部提示浮层
└── TraceReplayModal.vue         # Trace 回放弹窗
```

## Store 状态说明

`useChatStore`（不持久化）：

- 消息树状态（`messageNodes`、`rootChildIds`、`selectedRootChildId`）
- 会话状态（`activeSessionId`、`conversationId`、`sessionSummaries`）
- 流式生成状态（`isLoading`、`activeGeneration`）
- 输入状态（`inputText`、`selectedFiles`、`selectedSkillIds`）
- 编辑状态（`editingMessageId`、`editingDraftText`）

核心计算属性：`displayedMessages`、`currentLeafMessageId`、`latestLiveToolStatus`、`canConfirmEdit`

核心方法：`createMessageNode`、`switchMessageVersion`、`hydrateSessionSnapshot`、`prewarmVisibleConversationCache`

### Store 与 Composable 的关系

```
ChatView.vue
  ├── useChatStore()          ← 聊天状态
  ├── useChatSessions()       ← 会话 CRUD（读写 chatStore/appStore）
  ├── useChatStreaming()      ← 流式生成（读写 chatStore）
  ├── useMessageActions()     ← 消息操作（读写 chatStore/appStore）
  └── useCatalogLoader()      ← 目录加载（写入 appStore）
```

## API 依赖

| API | 方法 | 用途 |
|-----|------|------|
| `/chat-sessions` | GET | 加载会话列表 |
| `/chat-sessions/{id}` | GET | 加载会话详情 |
| `/chat-sessions/{id}` | PUT | 保存会话快照 |
| `/chat-sessions/{id}/title` | PATCH | 修改会话标题 |
| `/chat-sessions/{id}` | DELETE | 删除会话 |
| `/chat/stream` | POST | 发送消息并接收 SSE 流式回复 |
| `/models` | GET | 获取可用模型列表 |
| `/skills` | GET | 获取 Skill 列表 |

## 核心交互流程

1. 页面加载时获取会话列表和模型/Skill 列表
2. 用户在输入框输入消息，可选选择 Skill 和上传文件
3. 点击发送后，通过 SSE 流式接收 AI 回复
4. 回复过程中显示工具调用状态，完成后可查看 trace
5. 消息支持版本切换、编辑、重新生成、复制、下载

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

## Markdown 渲染与性能优化

当前消息渲染已做多层优化，后续维护时不要轻易破坏：

1. **纯文本绕过 Markdown**：普通用户纯文本消息不触发 markdown-it
2. **懒渲染**：需要 Markdown 的消息只有在接近视口时才真正渲染
3. **高亮按需加载**：highlight.js 使用 core + 常用语言按需注册
4. **会话级共享缓存**：缓存以 `cacheScopeId + messageId + role + contentHash` 为 key
5. **sessionStorage 短期复用**：缓存同步到 sessionStorage，页面刷新后可短期复用
6. **历史会话预热**：切换历史会话后，后台预热当前可见消息的缓存

## 组件交互约定

- `ChatView.vue` 是页面主组件，通过 `DefaultLayout` 的 AppHeader 显示标题
- 页面标题可点击，点击后保持在对话页面
- 侧边栏复用业务公共组件 `SessionSidebar`，会话数据通过 `useChatSessions` 管理
- 顶部提示复用业务公共组件 `FloatingToast`，展示由 `useCopyToast` 控制
- 流式消息通过 `useChatStreaming` composable 处理
- 聊天域交互按钮统一复用 `BaseButton`
- 文件上传触发器统一复用 `BaseFileUpload`

## 开发注意

- SSE 事件类型定义在 `types/chat/chat.ts` 的 `ChatStreamEvent` 中
- 消息树结构支持分支版本，通过 `message-tree.ts` 工具函数管理
- 文件上传先调用 `/chat/stream` 的 multipart 字段，返回 attachmentId
- 页面样式文件放在 `styles/` 目录下，通过 `<style scoped src="./styles/xxx.css">` 引入
