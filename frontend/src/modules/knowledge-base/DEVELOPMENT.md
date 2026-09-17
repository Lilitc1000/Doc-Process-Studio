# Knowledge Base 页面开发指南

## 数据来源 = RAGFlow dataset

本模块的知识库**唯一真相源是 RAGFlow**，后端不再使用本地 PostgreSQL 表。

- 应用中的「知识库项目」对应 RAGFlow 的 **dataset**，因此项目 `id` **就是 dataset id**
  （32 位十六进制，例如 `f05e5a4aadac11f1b9211b18c23af0c8`）。
- **文件夹为只读**：RAGFlow 这版不支持在 dataset 内新建 / 重命名 / 删除文件夹
  （接口仅允许 `GET /tree`、`PUT /rename project`、`DELETE project`，没有 `POST/DELETE` 文件夹）。
  前端**只渲染**文件夹（可展开）与文档，**不得提供**任何文件夹写操作入口。
- 树结构：`GET /projects/{id}/tree` 在无文件夹时返回扁平文档列表，有文件夹时返回层级树，
  前端无需区分，直接渲染即可。

## 目录结构

```text
frontend/src/modules/knowledge-base/
├── types/knowledge-base.ts        # 类型定义（KBProject / KBDocument / KBTreeNode* / ...）
├── api/knowledge-base.ts          # API 封装（list / create / rename / delete / tree / upload / deleteDoc）
├── store/knowledge-base.ts        # Pinia store
├── index.ts                       # 模块桶文件（统一导出公共 API 与类型）
├── views/
│   ├── KnowledgeBaseListView.vue    # 知识库项目列表页
│   ├── KnowledgeBaseDetailView.vue  # 知识库项目详情页（文档树 + 上传 + 删除文档）
│   ├── KbTreeNode.vue               # 树形节点组件（递归渲染文件夹/文档）
│   └── styles/
└── DEVELOPMENT.md
```

## 类型定义

所有类型定义集中在 `src/modules/knowledge-base/types/knowledge-base.ts`，API 层和组件通过 import 引用：

| 类型                    | 说明                                                                                                                                         |
| ----------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `KBProject`             | 知识库项目（id = dataset id、name、description、documentCount、createdAt、updatedAt）                                                        |
| `KBDocument`            | 文档（id、projectId、fileName、fileType、fileSize、chunkCount、isIndexed、parseStatus、uploadedAt）                                          |
| `KBTreeNode`            | 树形节点联合类型（`KBTreeNodeFolder \| KBTreeNodeDocument`）                                                                                 |
| `KBTreeNodeFolder`      | 文件夹节点（type、id、name、children；**无 path / sortOrder**）                                                                              |
| `KBTreeNodeDocument`    | 文档节点（type、id、name、fileType、fileSize、chunkCount、isIndexed、parseStatus、uploadedAt；**无 version / isLatest / folderId**）         |
| `KBTreeResponse`        | 树形结构响应（projectId + projectName + tree 数组）                                                                                          |
| `KBProjectSimple`       | 简要项目信息（id + name，供 Skill `$` 选择器使用）                                                                                           |
| `ParseStatus`           | 文档解析状态联合类型：`'UNSTART' \| 'RUNNING' \| 'DONE' \| 'FAIL'`                                                                           |
| `KBDocumentParseDetail` | 文档解析详情（documentId / fileName / parseStatus / isIndexed / progress / chunkCount / tokenCount / processDuration / message / updatedAt） |

> 已移除：`KBFolder`（文件夹写模型）、`KBUpdateStatus`、`KBProject.isUpdating` /
> `lastUpdatedAt` / `folderCount`、`KBDocument.version` / `isLatest` / `folderId`、
> 以及 `KBTreeNodeFolder.path` / `sortOrder`。

### 解析状态字段

`KBDocument` 与 `KBTreeNodeDocument` 均新增了 `parseStatus: ParseStatus`，用于文档树行内的
简洁状态徽章。**不要**在树行里展示冗长的解析进度文案——徽章只显示 2~3 个汉字：

- `UNSTART` → 未索引
- `RUNNING` → 解析中
- `FAIL` → 解析失败
- `DONE` → 解析成功（绿色，常驻显示，便于确认已就绪）

点击徽章会在详情页弹出「解析详情」弹窗（`teleport` 到 `body`），展示完整字段与「重新解析」按钮。

### 实时状态更新（前端轮询）

RAGFlow 解析是**异步**的（上传 / 重新解析后文档会经历 `UNSTART → RUNNING → DONE/FAIL`），
而后端没有推送通道（无 WebSocket / SSE）。因此前端通过**智能轮询**让徽章实时反映状态变化：

- store 新增 `isPolling` 与 `startStatusPolling(projectId)` / `stopStatusPolling()`。
- 触发点：详情页 `onMounted`、`onFileSelect`（上传后）、`onReparse`（重新解析后）均调用
  `startStatusPolling`；若当前已有轮询则幂等跳过。
- `startStatusPolling` 先拉一次树：若所有文档已是终态（`DONE`/`FAIL`）则立即返回、不轮询；
  否则每 **2s** 拉一次 `getKBTree`，直到全部文档到终态才自动 `stopStatusPolling`。
- 轮询期间若「解析详情」弹窗正打开且对应文档仍在解析，会顺带刷新 `fetchParseDetail`，使弹窗进度同步。
- `onUnmounted` 与 `reset()` 都会调用 `stopStatusPolling()`，避免离开页面后继续请求。

### 解析详情字段说明

