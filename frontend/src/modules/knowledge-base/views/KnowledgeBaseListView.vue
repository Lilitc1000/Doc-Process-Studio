<template>
  <section class="kb-list-page">
    <div class="kb-list-header">
      <h1 class="kb-list-title">知识库</h1>
      <base-button variant="primary" @click="showCreateDialog = true">
        + 新建项目
      </base-button>
    </div>

    <div v-if="store.isLoading" class="kb-list-loading">加载中...</div>

    <div v-else-if="store.projects.length === 0" class="kb-list-empty">
      <p>暂无知识库项目</p>
      <p class="kb-list-empty-hint">点击「新建项目」创建您的第一个知识库</p>
    </div>

    <div v-else class="kb-list-grid">
      <div
        v-for="project in store.projects"
        :key="project.id"
        class="kb-project-card"
        @click="onProjectClick(project.id)"
      >
        <div class="kb-project-card-header">
          <span class="kb-project-icon">📁</span>
          <span class="kb-project-name">{{ project.name }}</span>
        </div>
        <div class="kb-project-card-meta">
          <span>{{ project.documentCount }} 文档</span>
          <span v-if="project.lastUpdatedAt">
            · 更新于 {{ formatDate(project.lastUpdatedAt) }}
          </span>
        </div>
        <div class="kb-project-card-actions" @click.stop>
          <base-button variant="ghost" size="sm" @click="onRename(project)">
            重命名
          </base-button>
          <base-button variant="ghost" size="sm" @click="onDelete(project)">
            删除
          </base-button>
        </div>
      </div>
    </div>

    <teleport to="body">
      <div
        v-if="showCreateDialog"
        class="kb-dialog-overlay"
        @click.self="showCreateDialog = false"
      >
        <div class="kb-dialog">
          <h3 class="kb-dialog-title">新建知识库项目</h3>
          <label class="kb-dialog-label">
            项目名称
            <base-input
              v-model="newProjectName"
              placeholder="请输入项目名称"
              @keyup.enter="onCreateProject"
            />
          </label>
          <div class="kb-dialog-actions">
            <base-button variant="ghost" @click="showCreateDialog = false"
              >取消</base-button
            >
            <base-button
              variant="primary"
              :disabled="!newProjectName.trim()"
              @click="onCreateProject"
            >
              创建
            </base-button>
          </div>
        </div>
      </div>

      <div
        v-if="showRenameDialog"
        class="kb-dialog-overlay"
        @click.self="showRenameDialog = false"
      >
        <div class="kb-dialog">
          <h3 class="kb-dialog-title">重命名项目</h3>
          <label class="kb-dialog-label">
            新名称
            <base-input
              v-model="renameValue"
              placeholder="请输入新名称"
              @keyup.enter="onConfirmRename"
            />
          </label>
          <div class="kb-dialog-actions">
            <base-button variant="ghost" @click="showRenameDialog = false"
              >取消</base-button
            >
            <base-button
              variant="primary"
              :disabled="!renameValue.trim()"
              @click="onConfirmRename"
            >
              确认
            </base-button>
          </div>
        </div>
      </div>
    </teleport>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import BaseButton from '@shared/ui/BaseButton.vue';
import BaseInput from '@shared/ui/BaseInput.vue';
import { useKnowledgeBaseStore } from '../store/knowledge-base';
import type { KBProject } from '../types/knowledge-base';

const router = useRouter();
const store = useKnowledgeBaseStore();

const showCreateDialog = ref(false);
const newProjectName = ref('');
const showRenameDialog = ref(false);
const renameValue = ref('');
const renamingProject = ref<KBProject | null>(null);

onMounted(() => {
  store.fetchProjects();
});

const formatDate = (dateStr: string) => {
  const date = new Date(dateStr);
  return `${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
};

const onProjectClick = (projectId: string) => {
  router.push({ name: 'knowledge-base-detail', params: { id: projectId } });
};

const onCreateProject = async () => {
  if (!newProjectName.value.trim()) return;
  await store.createProject(newProjectName.value.trim());
  newProjectName.value = '';
  showCreateDialog.value = false;
};

const onRename = (project: KBProject) => {
  renamingProject.value = project;
  renameValue.value = project.name;
  showRenameDialog.value = true;
};

const onConfirmRename = async () => {
  if (!renamingProject.value || !renameValue.value.trim()) return;
  await store.renameProject(renamingProject.value.id, renameValue.value.trim());
  showRenameDialog.value = false;
  renamingProject.value = null;
};

const onDelete = async (project: KBProject) => {
  if (!confirm(`确定删除项目「${project.name}」？此操作不可恢复。`)) return;
  await store.removeProject(project.id);
};
</script>

<style scoped src="./styles/kb-list-page.css"></style>
