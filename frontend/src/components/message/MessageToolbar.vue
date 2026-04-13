<template>
  <div
    class="message-toolbar"
    :class="{ 'toolbar-actions-only': !showVersionSwitcher }"
  >
    <div v-if="showVersionSwitcher" class="message-version-switcher">
      <button
        class="message-tool-btn"
        :disabled="!canGoPrev || isVersionLocked"
        title="查看上一版"
        @click="$emit('prev-version')"
      >
        <svg viewBox="0 0 16 16" class="message-tool-icon" aria-hidden="true">
          <path
            d="M9.75 3.5L5.25 8L9.75 12.5"
            fill="none"
            stroke="currentColor"
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="1.8"
          />
        </svg>
      </button>
      <span class="message-version-text"
        >{{ versionIndex }}/{{ versionCount }}</span
      >
      <button
        class="message-tool-btn"
        :disabled="!canGoNext || isVersionLocked"
        title="查看下一版"
        @click="$emit('next-version')"
      >
        <svg viewBox="0 0 16 16" class="message-tool-icon" aria-hidden="true">
          <path
            d="M6.25 3.5L10.75 8L6.25 12.5"
            fill="none"
            stroke="currentColor"
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="1.8"
          />
        </svg>
      </button>
    </div>

    <div class="message-tool-actions">
      <template v-if="isEditing">
        <label class="message-tool-btn" title="选择文件">
          <svg viewBox="0 0 16 16" class="message-tool-icon" aria-hidden="true">
            <path
              d="M10.75 5.25L6.63 9.37A2.12 2.12 0 103.63 6.37l4.59-4.59a3.25 3.25 0 114.59 4.59L7.16 12a4.25 4.25 0 11-6.01-6.01l4.95-4.95"
              fill="none"
              stroke="currentColor"
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="1.4"
            />
          </svg>
          <input
            class="message-edit-file-input"
            type="file"
            multiple
            @change="onEditFileSelect"
          />
        </label>
        <button
          class="message-tool-btn is-cancel"
          title="取消编辑"
          @click="$emit('cancel-edit')"
        >
          <svg viewBox="0 0 16 16" class="message-tool-icon" aria-hidden="true">
            <path
              d="M4 4L12 12M12 4L4 12"
              fill="none"
              stroke="currentColor"
              stroke-linecap="round"
              stroke-width="1.8"
            />
          </svg>
        </button>
        <button
          class="message-tool-btn is-confirm"
          :disabled="!canConfirmEdit"
          title="确认并重新发送"
          @click="$emit('confirm-edit')"
        >
          <svg viewBox="0 0 16 16" class="message-tool-icon" aria-hidden="true">
            <path
              d="M3.75 8.5L6.75 11.5L12.25 5.5"
              fill="none"
              stroke="currentColor"
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="1.8"
            />
          </svg>
        </button>
      </template>

      <template v-else-if="role === 'user'">
        <button
          class="message-tool-btn"
          :disabled="!canEdit"
          title="编辑消息"
          @click="$emit('start-edit')"
        >
          <svg viewBox="0 0 16 16" class="message-tool-icon" aria-hidden="true">
            <path
              d="M3 11.75L4 9L10.5 2.5A1.77 1.77 0 0113 5l-6.5 6.5L3 11.75z"
              fill="none"
              stroke="currentColor"
              stroke-linejoin="round"
              stroke-width="1.4"
            />
            <path
              d="M9.5 3.5L12 6"
              fill="none"
              stroke="currentColor"
              stroke-linecap="round"
              stroke-width="1.4"
            />
          </svg>
        </button>
        <button
          class="message-tool-btn"
          :disabled="!canCopy"
          title="复制消息"
          @click="$emit('copy')"
        >
          <svg viewBox="0 0 16 16" class="message-tool-icon" aria-hidden="true">
            <rect
              x="5"
              y="3"
              width="7"
              height="9"
              rx="1.6"
              fill="none"
              stroke="currentColor"
              stroke-width="1.4"
            />
            <path
              d="M3.5 10.5H3A1.5 1.5 0 011.5 9V4A1.5 1.5 0 013 2.5h5A1.5 1.5 0 019.5 4v.5"
              fill="none"
              stroke="currentColor"
              stroke-linecap="round"
              stroke-width="1.4"
            />
          </svg>
        </button>
      </template>

      <template v-else>
        <button
          class="message-tool-btn"
          :disabled="!canRegenerate"
          title="重新生成"
          @click="$emit('regenerate')"
        >
          <svg viewBox="0 0 16 16" class="message-tool-icon" aria-hidden="true">
            <path
              d="M12.25 5.25V2.75H9.75"
              fill="none"
              stroke="currentColor"
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="1.6"
            />
            <path
              d="M12 8A4 4 0 104.86 10.5"
              fill="none"
              stroke="currentColor"
              stroke-linecap="round"
              stroke-width="1.6"
            />
          </svg>
        </button>
        <button
          class="message-tool-btn"
          :disabled="!canCopy"
          title="复制回答"
          @click="$emit('copy')"
        >
          <svg viewBox="0 0 16 16" class="message-tool-icon" aria-hidden="true">
            <rect
              x="5"
              y="3"
              width="7"
              height="9"
              rx="1.6"
              fill="none"
              stroke="currentColor"
              stroke-width="1.4"
            />
            <path
              d="M3.5 10.5H3A1.5 1.5 0 011.5 9V4A1.5 1.5 0 013 2.5h5A1.5 1.5 0 019.5 4v.5"
              fill="none"
              stroke="currentColor"
              stroke-linecap="round"
              stroke-width="1.4"
            />
          </svg>
        </button>
        <button
          v-if="canOpenTrace"
          class="message-tool-btn"
          title="查看链路"
          @click="$emit('open-trace')"
        >
          <svg viewBox="0 0 16 16" class="message-tool-icon" aria-hidden="true">
            <path
              d="M2.5 4.5H6L7.5 7.5H13.5"
              fill="none"
              stroke="currentColor"
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="1.4"
            />
            <path
              d="M2.5 11.5H6L7.5 8.5H13.5"
              fill="none"
              stroke="currentColor"
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="1.4"
            />
          </svg>
        </button>
        <button
          class="message-tool-btn"
          :disabled="!canDownload"
          title="下载为 Markdown"
          @click="$emit('download')"
        >
          <svg viewBox="0 0 16 16" class="message-tool-icon" aria-hidden="true">
            <path
              d="M8 2.75V10.25"
              fill="none"
              stroke="currentColor"
              stroke-linecap="round"
              stroke-width="1.6"
            />
            <path
              d="M5.25 7.75L8 10.5L10.75 7.75"
              fill="none"
              stroke="currentColor"
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="1.6"
            />
            <path
              d="M3 12.5H13"
              fill="none"
              stroke="currentColor"
              stroke-linecap="round"
              stroke-width="1.6"
            />
          </svg>
        </button>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { ChatMessageRole } from '../../types/chat';

