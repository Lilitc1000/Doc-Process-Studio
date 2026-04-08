<template>
  <div
    class="chat-message"
    :class="[
      `role-${message.role}`,
      {
        'is-editing': isEditing,
        'toolbar-visible': showToolbarByDefault,
      },
    ]"
  >
    <div class="message-track">
      <div class="message-header">
        <div class="avatar" :class="`avatar-${message.role}`">
          <span class="avatar-label">{{ avatarLabel }}</span>
        </div>
        <div class="message-info">
          <span class="message-role">{{ messageRole }}</span>
          <span class="message-meta-dot" aria-hidden="true"></span>
          <span class="message-time">{{ formattedTime }}</span>
        </div>
      </div>
      <div
        ref="messageContentRef"
        class="message-content"
        :class="{ thinking: isThinking }"
      >
        <div v-if="isEditing" class="message-edit-panel">
          <div v-if="editingFiles.length > 0" class="message-edit-files">
            <div
              v-for="(file, index) in editingFiles"
              :key="`${file.name}-${file.sizeLabel}-${index}`"
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
                <span class="message-file-size">
                  {{ file.sizeLabel }}
                </span>
              </div>
              <button
                class="message-edit-file-remove"
                type="button"
                title="移除文件"
                @click="$emit('remove-edit-file', index)"
              >
                ✕
              </button>
            </div>
          </div>
          <textarea
            ref="editTextareaRef"
            class="message-edit-textarea"
            rows="1"
            :value="editingText"
            placeholder="编辑消息内容..."
            @input="onEditTextInput"
          ></textarea>
        </div>
        <template v-else>
          <div
            v-if="showInlineLiveToolStatus"
            class="message-live-tool-status"
            aria-live="polite"
          >
            <div class="message-live-tool-status-leading" aria-hidden="true">
              <span class="message-live-tool-status-orbit"></span>
              <span class="message-live-tool-status-core"></span>
            </div>
            <div class="message-live-tool-status-content">
              <div class="message-live-tool-status-headline">
                <span class="message-live-tool-status-title">
                  {{ liveToolStatusLabel }}
                </span>
                <span class="message-live-tool-status-phase">
                  {{ liveToolStatusPhase }}
                </span>
              </div>
              <div class="message-live-tool-status-message">
                {{ liveToolStatusMessage }}
              </div>
            </div>
          </div>
          <div
            v-if="
              isThinking &&
              !normalizedDisplayContent.trim().length &&
              !(message.files && message.files.length > 0)
            "
            class="thinking-state"
          >
            <span class="thinking-spinner"></span>
            <span>思考中...</span>
          </div>
          <details
            v-if="showHistoricalToolStatuses"
            class="message-tool-status"
            :open="isToolStatusPanelOpen"
            :class="{ 'is-processing': isToolStatusPanelOpen }"
          >
            <summary class="message-tool-status-summary">
              <span class="message-tool-status-title">
                {{ isToolStatusPanelOpen ? '处理中' : '处理过程' }}
              </span>
              <span class="message-tool-status-count">
                {{ toolStatuses.length }} 条
              </span>
            </summary>
            <div class="message-tool-status-list">
              <div
                v-for="toolStatus in toolStatuses"
                :key="toolStatus.id"
                class="message-tool-status-item"
                :class="{
                  'is-running': toolStatus.phase === 'start',
                  'is-finished': toolStatus.phase === 'finish',
                }"
              >
                <span class="message-tool-status-dot" aria-hidden="true"></span>
                <div class="message-tool-status-body">
                  <div class="message-tool-status-headline">
                    <span class="message-tool-status-message">
                      {{ toolStatus.message }}
                    </span>
                    <span
                      class="message-tool-status-phase"
                      :class="{
                        'is-running': toolStatus.phase === 'start',
                        'is-finished': toolStatus.phase === 'finish',
                      }"
                    >
                      {{ formatToolPhase(toolStatus.phase) }}
                    </span>
                  </div>
                  <span
                    v-if="
                      toolStatus.label ||
                      toolStatus.toolName ||
                      toolStatus.createdAt
                    "
                    class="message-tool-status-meta"
                  >
                    <template v-if="toolStatus.label || toolStatus.toolName">
                      {{
                        toolStatus.label ||
                        formatFallbackToolName(toolStatus.toolName)
                      }}
                    </template>
                    <template
                      v-if="
                        (toolStatus.label || toolStatus.toolName) &&
                        toolStatus.createdAt
                      "
                    >
                      <span class="message-tool-status-separator">·</span>
                    </template>
                    <template v-if="toolStatus.createdAt">
                      {{ formatStatusTime(toolStatus.createdAt) }}
                    </template>
                  </span>
                </div>
              </div>
            </div>
          </details>
          <template v-if="message.role === 'assistant'">
            <!-- eslint-disable vue/no-v-html -->
            <div
              v-if="normalizedDisplayContent.trim().length > 0"
              class="message-text"
              v-html="renderedContent"
            ></div>
            <!-- eslint-enable vue/no-v-html -->
            <div
              v-if="message.files && message.files.length > 0"
              class="message-files"
            >
              <button
                v-for="file in message.files"
                :key="`${file.name}-${file.sizeLabel}-${file.attachmentId ?? 'plain'}`"
                class="message-file-item"
                :class="{
                  'is-downloadable': Boolean(file.attachmentId),
                  'is-static': !file.attachmentId,
                }"
                type="button"
                @click="onMessageFileClick(file)"
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
              </button>
            </div>
          </template>
          <template v-else>
            <div
              v-if="message.files && message.files.length > 0"
              class="message-files"
            >
              <button
                v-for="file in message.files"
                :key="`${file.name}-${file.sizeLabel}-${file.attachmentId ?? 'plain'}`"
                class="message-file-item"
                :class="{
                  'is-downloadable': Boolean(file.attachmentId),
                  'is-static': !file.attachmentId,
                }"
                type="button"
                @click="onMessageFileClick(file)"
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
              </button>
            </div>
            <!-- eslint-disable vue/no-v-html -->
            <div
              v-if="normalizedDisplayContent.trim().length > 0"
              class="message-text"
              v-html="renderedContent"
            ></div>
            <!-- eslint-enable vue/no-v-html -->
          </template>
        </template>
      </div>
      <div
        v-if="message.role !== 'system'"
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
            <svg
              viewBox="0 0 16 16"
              class="message-tool-icon"
              aria-hidden="true"
            >
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
          <span class="message-version-text">
            {{ versionIndex }}/{{ versionCount }}
          </span>
          <button
            class="message-tool-btn"
            :disabled="!canGoNext || isVersionLocked"
            title="查看下一版"
            @click="$emit('next-version')"
          >
            <svg
              viewBox="0 0 16 16"
              class="message-tool-icon"
              aria-hidden="true"
            >
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
              <svg
                viewBox="0 0 16 16"
                class="message-tool-icon"
                aria-hidden="true"
              >
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
                ref="editFileInputRef"
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
              <svg
                viewBox="0 0 16 16"
                class="message-tool-icon"
                aria-hidden="true"
              >
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
              <svg
                viewBox="0 0 16 16"
                class="message-tool-icon"
                aria-hidden="true"
              >
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
          <template v-else-if="message.role === 'user'">
            <button
              class="message-tool-btn"
              :disabled="!canEdit"
              title="编辑消息"
              @click="$emit('start-edit')"
            >
              <svg
                viewBox="0 0 16 16"
                class="message-tool-icon"
                aria-hidden="true"
              >
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
              <svg
                viewBox="0 0 16 16"
                class="message-tool-icon"
                aria-hidden="true"
              >
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
              <svg
                viewBox="0 0 16 16"
                class="message-tool-icon"
                aria-hidden="true"
              >
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
              <svg
                viewBox="0 0 16 16"
                class="message-tool-icon"
                aria-hidden="true"
              >
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
              class="message-tool-btn"
              :disabled="!canDownload"
              title="下载为 Markdown"
              @click="$emit('download')"
            >
              <svg
                viewBox="0 0 16 16"
                class="message-tool-icon"
                aria-hidden="true"
              >
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
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
  watchEffect,
} from 'vue';
import type {
  ChatAttachment,
  ChatEditAttachment,
  ChatMessageDisplay,
  ChatToolStatus,
} from '../types/chat';
import { getFileTypeVisual } from '../utils/file';
import {
  getCachedRenderedContent,
  renderMarkdown,
  renderPlainText,
  setCachedRenderedContent,
  shouldUseMarkdownRendering,
} from '../utils/render-markdown';

