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
        @show-parse-detail="onShowParseDetail"
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

    <teleport to="body">
      <div
        v-if="showParseDialog && store.parseDetail"
        class="kb-dialog-overlay"
        @click.self="closeParseDialog"
      >
        <div class="kb-dialog kb-parse-dialog">
          <h2 class="kb-dialog-title">解析详情</h2>

          <div class="kb-parse-detail">
            <div class="kb-parse-row">
              <span class="kb-parse-label">文件名</span>
              <span class="kb-parse-value">{{
                store.parseDetail.fileName
              }}</span>
            </div>
            <div class="kb-parse-row">
              <span class="kb-parse-label">状态</span>
              <span
                class="kb-parse-value"
                :class="statusClass(store.parseDetail.parseStatus)"
                >{{ statusText(store.parseDetail.parseStatus) }}</span
              >
            </div>
            <div class="kb-parse-row">
              <span class="kb-parse-label">进度</span>
              <span class="kb-parse-value"
                >{{ (store.parseDetail.progress * 100).toFixed(0) }}%</span
              >
            </div>
            <div class="kb-parse-row">
              <span class="kb-parse-label">分块数</span>
              <span class="kb-parse-value">{{
                store.parseDetail.chunkCount
              }}</span>
            </div>
            <div class="kb-parse-row">
              <span class="kb-parse-label">Token 数</span>
              <span class="kb-parse-value">{{
                store.parseDetail.tokenCount
              }}</span>
            </div>
            <div class="kb-parse-row">
              <span class="kb-parse-label">耗时</span>
              <span class="kb-parse-value"
                >{{
                  (store.parseDetail.processDuration ?? 0).toFixed(1)
                }}s</span
              >
            </div>
          </div>

          <div class="kb-parse-msg-wrap">
            <span class="kb-parse-label">进度信息</span>
            <pre class="kb-parse-msg">{{ store.parseDetail.message }}</pre>
          </div>

          <div class="kb-dialog-actions">
            <base-button
              variant="primary"
              :disabled="store.isReparsing"
              @click="onReparse"
              >{{
                store.isReparsing ? '重新解析中...' : '重新解析'
              }}</base-button
            >
            <base-button variant="ghost" @click="closeParseDialog"
              >关闭</base-button
            >
          </div>
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
import type { ParseStatus } from '../types/knowledge-base';
import KbTreeNode from './KbTreeNode.vue';

const route = useRoute();
const router = useRouter();
const store = useKnowledgeBaseStore();

const projectId = computed(() => route.params.id as string);

const isUploading = ref(false);
const showIndexingDialog = ref(false);

// 解析详情弹窗状态
const showParseDialog = ref(false);
const activeDocId = ref<string | null>(null);

onMounted(() => {
  store.startStatusPolling(projectId.value);
  store.fetchProjects();
});

onUnmounted(() => {
  store.stopStatusPolling();
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
    await store.startStatusPolling(projectId.value);
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

const statusText = (status: ParseStatus): string => {
  if (status === 'UNSTART') return '未索引';
  if (status === 'RUNNING') return '解析中';
  if (status === 'DONE') return '解析成功';
  return '解析失败';
};

const statusClass = (status: ParseStatus): string => {
  if (status === 'FAIL') return 'kb-parse-status--fail';
  if (status === 'DONE') return 'kb-parse-status--done';
  return 'kb-parse-status--pending';
};

const onShowParseDetail = async (docId: string) => {
  activeDocId.value = docId;
  await store.fetchParseDetail(docId);
  showParseDialog.value = true;
};

const onReparse = async () => {
  if (!activeDocId.value) return;
  await store.reparseDocument(activeDocId.value);
  if (activeDocId.value) await store.fetchParseDetail(activeDocId.value);
  store.startStatusPolling(projectId.value);
};

const closeParseDialog = () => {
  showParseDialog.value = false;
  activeDocId.value = null;
};
</script>

<style scoped src="./styles/kb-detail-page.css"></style>