const props = defineProps<{
  role: ChatMessageRole;
  isEditing?: boolean;
  showVersionSwitcher?: boolean;
  versionIndex?: number;
  versionCount?: number;
  canGoPrev?: boolean;
  canGoNext?: boolean;
  isVersionLocked?: boolean;
  canEdit?: boolean;
  canRegenerate?: boolean;
  canCopy?: boolean;
  canDownload?: boolean;
  canOpenTrace?: boolean;
  canConfirmEdit?: boolean;
}>();

const emit = defineEmits<{
  (e: 'prev-version'): void;
  (e: 'next-version'): void;
  (e: 'start-edit'): void;
  (e: 'upload-edit-files', files: File[]): void;
  (e: 'cancel-edit'): void;
  (e: 'confirm-edit'): void;
  (e: 'regenerate'): void;
  (e: 'copy'): void;
  (e: 'open-trace'): void;
  (e: 'download'): void;
}>();

const isEditing = computed(() => props.isEditing ?? false);
const showVersionSwitcher = computed(() => props.showVersionSwitcher ?? false);
const versionIndex = computed(() => props.versionIndex ?? 1);
const versionCount = computed(() => props.versionCount ?? 1);
const canGoPrev = computed(() => props.canGoPrev ?? false);
const canGoNext = computed(() => props.canGoNext ?? false);
const isVersionLocked = computed(() => props.isVersionLocked ?? false);
const canEdit = computed(() => props.canEdit ?? false);
const canRegenerate = computed(() => props.canRegenerate ?? false);
const canCopy = computed(() => props.canCopy ?? false);
const canDownload = computed(() => props.canDownload ?? false);
const canOpenTrace = computed(() => props.canOpenTrace ?? false);
const canConfirmEdit = computed(() => props.canConfirmEdit ?? false);

const onEditFileSelect = (event: Event) => {
  const input = event.target as HTMLInputElement;
  if (input.files && input.files.length > 0) {
    emit('upload-edit-files', Array.from(input.files));
    input.value = '';
  }
};
</script>
