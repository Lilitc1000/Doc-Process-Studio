import { defineStore } from 'pinia';
import { ref } from 'vue';
import type {
  KBProject,
  KBTreeResponse,
  KBDocumentParseDetail,
  KBTreeNode,
  KBTreeNodeDocument,
} from '../types/knowledge-base';
import {
  listKBProjects,
  createKBProject,
  renameKBProject,
  deleteKBProject,
  getKBTree,
  getDocumentParseDetail,
  reparseDocument as reparseKBDocument,
} from '../api/knowledge-base';

export const useKnowledgeBaseStore = defineStore('knowledge-base', () => {
  const projects = ref<KBProject[]>([]);
  const currentProject = ref<KBProject | null>(null);
  const currentTree = ref<KBTreeResponse | null>(null);
  const isLoading = ref(false);

  // 当前查看的文档解析详情
  const parseDetail = ref<KBDocumentParseDetail | null>(null);
  const isReparsing = ref(false);

  // 解析状态轮询（上传 / 重新解析后启动，全部到终态即停止）
  const isPolling = ref(false);
  let pollTimer: ReturnType<typeof setInterval> | null = null;

  function flattenDocs(nodes: KBTreeNode[]): KBTreeNodeDocument[] {
    const docs: KBTreeNodeDocument[] = [];
    for (const n of nodes) {
      if (n.type === 'document') docs.push(n);
      else if (n.type === 'folder') docs.push(...flattenDocs(n.children));
    }
    return docs;
  }

  function hasInProgressNode(tree: KBTreeResponse | null): boolean {
    if (!tree) return false;
    return flattenDocs(tree.tree).some(
      (d) => d.parseStatus === 'UNSTART' || d.parseStatus === 'RUNNING',
    );
  }

  function stopStatusPolling() {
    if (pollTimer !== null) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
    isPolling.value = false;
  }

  async function startStatusPolling(projectId: string) {
    // 先拉一次树：若已是终态（全部 DONE/FAIL）则无需轮询
    try {
      await fetchTree(projectId);
    } catch {
      // 初始拉取失败不阻塞；后续 tick 会重试
    }
    if (!hasInProgressNode(currentTree.value)) {
      return;
    }
    if (pollTimer !== null) return; // 已在轮询
    isPolling.value = true;
    pollTimer = setInterval(async () => {
      try {
        await fetchTree(projectId);
      } catch {
        return; // 拉取失败不终止轮询，下一 tick 再试
      }
      // 若解析详情弹窗正打开且对应文档仍在解析，同步刷新详情
      const pd = parseDetail.value;
      if (
        pd &&
        (pd.parseStatus === 'UNSTART' || pd.parseStatus === 'RUNNING')
      ) {
        try {
          await fetchParseDetail(pd.documentId);
        } catch {
          // 刷新详情失败不影响轮询
        }
      }
      if (!hasInProgressNode(currentTree.value)) {
        stopStatusPolling();
      }
    }, 2000);
  }

  async function fetchProjects() {
    isLoading.value = true;
    try {
      projects.value = await listKBProjects();
    } finally {
      isLoading.value = false;
    }
  }

  async function createProject(name: string, description = '') {
    const project = await createKBProject(name, description);
    projects.value.unshift(project);
    return project;
  }

  async function renameProject(projectId: string, name: string) {
    const updated = await renameKBProject(projectId, name);
    const index = projects.value.findIndex((p) => p.id === projectId);
    if (index !== -1) {
      projects.value[index] = updated;
    }
    return updated;
  }

  async function removeProject(projectId: string) {
    await deleteKBProject(projectId);
    projects.value = projects.value.filter((p) => p.id !== projectId);
    if (currentProject.value?.id === projectId) {
      currentProject.value = null;
      currentTree.value = null;
    }
  }

  async function fetchTree(projectId: string) {
    currentTree.value = await getKBTree(projectId);
    const project = projects.value.find((p) => p.id === projectId);
    if (project) {
      currentProject.value = project;
    }
  }

  async function fetchParseDetail(documentId: string) {
    parseDetail.value = await getDocumentParseDetail(documentId);
  }

  async function reparseDocument(documentId: string) {
    isReparsing.value = true;
    try {
      await reparseKBDocument(documentId);
    } finally {
      isReparsing.value = false;
    }
  }

  function reset() {
    stopStatusPolling();
    currentProject.value = null;
    currentTree.value = null;
    parseDetail.value = null;
  }

  return {
    projects,
    currentProject,
    currentTree,
    isLoading,
    parseDetail,
    isReparsing,
    isPolling,
    fetchProjects,
    createProject,
    renameProject,
    removeProject,
    fetchTree,
    fetchParseDetail,
    reparseDocument,
    startStatusPolling,
    stopStatusPolling,
    reset,
  };
});
