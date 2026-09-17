import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useKnowledgeBaseStore } from '@modules/knowledge-base';
import * as kbApi from '@modules/knowledge-base';
import type {
  KBProject,
  KBTreeResponse,
  KBTreeNodeDocument,
  KBDocumentParseDetail,
} from '@modules/knowledge-base';

vi.mock(
  '@modules/knowledge-base/api/knowledge-base',
  async (importOriginal) => {
    const original =
      await importOriginal<
        typeof import('@modules/knowledge-base/api/knowledge-base')
      >();
    return {
      ...original,
      listKBProjects: vi.fn(),
      createKBProject: vi.fn(),
      renameKBProject: vi.fn(),
      deleteKBProject: vi.fn(),
      getKBTree: vi.fn(),
      getDocumentParseDetail: vi.fn(),
      reparseDocument: vi.fn(),
    };
  },
);

function makeProject(overrides: Partial<KBProject> = {}): KBProject {
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

function makeTree(overrides: Partial<KBTreeResponse> = {}): KBTreeResponse {
  return {
    projectId: 'proj-001',
    projectName: 'Test Project',
    tree: [],
    ...overrides,
  };
}

function makeParseDetail(
  overrides: Partial<KBDocumentParseDetail> = {},
): KBDocumentParseDetail {
  return {
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
    ...overrides,
  };
}

function makeDoc(
  overrides: Partial<KBTreeNodeDocument> = {},
): KBTreeNodeDocument {
  return {
    type: 'document',
    id: 'doc-001',
    name: 'report.pdf',
    fileType: 'pdf',
    fileSize: 1024,
    chunkCount: 5,
    isIndexed: false,
    parseStatus: 'UNSTART',
    uploadedAt: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

describe('useKnowledgeBaseStore', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setActivePinia(createPinia());
  });

  describe('初始状态', () => {
    it('projects 为空数组', () => {
      const store = useKnowledgeBaseStore();
      expect(store.projects).toEqual([]);
    });

    it('currentProject 为 null', () => {
      const store = useKnowledgeBaseStore();
      expect(store.currentProject).toBeNull();
    });

    it('currentTree 为 null', () => {
      const store = useKnowledgeBaseStore();
      expect(store.currentTree).toBeNull();
    });

    it('isLoading 为 false', () => {
      const store = useKnowledgeBaseStore();
      expect(store.isLoading).toBe(false);
    });

    it('parseDetail 为 null 且 isReparsing 为 false', () => {
      const store = useKnowledgeBaseStore();
      expect(store.parseDetail).toBeNull();
      expect(store.isReparsing).toBe(false);
    });
  });

  describe('fetchProjects', () => {
    it('成功获取项目列表', async () => {
      const mockProjects = [
        makeProject(),
        makeProject({ id: 'proj-002', name: 'Project 2' }),
      ];
      (kbApi.listKBProjects as ReturnType<typeof vi.fn>).mockResolvedValue(
        mockProjects,
      );

      const store = useKnowledgeBaseStore();
      await store.fetchProjects();

      expect(store.projects).toEqual(mockProjects);
      expect(store.isLoading).toBe(false);
    });

    it('加载时设置 isLoading 为 true', async () => {
      let resolvePromise: (value: KBProject[]) => void;
      const promise = new Promise<KBProject[]>((resolve) => {
        resolvePromise = resolve;
      });
      (kbApi.listKBProjects as ReturnType<typeof vi.fn>).mockReturnValue(
        promise,
      );

      const store = useKnowledgeBaseStore();
      const fetchPromise = store.fetchProjects();

      expect(store.isLoading).toBe(true);
      resolvePromise!([makeProject()]);
      await fetchPromise;
      expect(store.isLoading).toBe(false);
    });

    it('请求失败时 isLoading 仍恢复为 false', async () => {
      (kbApi.listKBProjects as ReturnType<typeof vi.fn>).mockRejectedValue(
        new Error('Network error'),
      );

      const store = useKnowledgeBaseStore();
      await expect(store.fetchProjects()).rejects.toThrow('Network error');
      expect(store.isLoading).toBe(false);
    });
  });

  describe('createProject', () => {
    it('创建项目并添加到列表头部', async () => {
      const newProject = makeProject({ id: 'proj-new', name: 'New Project' });
      (kbApi.createKBProject as ReturnType<typeof vi.fn>).mockResolvedValue(
        newProject,
      );

      const store = useKnowledgeBaseStore();
      store.projects = [makeProject()];

      const result = await store.createProject('New Project');

      expect(result).toEqual(newProject);
      expect(store.projects[0]).toEqual(newProject);
      expect(store.projects).toHaveLength(2);
    });

    it('传递 description 参数', async () => {
      const newProject = makeProject({
        id: 'proj-new',
        name: 'New',
        description: 'desc',
      });
      (kbApi.createKBProject as ReturnType<typeof vi.fn>).mockResolvedValue(
        newProject,
      );

      const store = useKnowledgeBaseStore();
      await store.createProject('New', 'desc');

      expect(kbApi.createKBProject).toHaveBeenCalledWith('New', 'desc');
    });
  });

  describe('renameProject', () => {
    it('重命名项目并更新列表', async () => {
      const updated = makeProject({ id: 'proj-001', name: 'Renamed' });
      (kbApi.renameKBProject as ReturnType<typeof vi.fn>).mockResolvedValue(
        updated,
      );

      const store = useKnowledgeBaseStore();
      store.projects = [makeProject()];

      const result = await store.renameProject('proj-001', 'Renamed');

      expect(result).toEqual(updated);
      expect(store.projects[0].name).toBe('Renamed');
    });

    it('重命名不存在的项目不影响列表', async () => {
      const updated = makeProject({ id: 'proj-999', name: 'Renamed' });
      (kbApi.renameKBProject as ReturnType<typeof vi.fn>).mockResolvedValue(
        updated,
      );

      const store = useKnowledgeBaseStore();
      store.projects = [makeProject()];

      await store.renameProject('proj-999', 'Renamed');
      expect(store.projects).toHaveLength(1);
    });
  });

  describe('removeProject', () => {
    it('删除项目并从列表移除', async () => {
      (kbApi.deleteKBProject as ReturnType<typeof vi.fn>).mockResolvedValue(
        undefined,
      );

      const store = useKnowledgeBaseStore();
      store.projects = [
        makeProject(),
        makeProject({ id: 'proj-002', name: 'P2' }),
      ];

      await store.removeProject('proj-001');

      expect(store.projects).toHaveLength(1);
      expect(store.projects[0].id).toBe('proj-002');
    });

    it('删除当前项目时清空 currentProject 和 currentTree', async () => {
      (kbApi.deleteKBProject as ReturnType<typeof vi.fn>).mockResolvedValue(
        undefined,
      );

      const store = useKnowledgeBaseStore();
      const project = makeProject();
      store.projects = [project];
      store.currentProject = project;
      store.currentTree = makeTree();

      await store.removeProject('proj-001');

      expect(store.currentProject).toBeNull();
      expect(store.currentTree).toBeNull();
    });

    it('删除非当前项目不影响 currentProject', async () => {
      (kbApi.deleteKBProject as ReturnType<typeof vi.fn>).mockResolvedValue(
        undefined,
      );

      const store = useKnowledgeBaseStore();
      const currentProject = makeProject();
      store.projects = [currentProject, makeProject({ id: 'proj-002' })];
      store.currentProject = currentProject;

      await store.removeProject('proj-002');

      expect(store.currentProject).toEqual(currentProject);
    });
  });

  describe('fetchTree', () => {
    it('获取树结构并设置 currentProject', async () => {
      const tree = makeTree();
      (kbApi.getKBTree as ReturnType<typeof vi.fn>).mockResolvedValue(tree);

      const store = useKnowledgeBaseStore();
      store.projects = [makeProject()];

      await store.fetchTree('proj-001');

      expect(store.currentTree).toEqual(tree);
      expect(store.currentProject?.id).toBe('proj-001');
    });

    it('项目不在列表中时 currentProject 不更新', async () => {
      const tree = makeTree();
      (kbApi.getKBTree as ReturnType<typeof vi.fn>).mockResolvedValue(tree);

      const store = useKnowledgeBaseStore();
      store.projects = [];

      await store.fetchTree('proj-001');

      expect(store.currentTree).toEqual(tree);
      expect(store.currentProject).toBeNull();
    });
  });

  describe('reset', () => {
    it('清空 currentProject 和 currentTree', () => {
      const store = useKnowledgeBaseStore();
      store.currentProject = makeProject();
      store.currentTree = makeTree();

      store.reset();

      expect(store.currentProject).toBeNull();
      expect(store.currentTree).toBeNull();
    });

    it('不影响 projects 列表', () => {
      const store = useKnowledgeBaseStore();
      store.projects = [makeProject()];

      store.reset();

      expect(store.projects).toHaveLength(1);
    });
  });

  describe('fetchParseDetail', () => {
    it('将返回的解析详情写入 parseDetail', async () => {
      const detail = makeParseDetail();
      (
        kbApi.getDocumentParseDetail as ReturnType<typeof vi.fn>
      ).mockResolvedValue(detail);

      const store = useKnowledgeBaseStore();
      await store.fetchParseDetail('doc-001');

      expect(kbApi.getDocumentParseDetail).toHaveBeenCalledWith('doc-001');
      expect(store.parseDetail).toEqual(detail);
    });
  });

  describe('reparseDocument', () => {
    it('调用 api 的 reparseDocument', async () => {
      (kbApi.reparseDocument as ReturnType<typeof vi.fn>).mockResolvedValue(
        undefined,
      );

      const store = useKnowledgeBaseStore();
      await store.reparseDocument('doc-001');

      expect(kbApi.reparseDocument).toHaveBeenCalledWith('doc-001');
    });

    it('执行期间 isReparsing 为 true，结束后恢复 false', async () => {
      let resolvePromise: () => void;
      const promise = new Promise<void>((resolve) => {
        resolvePromise = resolve;
      });
      (kbApi.reparseDocument as ReturnType<typeof vi.fn>).mockReturnValue(
        promise,
      );

      const store = useKnowledgeBaseStore();
      const reparsePromise = store.reparseDocument('doc-001');

      expect(store.isReparsing).toBe(true);
      resolvePromise!();
      await reparsePromise;
      expect(store.isReparsing).toBe(false);
    });

    it('即使请求失败也恢复 isReparsing 为 false', async () => {
      (kbApi.reparseDocument as ReturnType<typeof vi.fn>).mockRejectedValue(
        new Error('reparse failed'),
      );

      const store = useKnowledgeBaseStore();
      await expect(store.reparseDocument('doc-001')).rejects.toThrow(
        'reparse failed',
      );
      expect(store.isReparsing).toBe(false);
    });
  });

  describe('startStatusPolling / stopStatusPolling', () => {
    beforeEach(() => {
      vi.useFakeTimers();
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it('全部为终态时启动后不轮询（isPolling 保持 false，仅拉取一次树）', async () => {
      const tree = makeTree({
        tree: [makeDoc({ parseStatus: 'DONE', isIndexed: true })],
      });
      (kbApi.getKBTree as ReturnType<typeof vi.fn>).mockResolvedValue(tree);

      const store = useKnowledgeBaseStore();
      await store.startStatusPolling('proj-001');

      expect(store.isPolling).toBe(false);
      expect(kbApi.getKBTree).toHaveBeenCalledTimes(1);
      expect(store.currentTree).toEqual(tree);
    });

    it('存在 UNSTART/RUNNING 时启动轮询并设置 isPolling 为 true', async () => {
      const tree = makeTree({ tree: [makeDoc({ parseStatus: 'UNSTART' })] });
      (kbApi.getKBTree as ReturnType<typeof vi.fn>).mockResolvedValue(tree);

      const store = useKnowledgeBaseStore();
      await store.startStatusPolling('proj-001');

      expect(store.isPolling).toBe(true);
      expect(kbApi.getKBTree).toHaveBeenCalledTimes(1);
    });

    it('轮询到全部终态后自动停止', async () => {
      const runningTree = makeTree({
        tree: [makeDoc({ parseStatus: 'RUNNING' })],
      });
      const doneTree = makeTree({
        tree: [makeDoc({ parseStatus: 'DONE', isIndexed: true })],
      });
      (kbApi.getKBTree as ReturnType<typeof vi.fn>)
        .mockResolvedValueOnce(runningTree)
        .mockResolvedValueOnce(doneTree);

      const store = useKnowledgeBaseStore();
      await store.startStatusPolling('proj-001');
      expect(store.isPolling).toBe(true);

      await vi.advanceTimersByTimeAsync(2000);

      expect(store.isPolling).toBe(false);
      expect(kbApi.getKBTree).toHaveBeenCalledTimes(2);
      expect(store.currentTree).toEqual(doneTree);
    });

    it('stopStatusPolling 清除计时器并复位 isPolling', async () => {
      const tree = makeTree({ tree: [makeDoc({ parseStatus: 'RUNNING' })] });
      (kbApi.getKBTree as ReturnType<typeof vi.fn>).mockResolvedValue(tree);

      const store = useKnowledgeBaseStore();
      await store.startStatusPolling('proj-001');
      expect(store.isPolling).toBe(true);

      store.stopStatusPolling();
      expect(store.isPolling).toBe(false);

      const callsBefore = (kbApi.getKBTree as ReturnType<typeof vi.fn>).mock
        .calls.length;
      await vi.advanceTimersByTimeAsync(2000);
      expect(
        (kbApi.getKBTree as ReturnType<typeof vi.fn>).mock.calls.length,
      ).toBe(callsBefore);
    });

    it('reset 会停止正在进行的轮询', async () => {
      const tree = makeTree({ tree: [makeDoc({ parseStatus: 'RUNNING' })] });
      (kbApi.getKBTree as ReturnType<typeof vi.fn>).mockResolvedValue(tree);

      const store = useKnowledgeBaseStore();
      await store.startStatusPolling('proj-001');
      expect(store.isPolling).toBe(true);

      store.reset();
      expect(store.isPolling).toBe(false);
      expect(store.currentTree).toBeNull();
    });
  });
});
