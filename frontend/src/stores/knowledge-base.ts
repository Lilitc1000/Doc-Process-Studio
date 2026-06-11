import { defineStore } from 'pinia';
import { ref } from 'vue';
import type {
  KBProject,
  KBTreeResponse,
} from '../types/knowledge-base/knowledge-base';
import {
  listKBProjects,
  createKBProject,
  renameKBProject,
  deleteKBProject,
  getKBTree,
} from '../api/knowledge-base';

export const useKnowledgeBaseStore = defineStore('knowledge-base', () => {
  const projects = ref<KBProject[]>([]);
  const currentProject = ref<KBProject | null>(null);
  const currentTree = ref<KBTreeResponse | null>(null);
  const isLoading = ref(false);

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

  function reset() {
    currentProject.value = null;
    currentTree.value = null;
  }

  return {
    projects,
    currentProject,
    currentTree,
    isLoading,
    fetchProjects,
    createProject,
    renameProject,
    removeProject,
    fetchTree,
    reset,
  };
});
