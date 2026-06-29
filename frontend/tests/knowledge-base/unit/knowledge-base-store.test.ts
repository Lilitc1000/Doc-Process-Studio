import { describe, expect, it, vi, beforeEach } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useKnowledgeBaseStore } from '@modules/knowledge-base';
import * as kbApi from '@modules/knowledge-base';
import type { KBProject, KBTreeResponse } from '@modules/knowledge-base';

vi.mock('@modules/knowledge-base', async (importOriginal) => {
  const original =
    await importOriginal<typeof import('@modules/knowledge-base')>();
  return {
    ...original,
    listKBProjects: vi.fn(),
    createKBProject: vi.fn(),
    renameKBProject: vi.fn(),
    deleteKBProject: vi.fn(),
    getKBTree: vi.fn(),
  };
});

function makeProject(overrides: Partial<KBProject> = {}): KBProject {
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

function makeTree(overrides: Partial<KBTreeResponse> = {}): KBTreeResponse {
  return {
    projectId: 'proj-001',
    projectName: 'Test Project',
    tree: [],
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
});
