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

    <div class="kb-detail-toolbar">
      <base-button variant="ghost" size="sm" @click="onCreateFolder(null)"
        >+ 新建文件夹</base-button
      >
    </div>

    <div v-if="store.currentTree" class="kb-tree">
      <kb-tree-node
        v-for="node in store.currentTree.tree"
        :key="node.type + node.id"
        :node="node"
        :project-id="projectId"
        @create-folder="onCreateFolder"
        @upload-to-folder="onUploadToFolder"
        @rename-folder="onRenameFolder"
        @delete-folder="onDeleteFolder"
        @delete-document="onDeleteDocument"
      />
      <div v-if="store.currentTree.tree.length === 0" class="kb-tree-empty">
        暂无文档，点击「上传文档」或「新建文件夹」开始
      </div>
    </div>

    <base-file-upload @select="onFileSelect">
      <template #default>
        <span style="display: none">文件上传</span>
      </template>
    </base-file-upload>

    <teleport to="body">
      <div
        v-if="showFolderDialog"
        class="kb-dialog-overlay"
        @click.self="showFolderDialog = false"
      >
        <div class="kb-dialog">
          <h3 class="kb-dialog-title">新建文件夹</h3>
          <label class="kb-dialog-label">
            文件夹名称
            <base-input
              v-model="newFolderName"
              placeholder="请输入文件夹名称"
              @keyup.enter="onConfirmCreateFolder"
            />
          </label>
          <div class="kb-dialog-actions">
            <base-button variant="ghost" @click="showFolderDialog = false"
              >取消</base-button
            >
            <base-button
              variant="primary"
              :disabled="!newFolderName.trim()"
              @click="onConfirmCreateFolder"
            >
              创建
            </base-button>
          </div>
        </div>
      </div>

      <div
        v-if="showRenameFolderDialog"
        class="kb-dialog-overlay"
        @click.self="showRenameFolderDialog = false"
      >
        <div class="kb-dialog">
          <h3 class="kb-dialog-title">重命名文件夹</h3>
          <label class="kb-dialog-label">
            新名称
            <base-input
              v-model="renameFolderValue"
              placeholder="请输入新名称"
              @keyup.enter="onConfirmRenameFolder"
            />
          </label>
          <div class="kb-dialog-actions">
            <base-button variant="ghost" @click="showRenameFolderDialog = false"
              >取消</base-button
            >
            <base-button
              variant="primary"
              :disabled="!renameFolderValue.trim()"
              @click="onConfirmRenameFolder"
            >
              确认
            </base-button>
          </div>
        </div>
      </div>

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
import BaseButton from '../../components/base/BaseButton.vue';
import BaseInput from '../../components/base/BaseInput.vue';
import BaseFileUpload from '../../components/base/BaseFileUpload.vue';
import { useKnowledgeBaseStore } from '../../stores/knowledge-base';
import {
  createKBFolder,
  renameKBFolder,
  deleteKBFolder,
  uploadKBDocument,
  deleteKBDocument,
} from '../../api/knowledge-base';
import KbTreeNode from './KbTreeNode.vue';

const route = useRoute();
const router = useRouter();
const store = useKnowledgeBaseStore();

const projectId = computed(() => route.params.id as string);

const uploadTargetFolderId = ref<string | null>(null);
const isUploading = ref(false);
const showFolderDialog = ref(false);
const newFolderName = ref('');
const newFolderParentId = ref<string | null>(null);
const showRenameFolderDialog = ref(false);
const renameFolderValue = ref('');
const renamingFolderId = ref('');
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
  uploadTargetFolderId.value = null;
  const fileInput = document.querySelector<HTMLInputElement>(
    '.base-file-upload input[type="file"]',
  );
  fileInput?.click();
};

const onUploadToFolder = (folderId: string) => {
  uploadTargetFolderId.value = folderId;
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
    await uploadKBDocument(
      projectId.value,
      file,
      uploadTargetFolderId.value ?? undefined,
    );
    await store.fetchTree(projectId.value);
    await store.fetchProjects();
  } catch (e) {
    alert('上传失败：' + (e instanceof Error ? e.message : '未知错误'));
  } finally {
    isUploading.value = false;
    showIndexingDialog.value = false;
  }
};

const onCreateFolder = (parentId: string | null) => {
  newFolderParentId.value = parentId;
  newFolderName.value = '';
  showFolderDialog.value = true;
};

const onConfirmCreateFolder = async () => {
  if (!newFolderName.value.trim()) return;
  await createKBFolder(
    projectId.value,
    newFolderName.value.trim(),
    newFolderParentId.value ?? undefined,
  );
  showFolderDialog.value = false;
  await store.fetchTree(projectId.value);
  await store.fetchProjects();
};

const onRenameFolder = (folderId: string, currentName: string) => {
  renamingFolderId.value = folderId;
  renameFolderValue.value = currentName;
  showRenameFolderDialog.value = true;
};

const onConfirmRenameFolder = async () => {
  if (!renameFolderValue.value.trim()) return;
  await renameKBFolder(renamingFolderId.value, renameFolderValue.value.trim());
  showRenameFolderDialog.value = false;
  await store.fetchTree(projectId.value);
};

const onDeleteFolder = async (folderId: string) => {
  if (!confirm('确定删除此文件夹？')) return;
  await deleteKBFolder(folderId);
  await store.fetchTree(projectId.value);
  await store.fetchProjects();
};

const onDeleteDocument = async (documentId: string) => {
  if (!confirm('确定删除此文档？')) return;
  await deleteKBDocument(documentId);
  await store.fetchTree(projectId.value);
  await store.fetchProjects();
};
</script>

<style scoped src="./styles/kb-detail-page.css"></style>