const props = defineProps<{
  message: ChatMessageDisplay;
  cacheScopeId: string;
  isThinking?: boolean;
  isStreaming?: boolean;
  liveToolStatus?: ChatToolStatus | null;
  showVersionSwitcher?: boolean;
  versionIndex?: number;
  versionCount?: number;
  canGoPrev?: boolean;
  canGoNext?: boolean;
  canEdit?: boolean;
  canRegenerate?: boolean;
  canCopy?: boolean;
  canDownload?: boolean;
  isVersionLocked?: boolean;
  isEditing?: boolean;
  editingText?: string;
  editingFiles?: ChatEditAttachment[];
  canConfirmEdit?: boolean;
  showToolbarByDefault?: boolean;
}>();

const emit = defineEmits<{
  (e: 'prev-version'): void;
  (e: 'next-version'): void;
  (e: 'start-edit'): void;
  (e: 'update-edit-text', value: string): void;
  (e: 'upload-edit-files', files: File[]): void;
  (e: 'remove-edit-file', index: number): void;
  (e: 'cancel-edit'): void;
  (e: 'confirm-edit'): void;
  (e: 'regenerate'): void;
  (e: 'copy'): void;
  (e: 'download'): void;
  (e: 'download-file', file: ChatAttachment): void;
}>();

