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

## API 依赖

| API                         | 方法   | 用途                        |
| --------------------------- | ------ | --------------------------- |
| `/chat-sessions`            | GET    | 加载会话列表                |
| `/chat-sessions/{id}`       | GET    | 加载会话详情                |
| `/chat-sessions/{id}`       | PUT    | 保存会话快照                |
| `/chat-sessions/{id}/title` | PATCH  | 修改会话标题                |
| `/chat-sessions/{id}`       | DELETE | 删除会话                    |
| `/chat/stream`              | POST   | 发送消息并接收 SSE 流式回复 |
| `/models`                   | GET    | 获取可用模型列表            |
| `/skills`                   | GET    | 获取 Skill 列表             |

## 核心交互流程

1. 页面加载时获取会话列表和模型/Skill 列表
2. 用户在输入框输入消息，可选选择 Skill 和上传文件
3. 点击发送后，通过 SSE 流式接收 AI 回复
4. 回复过程中显示工具调用状态，完成后可查看 trace
5. 消息支持版本切换、编辑、重新生成、复制、下载

## 组件交互约定

- `ChatView.vue` 是页面主组件，通过 `DefaultLayout` 的 AppHeader 显示标题
- 页面标题可点击，点击后保持在对话页面
- 侧边栏复用业务公共组件 `SessionSidebar`，会话数据通过 `useChatSessions` 管理
- 顶部提示复用业务公共组件 `FloatingToast`，展示由 `useCopyToast` 控制
- 流式消息通过 `useChatStreaming` composable 处理
- 聊天域交互按钮统一复用 `BaseButton`：`ChatInput` 发送/清空附件、`MessageToolbar` 消息操作、`SessionSidebar` 会话操作、`TraceReplayModal` 弹窗操作、`AppHeader` 页头按钮均走基础按钮组件
- 文件上传触发器统一复用 `BaseFileUpload`：`ChatInput`（主输入上传）和 `MessageToolbar`（编辑态上传）共用同一上传控件

## 开发注意

- SSE 事件类型定义在 `types/chat/chat.ts` 的 `ChatStreamEvent` 中
- 消息树结构支持分支版本，通过 `message-tree.ts` 工具函数管理
- 文件上传先调用 `/chat/stream` 的 multipart 字段，返回 attachmentId
- 页面样式文件放在 `styles/` 目录下，通过 `<style scoped src="./styles/xxx.css">` 引入
