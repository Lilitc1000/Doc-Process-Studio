# Stores 开发指南

Pinia 全局状态管理目录，按业务域组织。Store 负责**状态持有和基础操作**，Composable 负责**业务逻辑编排**。

## 目录结构

```text
frontend/src/stores/
├── app.ts              # 用户偏好（持久化）
├── auth.ts             # 认证状态（部分持久化）
├── chat.ts             # 聊天工作区状态（不持久化）
├── incident-report.ts  # 事故报告工作区状态（不持久化）
└── knowledge-base.ts   # 知识库工作区状态（不持久化）
```

## Store 说明

| Store                    | 职责                         | 持久化               | 关键字段                                                                       |
| ------------------------ | ---------------------------- | -------------------- | ------------------------------------------------------------------------------ |
| `useAppStore`            | 用户偏好和配置缓存           | ✅                   | `selectedModel`、`selectedRerankerModel`、`availableModels`、`processingModes` |
| `useAuthStore`           | 认证状态管理                 | 部分（refreshToken） | `accessToken`、`refreshToken`、`userInfo`                                      |
| `useChatStore`           | 聊天工作区全部运行时状态     | ❌                   | 消息树、会话状态、流式生成状态、输入状态                                       |
| `useIncidentReportStore` | 事故报告工作区全部运行时状态 | ❌                   | 会话状态、生成状态                                                             |
| `useKnowledgeBaseStore`  | 知识库工作区全部运行时状态   | ❌                   | 项目列表、当前项目、树形结构、更新状态                                         |

## 持久化策略

- `appStore`：全部字段持久化到 localStorage，页面刷新后自动恢复
- `authStore`：仅 `refreshToken` 持久化，`accessToken` 和 `userInfo` 存内存
- `chatStore` / `incidentReportStore` / `knowledgeBaseStore`：不持久化，避免运行时数据污染 localStorage

## 开发注意

- 不要把组件局部 UI 状态（如弹窗开关、下拉展开）搬进 Store
- 不要把运行时数据（消息树、流式状态）持久化到 localStorage
- 各 Store 的详细字段和方法说明见对应业务域开发文档
- 单元测试中每个 `beforeEach` 必须调用 `setActivePinia(createPinia())`
