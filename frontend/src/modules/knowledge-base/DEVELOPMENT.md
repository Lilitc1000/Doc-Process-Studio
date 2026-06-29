# Knowledge Base 页面开发指南

## 目录结构

```text
frontend/src/views/knowledge-base/
├── KnowledgeBaseListView.vue    # 知识库项目列表页
├── KnowledgeBaseDetailView.vue  # 知识库项目详情页（文档树 + 上传 + 更新）
├── KbTreeNode.vue               # 树形节点组件（递归渲染文件夹/文档）
└── styles/
    ├── kb-list-page.css         # 列表页样式
    ├── kb-detail-page.css       # 详情页样式
    └── kb-tree-node.css         # 树节点样式
```

## 类型定义

所有类型定义集中在 `src/types/knowledge-base/knowledge-base.ts`，API 层和组件通过 import 引用：

| 类型              | 说明                                                 |
| ----------------- | ---------------------------------------------------- | --------------------- |
| `KBProject`       | 知识库项目（id、name、documentCount、isUpdating 等） |
| `KBFolder`        | 文件夹（支持多级嵌套）                               |
| `KBDocument`      | 文档（支持版本管理、索引状态）                       |
| `KBTreeNode`      | 树形节点联合类型（`KBTreeNodeFolder                  | KBTreeNodeDocument`） |
| `KBTreeResponse`  | 树形结构响应（projectId + tree 数组）                |
| `KBUpdateStatus`  | 更新状态（isUpdating + message）                     |
| `KBProjectSimple` | 简要项目信息（id + name，供 Skill 选择器使用）       |

## Store 状态说明

`useKnowledgeBaseStore`（不持久化）：

- `projects`：项目列表
- `currentProject`：当前查看的项目
- `currentTree`：当前项目的文档树
- `isLoading`：列表加载状态
- `isUpdating`：知识库更新状态

核心方法：`fetchProjects`、`createProject`、`renameProject`、`removeProject`、`fetchTree`、`triggerUpdate`、`checkUpdateStatus`、`reset`

## 组件规范

- 所有按钮使用 `BaseButton`，输入框使用 `BaseInput`，文件上传使用 `BaseFileUpload`
- 样式通过 `<style scoped src="./styles/xxx.css">` 引入，不内联在 `.vue` 文件中
- 类型从 `src/types/knowledge-base/knowledge-base.ts` 导入，不在组件内重复定义