后端 `GET /knowledge-base/documents/{id}/parse-detail` 返回 snake_case，经 axios 拦截器
`humps.camelizeKeys` 自动转为 camelCase 后形如：

```ts
interface KBDocumentParseDetail {
  documentId: string;
  fileName: string;
  parseStatus: ParseStatus;
  isIndexed: boolean;
  progress: number; // 0~1 的进度比例
  chunkCount: number;
  tokenCount: number;
  processDuration: number | null; // 解析耗时（秒），可能为 null
  message: string; // RAGFlow 的 progress_msg，可能包含 `[ERROR]` 原因（可能很长）
  updatedAt: string | null;
}
```

## API 封装

`apiClient` 的 `baseURL` 为 `/api`，故调用路径为相对 `/api` 的剩余部分：

| 函数                     | 方法 & 路径                                           | 说明                             |
| ------------------------ | ----------------------------------------------------- | -------------------------------- |
| `listKBProjects`         | `GET /knowledge-base/projects`                        | 项目列表                         |
| `createKBProject`        | `POST /knowledge-base/projects`                       | 新建项目                         |
| `renameKBProject`        | `PUT /knowledge-base/projects/{id}/rename`            | 重命名项目                       |
| `deleteKBProject`        | `DELETE /knowledge-base/projects/{id}`                | 删除项目                         |
| `getKBTree`              | `GET /knowledge-base/projects/{id}/tree`              | 文档树                           |
| `uploadKBDocument`       | `POST /knowledge-base/projects/{id}/documents/upload` | 上传文档                         |
| `deleteKBDocument`       | `DELETE /knowledge-base/documents/{id}`               | 删除文档                         |
| `listKBProjectsSimple`   | `GET /knowledge-base/projects-simple`                 | Skill `$` 选择器用的简要项目列表 |
| `getDocumentParseDetail` | `GET /knowledge-base/documents/{id}/parse-detail`     | 获取文档解析详情                 |
| `reparseDocument`        | `POST /knowledge-base/documents/{id}/parse`           | 触发文档重新解析（后端返回 202） |

> `reparseDocument` 触发 RAGFlow 后台异步重新解析，前端**不**等待解析完成，仅发起请求；
> 请求结束后通常应再调用 `getDocumentParseDetail` 刷新弹窗内的进度。

## Store 状态说明

`useKnowledgeBaseStore`（不持久化）：

- `projects`：项目列表
- `currentProject`：当前查看的项目
- `currentTree`：当前项目的文档树
- `isLoading`：列表加载状态
- `parseDetail`：当前查看的文档解析详情（`KBDocumentParseDetail | null`）
- `isReparsing`：是否正在触发重新解析（请求进行中为 `true`）
- `isPolling`：是否正在轮询解析状态（上传 / 重新解析后启动，全部到终态即停止）

核心方法：`fetchProjects`、`createProject`、`renameProject`、`removeProject`、`fetchTree`、`reset`、
`fetchParseDetail(documentId)`、`reparseDocument(documentId)`、
`startStatusPolling(projectId)`（智能轮询：见上文「实时状态更新」）、`stopStatusPolling()`。

## 组件规范

- 所有按钮使用 `BaseButton`，文件上传使用 `BaseFileUpload`（KbTreeNode / DetailView 不再使用 BaseInput）。
- 样式通过 `<style scoped src="./styles/xxx.css">` 引入，不内联在 `.vue` 文件中。
- 类型从 `src/modules/knowledge-base/types/knowledge-base.ts` 导入，不在组件内重复定义。

## 解析状态徽章与详情弹窗

- `KbTreeNode.vue` 在文档行渲染一个可点击徽章，展示 `未索引` / `解析中` / `解析失败` / `解析成功` 之一：
  - `DONE` → `解析成功`（绿色，`kb-tree-badge--done`），**常驻显示**，便于确认文档已就绪；
  - `FAIL` → `解析失败`（红色，`kb-tree-badge--fail`）；
  - `UNSTART` / `RUNNING` → `未索引` / `解析中`（中性，`kb-tree-badge--pending`）.
    徽章点击通过 `@click.stop="$emit('showParseDetail', node.id)"` 向上冒泡，递归子节点需透传
    `@show-parse-detail`。
- `KnowledgeBaseDetailView.vue` 监听 `@show-parse-detail`，调用 `store.fetchParseDetail(docId)`
  后弹出「解析详情」弹窗（`teleport` 到 `body`，沿用 `kb-dialog-overlay` / `kb-dialog` 样式）。
  弹窗内展示：文件名、状态（UNSTART 未索引 / RUNNING 解析中 / DONE 解析成功 / FAIL 解析失败）、
  进度（`progress * 100` 取整 + `%`）、分块数、Token 数、耗时（`processDuration ?? 0` 取 1 位小数 + `s`）、
  以及 `message`（用 `<pre class="kb-parse-msg">` 可滚动展示，保留原始空白与换行，含可能很长的 `[ERROR]` 文本）。
- 弹窗提供「重新解析」按钮（`<base-button>`，`:disabled="store.isReparsing"`，`@click="onReparse"`）
  与「关闭」按钮。

## Skill `$` 提及（对话）

对话输入框通过 `useSkillMentionSelector` 支持 `@`/`$` 提及知识库。

- 提及 id 形如 `kb:<datasetId>`（即项目 `id`，32 位十六进制），**不是项目名称**。
- 选择器按 `p.id === datasetId` 反查 `KBProjectOption`，展示文本仍用 `project.name`，
  不要把 dataset id 暴露给用户。
- 新增 / 删除文档后调用 `store.fetchProjects()` / `store.fetchTree()` 刷新。
