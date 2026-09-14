<template>
  <section class="kb-detail-page">
    <div class="kb-detail-header">
      <base-button variant="ghost" @click="onBack">← 返回</base-button>
      <h1 class="kb-detail-title">
        {{ store.currentProject?.name || '加载中...' }}
      </h1>
      <div class="kb-detail-actions">
        <base-button
          variant="primary"
          :disabled="isUploading"
          @click="onUpload"
        >
          {{ isUploading ? '上传中...' : '上传文档' }}
        </base-button>
      </div>
    </div>

    <div v-if="store.currentTree" class="kb-tree">
      <kb-tree-node
        v-for="node in store.currentTree.tree"
        :key="node.type + node.id"
        :node="node"
        :project-id="projectId"
        @delete-document="onDeleteDocument"
      />
      <div v-if="store.currentTree.tree.length === 0" class="kb-tree-empty">
        暂无文档，点击「上传文档」开始
      </div>
    </div>

    <base-file-upload @select="onFileSelect">
      <template #default>
        <span style="display: none">文件上传</span>
      </template>
    </base-file-upload>

    <teleport to="body">
      <div v-if="showIndexingDialog" class="kb-dialog-overlay">
        <div class="kb-dialog kb-dialog--updating">
          <div class="kb-updating-spinner"></div>
          <p class="kb-updating-text">正在上传并索引文档，请稍候...</p>
        </div>
      </div>
    </teleport>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import BaseButton from '@shared/ui/BaseButton.vue';
import BaseFileUpload from '@shared/ui/BaseFileUpload.vue';
import { useKnowledgeBaseStore } from '../store/knowledge-base';
import { uploadKBDocument, deleteKBDocument } from '../api/knowledge-base';
import KbTreeNode from './KbTreeNode.vue';

const route = useRoute();
const router = useRouter();
const store = useKnowledgeBaseStore();

const projectId = computed(() => route.params.id as string);

const isUploading = ref(false);
const showIndexingDialog = ref(false);

onMounted(() => {
  store.fetchTree(projectId.value);
  store.fetchProjects();
});

onUnmounted(() => {
  store.reset();
});

watch(projectId, (newId) => {
  if (newId) store.fetchTree(newId);
});

const onBack = () => {
  router.push({ name: 'knowledge-base-list' });
};

const onUpload = () => {
  const fileInput = document.querySelector<HTMLInputElement>(
    '.base-file-upload input[type="file"]',
  );
  fileInput?.click();
};

const onFileSelect = async (files: File[]) => {
  const file = files[0];
  if (!file) return;

  isUploading.value = true;
  showIndexingDialog.value = true;
  try {
    await uploadKBDocument(projectId.value, file);
    await store.fetchTree(projectId.value);
    await store.fetchProjects();
  } catch (e) {
    alert('上传失败：' + (e instanceof Error ? e.message : '未知错误'));
  } finally {
    isUploading.value = false;
    showIndexingDialog.value = false;
  }
};

const onDeleteDocument = async (documentId: string) => {
  if (!confirm('确定删除此文档？')) return;
  await deleteKBDocument(documentId);
  await store.fetchTree(projectId.value);
  await store.fetchProjects();
};
</script>

<style scoped src="./styles/kb-detail-page.css"></style>