const renderedContent = ref('');
const editFileInputRef = ref<HTMLInputElement | null>(null);
const editTextareaRef = ref<HTMLTextAreaElement | null>(null);
const messageContentRef = ref<HTMLElement | null>(null);
const hasEnteredViewport = ref(false);
let messageViewportObserver: IntersectionObserver | null = null;

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

const formattedTime = computed(() => {
  const date = props.message.timestamp;
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
  });
});

const messageRoleMap = {
  user: '你',
  assistant: 'AI 助手',
  system: '系统',
};

const messageRole = computed(() => {
  return messageRoleMap[props.message.role] || props.message.role;
});

const avatarLabelMap = {
  user: 'U',
  assistant: 'AI',
  system: 'SYS',
} as const;

const avatarLabel = computed(() => {
  return avatarLabelMap[props.message.role] ?? props.message.role;
});

const editingFiles = computed(() => props.editingFiles ?? []);
const editingText = computed(() => props.editingText ?? '');
const isEditing = computed(() => props.isEditing ?? false);
const showVersionSwitcher = computed(() => props.showVersionSwitcher ?? false);
const showToolbarByDefault = computed(
  () => props.showToolbarByDefault ?? false,
);
const canConfirmEdit = computed(() => props.canConfirmEdit ?? false);
const toolStatuses = computed<ChatToolStatus[]>(() => {
  return props.message.toolStatuses ?? [];
});
const shouldRenderMarkdownContent = computed(() => {
  return shouldUseMarkdownRendering(
    normalizedDisplayContent.value,
    props.message.role,
  );
});

const normalizedDisplayContent = computed(() => {
  const rawContent = props.message.content;
  if (
    props.message.role !== 'assistant' ||
    (props.message.files?.length ?? 0) === 0
  ) {
    return rawContent;
  }

  const cleanedLines = rawContent.split('\n').filter((line) => {
    const normalizedLine = line.trim();
    if (!normalizedLine) {
      return true;
    }

    if (normalizedLine.includes('file://')) {
      return false;
    }

    return !(
      normalizedLine.includes('复制到浏览器') ||
      normalizedLine.includes('点击下载')
    );
  });

  return cleanedLines.join('\n').trim();
});

const hasRunningToolStatus = computed(() => {
  const lastToolStatus = toolStatuses.value[toolStatuses.value.length - 1];
  return lastToolStatus?.phase === 'start';
});

const showInlineLiveToolStatus = computed(() => {
  return props.message.role === 'assistant' && Boolean(props.liveToolStatus);
});

const showHistoricalToolStatuses = computed(() => {
  return (
    props.message.role === 'assistant' &&
    toolStatuses.value.length > 0 &&
    !(props.isStreaming ?? false)
  );
});

const isToolStatusPanelOpen = computed(() => {
  return (props.isStreaming ?? false) || hasRunningToolStatus.value;
});

const formatFallbackToolName = (toolName?: string) => {
  const normalizedToolName = toolName?.trim() ?? '';
  if (!normalizedToolName) {
    return '';
  }

  return normalizedToolName.replaceAll('_', ' ');
};

const liveToolStatusLabel = computed(() => {
  const status = props.liveToolStatus;
  if (!status) {
    return '';
  }

  return status.label || formatFallbackToolName(status.toolName) || '工具执行';
});

const liveToolStatusPhase = computed(() => {
  const status = props.liveToolStatus;
  if (!status) {
    return '';
  }

  return status.phase === 'finish' ? '已完成' : '进行中';
});

const liveToolStatusMessage = computed(() => {
  return props.liveToolStatus?.message ?? '';
});

