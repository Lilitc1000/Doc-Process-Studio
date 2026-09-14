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

| 类型                 | 说明                                                                                                                    |
| -------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| `KBProject`          | 知识库项目（id = dataset id、name、description、documentCount、createdAt、updatedAt）                                   |
| `KBDocument`         | 文档（id、projectId、fileName、fileType、fileSize、chunkCount、isIndexed、uploadedAt）                                  |
| `KBTreeNode`         | 树形节点联合类型（`KBTreeNodeFolder \| KBTreeNodeDocument`）                                                            |
| `KBTreeNodeFolder`   | 文件夹节点（type、id、name、children；**无 path / sortOrder**）                                                         |
| `KBTreeNodeDocument` | 文档节点（type、id、name、fileType、fileSize、chunkCount、isIndexed、uploadedAt；**无 version / isLatest / folderId**） |
| `KBTreeResponse`     | 树形结构响应（projectId + projectName + tree 数组）                                                                     |
| `KBProjectSimple`    | 简要项目信息（id + name，供 Skill `$` 选择器使用）                                                                      |

> 已移除：`KBFolder`（文件夹写模型）、`KBUpdateStatus`、`KBProject.isUpdating` /
> `lastUpdatedAt` / `folderCount`、`KBDocument.version` / `isLatest` / `folderId`、
> 以及 `KBTreeNodeFolder.path` / `sortOrder`。

## Store 状态说明

`useKnowledgeBaseStore`（不持久化）：

- `projects`：项目列表
- `currentProject`：当前查看的项目
- `currentTree`：当前项目的文档树
- `isLoading`：列表加载状态

核心方法：`fetchProjects`、`createProject`、`renameProject`、`removeProject`、`fetchTree`、`reset`

## 组件规范

- 所有按钮使用 `BaseButton`，文件上传使用 `BaseFileUpload`（KbTreeNode / DetailView 不再使用 BaseInput）。
- 样式通过 `<style scoped src="./styles/xxx.css">` 引入，不内联在 `.vue` 文件中。
- 类型从 `src/modules/knowledge-base/types/knowledge-base.ts` 导入，不在组件内重复定义。

## Skill `$` 提及（对话）

对话输入框通过 `useSkillMentionSelector` 支持 `@`/`$` 提及知识库。

- 提及 id 形如 `kb:<datasetId>`（即项目 `id`，32 位十六进制），**不是项目名称**。
- 选择器按 `p.id === datasetId` 反查 `KBProjectOption`，展示文本仍用 `project.name`，
  不要把 dataset id 暴露给用户。
- 新增 / 删除文档后调用 `store.fetchProjects()` / `store.fetchTree()` 刷新。
