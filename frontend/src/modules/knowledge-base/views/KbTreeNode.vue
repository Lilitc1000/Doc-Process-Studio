<template>
  <div
    class="kb-tree-node"
    :style="{ paddingLeft: `calc(${depth ?? 0} * var(--space-xl))` }"
  >
    <!-- Folder -->
    <div
      v-if="node.type === 'folder'"
      class="kb-tree-item kb-tree-item--folder"
    >
      <div class="kb-tree-item-row" @click="toggleExpand">
        <span class="kb-tree-expand">{{ isExpanded ? '▼' : '▶' }}</span>
        <span class="kb-tree-icon">📁</span>
        <span class="kb-tree-name">{{ node.name }}</span>
      </div>
    </div>
    <div v-if="node.type === 'folder' && isExpanded" class="kb-tree-children">
      <kb-tree-node
        v-for="child in node.children"
        :key="child.type + child.id"
        :node="child"
        :project-id="projectId"
        :depth="(depth ?? 0) + 1"
        @delete-document="(id: string) => $emit('deleteDocument', id)"
        @show-parse-detail="(id: string) => $emit('showParseDetail', id)"
      />
    </div>

    <!-- Document -->
    <div
      v-if="node.type === 'document'"
      class="kb-tree-item kb-tree-item--document"
    >
      <div class="kb-tree-item-row">
        <span class="kb-tree-icon">{{ fileIcon }}</span>
        <span class="kb-tree-name">{{ node.name }}</span>
        <span
          v-if="parseLabel"
          class="kb-tree-badge"
          :class="
            node.parseStatus === 'FAIL'
              ? 'kb-tree-badge--fail'
              : node.parseStatus === 'DONE'
                ? 'kb-tree-badge--done'
                : 'kb-tree-badge--pending'
          "
          @click.stop="$emit('showParseDetail', node.id)"
          >{{ parseLabel }}</span
        >
      </div>
      <div class="kb-tree-item-actions">
        <base-button
          variant="ghost"
          size="sm"
          @click.stop="$emit('deleteDocument', node.id)"
          >删除</base-button
        >
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import BaseButton from '@shared/ui/BaseButton.vue';
import type { KBTreeNode } from '../types/knowledge-base';

const props = defineProps<{
  node: KBTreeNode;
  projectId: string;
  depth?: number;
}>();

defineEmits<{
  deleteDocument: [documentId: string];
  showParseDetail: [documentId: string];
}>();

const isExpanded = ref(true);

const toggleExpand = () => {
  isExpanded.value = !isExpanded.value;
};

const fileIcon = computed(() => {
  if (props.node.type !== 'document') return '📄';
  const ext = props.node.fileType;
  if (ext === 'pdf') return '📕';
  if (ext === 'docx') return '📘';
  if (ext === 'xlsx') return '📗';
  return '📄';
});

// 解析状态徽章文案（简洁）：未索引 / 解析中 / 解析失败 / 解析成功；无状态时不显示。
const parseLabel = computed(() => {
  const s = props.node.type === 'document' ? props.node.parseStatus : null;
  if (s === 'UNSTART') return '未索引';
  if (s === 'RUNNING') return '解析中';
  if (s === 'FAIL') return '解析失败';
  if (s === 'DONE') return '解析成功';
  return '';
});
</script>

<style scoped src="./styles/kb-tree-node.css"></style>
