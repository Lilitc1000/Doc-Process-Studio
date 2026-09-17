import { describe, expect, it } from 'vitest';
import type {
  KBProject,
  KBDocument,
  KBTreeNode,
  KBTreeNodeFolder,
  KBTreeNodeDocument,
  KBTreeResponse,
  KBProjectSimple,
  ParseStatus,
  KBDocumentParseDetail,
} from '@modules/knowledge-base';

function makeKBProject(overrides: Partial<KBProject> = {}): KBProject {
  return {
    id: 'proj-001',
    name: 'Test Project',
    description: null,
    documentCount: 0,
    createdAt: '2026-01-01T00:00:00Z',
    updatedAt: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

function makeKBDocument(overrides: Partial<KBDocument> = {}): KBDocument {
  return {
    id: 'doc-001',
    fileName: 'test.pdf',
    fileType: 'pdf',
    fileSize: 1024,
    chunkCount: 5,
    isIndexed: true,
    parseStatus: 'DONE',
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
    expect(project.documentCount).toBe(0);
    expect(project.createdAt).toBe('2026-01-01T00:00:00Z');
    expect(project.updatedAt).toBe('2026-01-01T00:00:00Z');
  });

  it('支持覆盖字段', () => {
    const project = makeKBProject({ name: 'Custom', documentCount: 10 });
    expect(project.name).toBe('Custom');
    expect(project.documentCount).toBe(10);
  });
});

describe('KBDocument', () => {
  it('创建包含所有必填字段', () => {
    const doc = makeKBDocument();
    expect(doc.id).toBe('doc-001');
    expect(doc.fileName).toBe('test.pdf');
    expect(doc.fileType).toBe('pdf');
    expect(doc.isIndexed).toBe(true);
    expect(doc.parseStatus).toBe('DONE');
  });

  it('支持未索引文档', () => {
    const doc = makeKBDocument({ isIndexed: false });
    expect(doc.isIndexed).toBe(false);
  });

  it('parseStatus 为 ParseStatus 联合类型', () => {
    const statuses: ParseStatus[] = ['UNSTART', 'RUNNING', 'DONE', 'FAIL'];
    for (const s of statuses) {
      const doc = makeKBDocument({ parseStatus: s });
      expect(doc.parseStatus).toBe(s);
    }
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
      isIndexed: true,
      parseStatus: 'DONE',
      uploadedAt: '2026-01-01T00:00:00Z',
    };
    const folderNode: KBTreeNodeFolder = {
      type: 'folder',
      id: 'folder-001',
      name: 'Root',
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
      isIndexed: false,
      parseStatus: 'UNSTART',
      uploadedAt: '2026-01-01T00:00:00Z',
    };
    expect(docNode.type).toBe('document');
    expect(docNode.isIndexed).toBe(false);
    expect(docNode.parseStatus).toBe('UNSTART');
  });

  it('KBTreeNode 联合类型区分文件夹和文档', () => {
    const folder: KBTreeNode = {
      type: 'folder',
      id: 'f1',
      name: 'F',
      children: [],
    };
    const doc: KBTreeNode = {
      type: 'document',
      id: 'd1',
      name: 'D',
      fileType: 'pdf',
      fileSize: 100,
      chunkCount: 1,
      isIndexed: true,
      parseStatus: 'DONE',
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

describe('ParseStatus', () => {
  it('仅包含 4 个合法取值', () => {
    const valid: ParseStatus[] = ['UNSTART', 'RUNNING', 'DONE', 'FAIL'];
    valid.forEach((s) => {
      const detail = {} as { parseStatus: ParseStatus };
      detail.parseStatus = s;
      expect(valid).toContain(detail.parseStatus);
    });
  });
});

describe('KBDocumentParseDetail', () => {
  it('camelCase 字段与后端 snake_case 对应', () => {
    const detail: KBDocumentParseDetail = {
      documentId: 'doc-001',
      fileName: 'test.pdf',
      parseStatus: 'RUNNING',
      isIndexed: false,
      progress: 0.5,
      chunkCount: 0,
      tokenCount: 1200,
      processDuration: null,
      message: '解析进度 50%',
      updatedAt: null,
    };
    expect(detail.documentId).toBe('doc-001');
    expect(detail.fileName).toBe('test.pdf');
    expect(detail.parseStatus).toBe('RUNNING');
    expect(detail.isIndexed).toBe(false);
    expect(detail.progress).toBe(0.5);
    expect(detail.chunkCount).toBe(0);
    expect(detail.tokenCount).toBe(1200);
    expect(detail.processDuration).toBeNull();
    expect(detail.message).toBe('解析进度 50%');
    expect(detail.updatedAt).toBeNull();
  });

  it('processDuration 可为数字', () => {
    const detail: KBDocumentParseDetail = {
      documentId: 'doc-002',
      fileName: 'a.pdf',
      parseStatus: 'DONE',
      isIndexed: true,
      progress: 1,
      chunkCount: 3,
      tokenCount: 900,
      processDuration: 12.34,
      message: '',
      updatedAt: '2026-01-01T00:00:00Z',
    };
    expect(detail.processDuration).toBe(12.34);
    expect(detail.message).toBe('');
  });
});
