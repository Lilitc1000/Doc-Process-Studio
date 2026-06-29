export interface KBProject {
  id: string;
  name: string;
  description: string | null;
  folderCount: number;
  documentCount: number;
  isUpdating: boolean;
  lastUpdatedAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface KBFolder {
  id: string;
  projectId: string;
  parentId: string | null;
  name: string;
  path: string;
  sortOrder: number;
  createdAt: string;
  updatedAt: string;
}

export interface KBDocument {
  id: string;
  projectId: string;
  folderId: string | null;
  fileName: string;
  fileType: string;
  fileSize: number;
  chunkCount: number;
  version: number;
  isIndexed: boolean;
  isLatest: boolean;
  uploadedAt: string;
}

export interface KBTreeNodeFolder {
  type: 'folder';
  id: string;
  name: string;
  path: string;
  sortOrder: number;
  children: KBTreeNode[];
}

export interface KBTreeNodeDocument {
  type: 'document';
  id: string;
  name: string;
  fileType: string;
  fileSize: number;
  chunkCount: number;
  version: number;
  isIndexed: boolean;
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
