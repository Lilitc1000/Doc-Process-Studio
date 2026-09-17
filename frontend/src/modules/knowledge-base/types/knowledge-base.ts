// 知识库领域类型定义。
// 数据来源：RAGFlow。应用里的「知识库项目」对应 RAGFlow 的 dataset，
// 因此项目 id 即为 dataset id（32 位十六进制，如 f05e5a4aadac11f1b9211b18c23af0c8）。
// RAGFlow 这版不支持在 dataset 内写操作文件夹（接口仅 GET/PUT/PATCH），
// 故前端只消费文件夹（只读、可展开）与文档，不提供任何文件夹写入口。

// 文档解析状态（来自 RAGFlow 的文档解析进度）。
export type ParseStatus = 'UNSTART' | 'RUNNING' | 'DONE' | 'FAIL';

export interface KBProject {
  id: string;
  name: string;
  description: string | null;
  documentCount: number;
  createdAt: string;
  updatedAt: string;
}

export interface KBDocument {
  id: string;
  fileName: string;
  fileType: string;
  fileSize: number;
  chunkCount: number;
  isIndexed: boolean;
  parseStatus: ParseStatus;
  uploadedAt: string;
}

export interface KBTreeNodeFolder {
  type: 'folder';
  id: string;
  name: string;
  children: KBTreeNode[];
}

export interface KBTreeNodeDocument {
  type: 'document';
  id: string;
  name: string;
  fileType: string;
  fileSize: number;
  chunkCount: number;
  isIndexed: boolean;
  parseStatus: ParseStatus;
  uploadedAt: string;
}

export type KBTreeNode = KBTreeNodeFolder | KBTreeNodeDocument;

export interface KBTreeResponse {
  projectId: string;
  projectName: string;
  tree: KBTreeNode[];
}

export interface KBProjectSimple {
  id: string;
  name: string;
}

// 文档解析详情（GET /knowledge-base/documents/{id}/parse-detail）。
// 后端为 snake_case，经 axios 拦截器 humps.camelizeKeys 自动转为 camelCase。
export interface KBDocumentParseDetail {
  documentId: string;
  fileName: string;
  parseStatus: ParseStatus;
  isIndexed: boolean;
  progress: number;
  chunkCount: number;
  tokenCount: number;
  processDuration: number | null;
  message: string;
  updatedAt: string | null;
}
