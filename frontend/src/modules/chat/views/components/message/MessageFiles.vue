<template>
  <div :class="containerClass">
    <template v-if="editable">
      <div
        v-for="(file, index) in files"
        :key="buildFileKey(file, index)"
        class="message-edit-file-item"
      >
        <span
          class="message-file-icon"
          :style="getFileIconStyle(file.name, file.mimeType)"
          :title="getFileIconLabel(file.name, file.mimeType)"
          aria-hidden="true"
        >
          <svg viewBox="0 0 20 20" class="message-file-icon-svg">
            <path
              d="M6 2.75H10.6L14.75 6.9V15a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 15V5A2.25 2.25 0 016 2.75z"
              fill="var(--file-icon-bg)"
              stroke="var(--file-icon-border)"
              stroke-linejoin="round"
              stroke-width="1.2"
            />
            <path
              d="M10.5 2.75V6.25H14"
              fill="none"
              stroke="var(--file-icon-border)"
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="1.2"
            />
          </svg>
          <span class="message-file-icon-badge">
            {{ getFileIconBadge(file.name, file.mimeType) }}
          </span>
        </span>
        <div class="message-edit-file-meta">
          <span class="message-file-name">{{ file.name }}</span>
          <span class="message-file-size">{{ file.sizeLabel }}</span>
        </div>
        <base-button
          class="message-edit-file-remove"
          type="button"
          variant="ghost"
          size="sm"
          title="移除文件"
          @click="$emit('remove', index)"
        >
          ✕
        </base-button>
      </div>
    </template>

    <template v-else>
      <base-button
        v-for="(file, index) in files"
        :key="buildFileKey(file, index)"
        class="message-file-item"
        variant="ghost"
        size="sm"
        :class="{
          'is-downloadable': Boolean(file.attachmentId),
          'is-static': !file.attachmentId,
        }"
        type="button"
        @click="onFileClick(file)"
      >
        <span
          class="message-file-icon"
          :style="getFileIconStyle(file.name, file.mimeType)"
          :title="getFileIconLabel(file.name, file.mimeType)"
          aria-hidden="true"
        >
          <svg viewBox="0 0 20 20" class="message-file-icon-svg">
            <path
              d="M6 2.75H10.6L14.75 6.9V15a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 15V5A2.25 2.25 0 016 2.75z"
              fill="var(--file-icon-bg)"
              stroke="var(--file-icon-border)"
              stroke-linejoin="round"
              stroke-width="1.2"
            />
            <path
              d="M10.5 2.75V6.25H14"
              fill="none"
              stroke="var(--file-icon-border)"
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="1.2"
            />
          </svg>
          <span class="message-file-icon-badge">
            {{ getFileIconBadge(file.name, file.mimeType) }}
          </span>
        </span>
        <div class="message-file-meta">
          <span class="message-file-name">{{ file.name }}</span>
          <span class="message-file-size">{{ file.sizeLabel }}</span>
        </div>
      </base-button>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import BaseButton from '@shared/ui/BaseButton.vue';
import type { ChatAttachment } from '../../../types/chat';
import { getFileTypeVisual } from '@shared/utils/file';

const props = defineProps<{
  files: ChatAttachment[];
  editable?: boolean;
}>();

const emit = defineEmits<{
  (e: 'remove', index: number): void;
  (e: 'download', file: ChatAttachment): void;
}>();

const editable = computed(() => props.editable ?? false);
const containerClass = computed(() => {
  return editable.value ? 'message-edit-files' : 'message-files';
});

const getFileIconStyle = (fileName: string, mimeType?: string) => {
  const visual = getFileTypeVisual(fileName, mimeType);
  return {
    '--file-icon-fg': visual.color,
    '--file-icon-bg': visual.background,
    '--file-icon-border': visual.border,
  };
};

const getFileIconBadge = (fileName: string, mimeType?: string) => {
  return getFileTypeVisual(fileName, mimeType).badge;
};

const getFileIconLabel = (fileName: string, mimeType?: string) => {
  return getFileTypeVisual(fileName, mimeType).label;
};

const buildFileKey = (file: ChatAttachment, index: number) => {
  return `${file.name}-${file.sizeLabel}-${file.attachmentId ?? 'plain'}-${index}`;
};

const onFileClick = (file: ChatAttachment) => {
  if (!file.attachmentId) {
    return;
  }
  emit('download', file);
};
</script>
