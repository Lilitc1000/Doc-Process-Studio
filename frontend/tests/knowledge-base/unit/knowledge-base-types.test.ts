import { describe, expect, it } from 'vitest';
import type {
  KBProject,
  KBFolder,
  KBDocument,
  KBTreeNode,
  KBTreeNodeFolder,
  KBTreeNodeDocument,
  KBTreeResponse,
  KBProjectSimple,
} from '../../../src/types/knowledge-base/knowledge-base';

function makeKBProject(overrides: Partial<KBProject> = {}): KBProject {
  return {
    id: 'proj-001',
    name: 'Test Project',
    description: null,
    folderCount: 0,
    documentCount: 0,
    isUpdating: false,
    lastUpdatedAt: null,
    createdAt: '2026-01-01T00:00:00Z',
    updatedAt: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

function makeKBFolder(overrides: Partial<KBFolder> = {}): KBFolder {
  return {
    id: 'folder-001',
    projectId: 'proj-001',
    parentId: null,
    name: 'Test Folder',
    path: 'Test Folder',
    sortOrder: 0,
    createdAt: '2026-01-01T00:00:00Z',
    updatedAt: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

function makeKBDocument(overrides: Partial<KBDocument> = {}): KBDocument {
  return {
    id: 'doc-001',
    projectId: 'proj-001',
    folderId: null,
    fileName: 'test.pdf',
    fileType: 'pdf',
    fileSize: 1024,
    chunkCount: 5,
    version: 1,
    isIndexed: true,
    isLatest: true,
    uploadedAt: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

describe('KBProject', () => {
  it('创建包含所有必填字段', () => {
    const project = makeKBProject();
    expect(project.id).toBe('proj-001');
    expect(project.name).toBe('Test Project');
    expect(project.description).toBeNull();
    expect(project.folderCount).toBe(0);
    expect(project.documentCount).toBe(0);
    expect(project.isUpdating).toBe(false);
  });

  it('支持覆盖字段', () => {
    const project = makeKBProject({ name: 'Custom', documentCount: 10 });
    expect(project.name).toBe('Custom');
    expect(project.documentCount).toBe(10);
  });
});

describe('KBFolder', () => {
  it('创建包含所有必填字段', () => {
    const folder = makeKBFolder();
    expect(folder.id).toBe('folder-001');
    expect(folder.projectId).toBe('proj-001');
    expect(folder.parentId).toBeNull();
    expect(folder.name).toBe('Test Folder');
    expect(folder.sortOrder).toBe(0);
  });

  it('支持嵌套文件夹', () => {
    const child = makeKBFolder({ parentId: 'folder-001', name: 'Child' });
    expect(child.parentId).toBe('folder-001');
  });
});

describe('KBDocument', () => {
  it('创建包含所有必填字段', () => {
    const doc = makeKBDocument();
    expect(doc.id).toBe('doc-001');
    expect(doc.fileName).toBe('test.pdf');
    expect(doc.fileType).toBe('pdf');
    expect(doc.version).toBe(1);
    expect(doc.isIndexed).toBe(true);
    expect(doc.isLatest).toBe(true);
  });

  it('支持多版本文档', () => {
    const doc = makeKBDocument({ version: 3, isLatest: false });
    expect(doc.version).toBe(3);
    expect(doc.isLatest).toBe(false);
  });
});

describe('KBTreeNode', () => {
  it('文件夹节点包含 children', () => {
    const docNode: KBTreeNodeDocument = {
      type: 'document',
      id: 'doc-001',
      name: 'test.pdf',
      fileType: 'pdf',
      fileSize: 1024,
      chunkCount: 5,
      version: 1,
      isIndexed: true,
      uploadedAt: '2026-01-01T00:00:00Z',
    };
    const folderNode: KBTreeNodeFolder = {
      type: 'folder',
      id: 'folder-001',
      name: 'Root',
      path: 'Root',
      sortOrder: 0,
      children: [docNode],
    };
    expect(folderNode.type).toBe('folder');
    expect(folderNode.children).toHaveLength(1);
    expect(folderNode.children[0].type).toBe('document');
  });

  it('文档节点无 children', () => {
    const docNode: KBTreeNodeDocument = {
      type: 'document',
      id: 'doc-001',
      name: 'report.docx',
      fileType: 'docx',
      fileSize: 2048,
      chunkCount: 10,
      version: 2,
      isIndexed: false,
      uploadedAt: '2026-01-01T00:00:00Z',
    };
    expect(docNode.type).toBe('document');
    expect(docNode.isIndexed).toBe(false);
  });

  it('KBTreeNode 联合类型区分文件夹和文档', () => {
    const folder: KBTreeNode = {
      type: 'folder',
      id: 'f1',
      name: 'F',
      path: 'F',
      sortOrder: 0,
      children: [],
    };
    const doc: KBTreeNode = {
      type: 'document',
      id: 'd1',
      name: 'D',
      fileType: 'pdf',
      fileSize: 100,
      chunkCount: 1,
      version: 1,
      isIndexed: true,
      uploadedAt: '2026-01-01T00:00:00Z',
    };

    if (folder.type === 'folder') {
      expect(folder.children).toEqual([]);
    }
    if (doc.type === 'document') {
      expect(doc.fileType).toBe('pdf');
    }
  });
});

describe('KBTreeResponse', () => {
  it('包含项目信息和树结构', () => {
    const tree: KBTreeResponse = {
      projectId: 'proj-001',
      projectName: 'Test Project',
      tree: [],
    };
    expect(tree.projectId).toBe('proj-001');
    expect(tree.tree).toEqual([]);
  });
});

describe('KBProjectSimple', () => {
  it('只包含 id 和 name', () => {
    const simple: KBProjectSimple = { id: 'proj-001', name: 'Test' };
    expect(simple.id).toBe('proj-001');
    expect(simple.name).toBe('Test');
  });
});
