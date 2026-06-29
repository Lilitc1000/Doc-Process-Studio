// knowledge-base 模块桶文件：统一导出知识库域公共 API

// --- Store ---
export { useKnowledgeBaseStore } from './store/knowledge-base';

// --- API ---
export {
  listKBProjects,
  createKBProject,
  renameKBProject,
  deleteKBProject,
  createKBFolder,
  renameKBFolder,
  deleteKBFolder,
  getKBTree,
  uploadKBDocument,
  deleteKBDocument,
  listKBProjectsSimple,
} from './api/knowledge-base';

// --- Types ---
export type {
  KBProject,
  KBFolder,
  KBDocument,
  KBTreeNodeFolder,
  KBTreeNodeDocument,
  KBTreeNode,
  KBTreeResponse,
  KBProjectSimple,
} from './types/knowledge-base';