const activateLazyMarkdownRendering = () => {
  hasEnteredViewport.value = true;
  if (messageViewportObserver) {
    messageViewportObserver.disconnect();
    messageViewportObserver = null;
  }
};

const ensureViewportObservation = () => {
  if (
    hasEnteredViewport.value ||
    !shouldRenderMarkdownContent.value ||
    isEditing.value
  ) {
    return;
  }

  if (
    showToolbarByDefault.value ||
    typeof IntersectionObserver === 'undefined' ||
    !messageContentRef.value
  ) {
    activateLazyMarkdownRendering();
    return;
  }

  if (messageViewportObserver) {
    return;
  }

  messageViewportObserver = new IntersectionObserver(
    (entries) => {
      if (entries.some((entry) => entry.isIntersecting)) {
        activateLazyMarkdownRendering();
      }
    },
    {
      root: null,
      rootMargin: '280px 0px',
      threshold: 0.01,
    },
  );

  messageViewportObserver.observe(messageContentRef.value);
};

const onEditTextInput = (event: Event) => {
  const textarea = event.target as HTMLTextAreaElement;
  textarea.style.height = 'auto';
  textarea.style.height = `${textarea.scrollHeight}px`;
  emit('update-edit-text', textarea.value);
};

const onEditFileSelect = (event: Event) => {
  const input = event.target as HTMLInputElement;
  if (input.files && input.files.length > 0) {
    emit('upload-edit-files', Array.from(input.files));
    input.value = '';
  }
};

const onMessageFileClick = (file: ChatAttachment) => {
  if (!file.attachmentId) {
    return;
  }

  emit('download-file', file);
};

const formatStatusTime = (value: string) => {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return '';
  }

  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
};

const formatToolPhase = (phase?: string) => {
  if (phase === 'start') {
    return '进行中';
  }

  if (phase === 'finish') {
    return '已完成';
  }

  return '处理中';
};

const resizeEditTextarea = () => {
  if (!editTextareaRef.value) {
    return;
  }

  editTextareaRef.value.style.height = 'auto';
  editTextareaRef.value.style.height = `${editTextareaRef.value.scrollHeight}px`;
};

watch(
  [isEditing, editingText],
  async () => {
    if (!isEditing.value) {
      return;
    }

    await nextTick();
    resizeEditTextarea();
  },
  { immediate: true },
);

watchEffect((onCleanup) => {
  let cancelled = false;
  const displayContent = normalizedDisplayContent.value;
  const currentRole = props.message.role;
  const currentCacheScopeId = props.cacheScopeId;
  const currentMessageId = props.message.id;

  if (!shouldRenderMarkdownContent.value || !hasEnteredViewport.value) {
    const plainTextContent = renderPlainText(displayContent);
    renderedContent.value = plainTextContent;

    if (!shouldRenderMarkdownContent.value) {
      setCachedRenderedContent(
        currentCacheScopeId,
        currentMessageId,
        displayContent,
        currentRole,
        plainTextContent,
      );
    }

    return;
  }

  const cachedRenderedContent = getCachedRenderedContent(
    currentCacheScopeId,
    currentMessageId,
    displayContent,
    currentRole,
  );
  if (cachedRenderedContent) {
    renderedContent.value = cachedRenderedContent;
    return;
  }

  renderMarkdown(displayContent)
    .then((renderedHtml) => {
      if (!cancelled) {
        renderedContent.value = renderedHtml;
        setCachedRenderedContent(
          currentCacheScopeId,
          currentMessageId,
          displayContent,
          currentRole,
          renderedHtml,
        );
      }
    })
    .catch(() => {
      if (!cancelled) {
        const fallbackContent = renderPlainText(displayContent);
        renderedContent.value = fallbackContent;
        setCachedRenderedContent(
          currentCacheScopeId,
          currentMessageId,
          displayContent,
          currentRole,
          fallbackContent,
        );
      }
    });

  onCleanup(() => {
    cancelled = true;
  });
});

onMounted(() => {
  ensureViewportObservation();
});

watch(
  [shouldRenderMarkdownContent, showToolbarByDefault, isEditing],
  async () => {
    await nextTick();
    ensureViewportObservation();
  },
  { immediate: true },
);

watch(
  () => props.message.content,
  async () => {
    await nextTick();
    ensureViewportObservation();
  },
  { flush: 'post' },
);

watch(messageContentRef, () => {
  ensureViewportObservation();
});

onBeforeUnmount(() => {
  if (messageViewportObserver) {
    messageViewportObserver.disconnect();
    messageViewportObserver = null;
  }
});
</script>

<style scoped src="../styles/components/chat-message.css"></style>
