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
      <div class="message-content" :class="{ thinking: isThinking }">
        <div v-if="isThinking" class="thinking-state">
          <span class="thinking-spinner"></span>
          <span>思考中...</span>
        </div>
        <div v-else-if="isEditing" class="message-edit-panel">
          <div v-if="editingFiles.length > 0" class="message-edit-files">
            <div
              v-for="(file, index) in editingFiles"
              :key="`${file.name}-${file.size}-${index}`"
              class="message-edit-file-item"
            >
              <span class="message-file-icon">📄</span>
              <div class="message-edit-file-meta">
                <span class="message-file-name">{{ file.name }}</span>
                <span class="message-file-size">{{ formattedSize(file) }}</span>
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
            v-if="message.files && message.files.length > 0"
            class="message-files"
          >
            <div
              v-for="file in message.files"
              :key="`${file.name}-${file.sizeLabel}`"
              class="message-file-item"
            >
              <span class="message-file-icon">📄</span>
              <div class="message-file-meta">
                <span class="message-file-name">{{ file.name }}</span>
                <span class="message-file-size">{{ file.sizeLabel }}</span>
              </div>
            </div>
          </div>
          <!-- eslint-disable vue/no-v-html -->
          <div
            v-if="message.content.trim().length > 0"
            class="message-text"
            v-html="renderedContent"
          ></div>
          <!-- eslint-enable vue/no-v-html -->
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
import { computed, nextTick, ref, watch, watchEffect } from 'vue';

const props = defineProps<{
  message: {
    role: 'user' | 'assistant' | 'system';
    content: string;
    files?: Array<{
      name: string;
      sizeLabel: string;
    }>;
    timestamp: Date;
  };
  isThinking?: boolean;
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
  editingFiles?: File[];
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
}>();

const renderedContent = ref('');
const editFileInputRef = ref<HTMLInputElement | null>(null);
const editTextareaRef = ref<HTMLTextAreaElement | null>(null);

type RenderMarkdown = (content: string) => string;

let markdownRendererPromise: Promise<RenderMarkdown> | null = null;

const loadMarkdownRenderer = async (): Promise<RenderMarkdown> => {
  if (!markdownRendererPromise) {
    markdownRendererPromise = Promise.all([
      import('markdown-it'),
      import('highlight.js/lib/core'),
      import('highlight.js/lib/languages/javascript'),
      import('highlight.js/lib/languages/typescript'),
      import('highlight.js/lib/languages/json'),
      import('highlight.js/lib/languages/bash'),
      import('highlight.js/lib/languages/python'),
      import('highlight.js/lib/languages/xml'),
      import('highlight.js/lib/languages/css'),
      import('highlight.js/lib/languages/markdown'),
    ]).then(
      ([
        markdownItModule,
        highlightCoreModule,
        javascriptModule,
        typescriptModule,
        jsonModule,
        bashModule,
        pythonModule,
        xmlModule,
        cssModule,
        markdownModule,
      ]) => {
        const MarkdownIt = markdownItModule.default;
        const hljs = highlightCoreModule.default;

        hljs.registerLanguage('javascript', javascriptModule.default);
        hljs.registerLanguage('js', javascriptModule.default);
        hljs.registerLanguage('typescript', typescriptModule.default);
        hljs.registerLanguage('ts', typescriptModule.default);
        hljs.registerLanguage('json', jsonModule.default);
        hljs.registerLanguage('bash', bashModule.default);
        hljs.registerLanguage('shell', bashModule.default);
        hljs.registerLanguage('sh', bashModule.default);
        hljs.registerLanguage('python', pythonModule.default);
        hljs.registerLanguage('py', pythonModule.default);
        hljs.registerLanguage('xml', xmlModule.default);
        hljs.registerLanguage('html', xmlModule.default);
        hljs.registerLanguage('vue', xmlModule.default);
        hljs.registerLanguage('css', cssModule.default);
        hljs.registerLanguage('markdown', markdownModule.default);
        hljs.registerLanguage('md', markdownModule.default);

        const markdown = new MarkdownIt({
          html: false,
          xhtmlOut: false,
          breaks: true,
          linkify: true,
          typographer: true,
          langPrefix: 'language-',
          highlight: (str: string, lang: string): string => {
            if (lang) {
              try {
                return `<pre class="highlight"><code class="hljs ${lang}">${hljs.highlight(str, { language: lang }).value}</code></pre>`;
              } catch {
                // Fall back to escaped plain text when the language is unknown.
              }
            }

            return `<pre class="highlight"><code class="hljs">${markdown.utils.escapeHtml(str)}</code></pre>`;
          },
        });

        return (content: string) => markdown.render(content);
      },
    );
  }

  return markdownRendererPromise;
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

const formattedSize = (file: File) => {
  if (file.size < 1024) return `${file.size} B`;
  if (file.size < 1024 * 1024) return `${(file.size / 1024).toFixed(1)} KB`;
  return `${(file.size / (1024 * 1024)).toFixed(1)} MB`;
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
  const currentContent = props.message.content;

  loadMarkdownRenderer()
    .then((renderMarkdown) => {
      if (!cancelled) {
        renderedContent.value = renderMarkdown(currentContent);
      }
    })
    .catch(() => {
      if (!cancelled) {
        renderedContent.value = currentContent;
      }
    });

  onCleanup(() => {
    cancelled = true;
  });
});
</script>

<style scoped>
.chat-message {
  --message-track-edge-gap: 1.5rem;
  --message-track-max-width: calc(100% - (var(--message-track-edge-gap) * 2));
  --user-message-max-width: 560px;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 0.08rem;
}

.message-track {
  display: inline-grid;
  justify-items: stretch;
  gap: 0.28rem;
}

.chat-message.role-user {
  align-self: flex-end;
  align-items: flex-end;
  padding-left: max(20%, var(--message-track-edge-gap));
  padding-right: var(--message-track-edge-gap);
}

.chat-message.role-assistant {
  align-self: flex-start;
  align-items: flex-start;
  padding-inline: var(--message-track-edge-gap);
}

.chat-message.role-system {
  align-self: center;
  align-items: stretch;
  width: min(100%, 760px);
  max-width: 760px;
  color: #5b4b2f;
  margin-bottom: 0.5rem;
}

.message-header {
  box-sizing: border-box;
  display: flex;
  align-items: center;
  gap: 0.65rem;
  margin-bottom: 0.4rem;
  font-size: 0.74rem;
  color: #7a8699;
}

.avatar {
  width: 1.75rem;
  height: 1.75rem;
  border-radius: 0.85rem;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border: 1px solid transparent;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.7);
}

.avatar-user {
  background: linear-gradient(180deg, #eff6ff, #dbeafe);
  border-color: rgba(59, 130, 246, 0.2);
  color: #1d4ed8;
}

.avatar-assistant {
  background: linear-gradient(180deg, #eefbf3, #dcfce7);
  border-color: rgba(34, 197, 94, 0.2);
  color: #15803d;
}

.avatar-system {
  background: linear-gradient(180deg, #fff7ed, #ffedd5);
  border-color: rgba(249, 115, 22, 0.2);
  color: #c2410c;
}

.avatar-label {
  font-size: 0.68rem;
  font-weight: 700;
  line-height: 1;
  letter-spacing: 0.04em;
}

.message-info {
  display: flex;
  align-items: center;
  gap: 0.42rem;
  min-width: 0;
}

.message-role {
  display: inline-flex;
  align-items: center;
  padding: 0.16rem 0.52rem;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 600;
  line-height: 1;
  letter-spacing: 0.01em;
}

.chat-message.role-user .message-role {
  background: rgba(22, 121, 255, 0.12);
  color: #175cd3;
}

.chat-message.role-assistant .message-role {
  background: #eef7f1;
  color: #166534;
}

.chat-message.role-system .message-role {
  background: rgba(212, 155, 47, 0.14);
  color: #8a6115;
}

.message-meta-dot {
  display: block;
  width: 0.22rem;
  height: 0.22rem;
  border-radius: 999px;
  background: currentColor;
  opacity: 0.35;
  flex-shrink: 0;
  align-self: center;
}

.message-time {
  font-size: 0.72rem;
  letter-spacing: 0.01em;
  opacity: 0.82;
}

.message-content {
  box-sizing: border-box;
  padding: 1.05rem 1.2rem;
  border-radius: 18px;
  line-height: 1.6;
  font-size: 0.95rem;
  max-width: 100%;
  overflow: hidden;
}

.message-content.thinking {
  display: flex;
  align-items: center;
}

.message-files {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
}

.message-edit-panel {
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
}

.message-edit-files {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.message-edit-file-item {
  position: relative;
  padding-right: 2.15rem;
}

.message-file-meta,
.message-edit-file-meta {
  min-width: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.08rem;
}

.message-edit-file-remove {
  position: absolute;
  top: 0.35rem;
  right: 0.38rem;
  width: 1.1rem;
  height: 1.1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 999px;
  background: #9ca3af;
  color: white;
  font-size: 0.72rem;
  cursor: pointer;
  opacity: 0;
  transition:
    opacity 0.2s ease,
    background-color 0.2s ease;
}

.message-edit-file-item:hover .message-edit-file-remove {
  opacity: 1;
}

.message-edit-file-remove:hover {
  background: #6b7280;
}

.message-edit-textarea {
  width: 100%;
  min-height: 1.6em;
  height: 1.6em;
  padding: 0;
  border: none;
  outline: none;
  background: transparent;
  resize: none;
  overflow: hidden;
  font: inherit;
  line-height: 1.6;
  color: inherit;
}

.message-edit-textarea::placeholder {
  color: inherit;
  opacity: 0.6;
}

.message-text {
  min-width: 0;
}

.message-files + .message-text {
  margin-top: 0.85rem;
}

.message-file-item {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  width: min(100%, 250px);
  padding: 0.45rem 0.75rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.16);
}

.chat-message.role-user .message-file-item,
.message-edit-file-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
  width: min(100%, 250px);
  padding: 0.55rem 0.85rem;
  border-radius: 18px;
  border: 1px solid rgba(255, 255, 255, 0.24);
  background: rgba(255, 255, 255, 0.16);
}

.chat-message.role-assistant .message-edit-file-item {
  border-color: #dddddd;
  background: white;
}

.chat-message.role-assistant .message-file-item,
.chat-message.role-system .message-file-item {
  background: rgba(0, 0, 0, 0.05);
}

.message-file-icon {
  flex-shrink: 0;
}

.message-file-name {
  font-size: 0.84rem;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}

.message-file-size {
  font-size: 0.74rem;
  opacity: 0.8;
  flex-shrink: 0;
}

.message-file-meta {
  min-width: 0;
}

.chat-message.role-user .message-file-item .message-file-icon,
.message-edit-file-item .message-file-icon {
  margin-top: 0.1rem;
}

.chat-message.role-user .message-content {
  background: linear-gradient(135deg, #1679ff, #0f67df);
  color: white;
  border: 1px solid rgba(15, 103, 223, 0.95);
  border-bottom-right-radius: 6px;
  box-shadow: 0 14px 28px rgba(15, 103, 223, 0.18);
}

.chat-message.role-assistant .message-content {
  background: linear-gradient(180deg, #ffffff, #f8fafc);
  color: #243041;
  border: 1px solid #e2e8f0;
  border-bottom-left-radius: 6px;
  box-shadow: 0 10px 26px rgba(15, 23, 42, 0.06);
}

.thinking-state {
  display: inline-flex;
  align-items: center;
  gap: 0.6rem;
  color: #666;
  min-height: 1.5rem;
}

.thinking-spinner {
  width: 0.95rem;
  height: 0.95rem;
  border-radius: 50%;
  border: 2px solid rgba(0, 122, 204, 0.18);
  border-top-color: #007acc;
  animation: spin 0.8s linear infinite;
}

.chat-message.role-system .message-content {
  background:
    radial-gradient(
      circle at top left,
      rgba(255, 255, 255, 0.95),
      transparent 38%
    ),
    linear-gradient(135deg, #fff8e8, #f6efe1);
  color: inherit;
  border: 1px solid #eadab8;
  border-radius: 20px;
  box-shadow: 0 16px 30px rgba(163, 122, 45, 0.08);
  padding: 1.15rem 1.35rem;
}

.chat-message.role-system .message-header {
  justify-content: center;
  gap: 0.75rem;
  margin-bottom: 0.55rem;
  color: #8b6f3d;
}

.chat-message.role-system .message-role {
  font-size: 0.72rem;
  letter-spacing: 0.04em;
}

.chat-message.role-system .message-time {
  color: #b09158;
}

.chat-message.role-system .avatar {
  width: 2rem;
  height: 2rem;
  box-shadow: 0 8px 18px rgba(245, 158, 11, 0.22);
}

.chat-message.role-system .avatar-label {
  font-size: 0.64rem;
}

.chat-message.role-system .message-content :deep(h3) {
  margin: 0 0 0.7rem 0;
  font-size: 1.15rem;
  line-height: 1.25;
  color: #4d3c1e;
}

.chat-message.role-system .message-content :deep(strong) {
  color: #7a4f16;
}

.chat-message.role-system .message-content :deep(ul) {
  margin-top: 0.75rem;
}

.chat-message.role-system .message-content :deep(li) {
  margin-bottom: 0.45rem;
}

.chat-message.role-system .message-content :deep(li::marker) {
  color: #d29b2f;
}

.message-toolbar {
  box-sizing: border-box;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-top: 0.5rem;
  opacity: 0;
  pointer-events: none;
  transform: translateY(-2px);
  transition:
    opacity 0.2s ease,
    transform 0.2s ease;
}

.chat-message.role-user .message-track {
  width: fit-content;
  max-width: min(var(--user-message-max-width), var(--message-track-max-width));
  margin-left: auto;
}

.chat-message.role-user.is-editing .message-track {
  width: min(var(--user-message-max-width), var(--message-track-max-width));
}

.chat-message.role-assistant .message-track {
  width: max-content;
  min-width: min(18rem, var(--message-track-max-width));
  max-width: calc(var(--message-track-max-width) - 1.25rem);
}

.chat-message.role-system .message-track {
  width: 100%;
}

.chat-message.role-assistant .message-header {
  padding-left: 0.15rem;
}

.chat-message.role-user .message-header {
  justify-content: flex-end;
  padding-right: 0.15rem;
}

.chat-message.role-user .message-info {
  align-items: flex-end;
}

.chat-message.role-user .message-content :deep(a) {
  color: rgba(255, 255, 255, 0.96);
}

.chat-message.role-user .message-content :deep(code) {
  background: rgba(255, 255, 255, 0.15);
}

.chat-message.role-user .message-content :deep(blockquote) {
  border-left-color: rgba(255, 255, 255, 0.55);
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.92);
}

.chat-message.role-assistant .message-content :deep(blockquote) {
  background: #f8fbff;
  border-left-color: #60a5fa;
}

.chat-message.role-user.is-editing .message-content {
  backdrop-filter: blur(4px);
}

.chat-message.role-user .message-toolbar {
  justify-content: flex-end;
}

.chat-message.role-assistant .message-toolbar {
  justify-content: space-between;
}

.chat-message:hover .message-toolbar,
.chat-message.is-editing .message-toolbar,
.chat-message.toolbar-visible .message-toolbar {
  opacity: 1;
  pointer-events: auto;
  transform: translateY(0);
}

.message-toolbar.toolbar-actions-only {
  justify-content: flex-end;
}

.message-version-switcher,
.message-tool-actions {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.message-version-text {
  min-width: 2.2rem;
  text-align: center;
  font-size: 0.78rem;
  color: #666;
}

.message-tool-btn {
  min-width: 32px;
  height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(203, 213, 225, 0.9);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.92);
  color: #475569;
  cursor: pointer;
  font-size: 0.85rem;
  text-decoration: none;
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.05);
  transition:
    background 0.2s ease,
    border-color 0.2s ease,
    color 0.2s ease,
    transform 0.2s ease,
    box-shadow 0.2s ease;
}

.message-tool-btn:hover:not(:disabled) {
  background: white;
  border-color: #cbd5e1;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.1);
  transform: translateY(-1px);
}

.message-tool-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.message-tool-btn.is-cancel {
  color: #c2410c;
}

.message-tool-btn.is-confirm {
  color: #166534;
}

.message-tool-icon {
  width: 0.95rem;
  height: 0.95rem;
  flex-shrink: 0;
}

.message-edit-file-input {
  display: none;
}

.message-content :deep(p) {
  margin: 0 0 0.5rem 0;
}

.message-content :deep(p:last-child) {
  margin: 0;
}

.message-content :deep(ul),
.message-content :deep(ol) {
  margin: 0 0 0.5rem 0;
  padding-left: 1.5rem;
}

.message-content :deep(li) {
  margin-bottom: 0.25rem;
}

.message-content :deep(code) {
  font-family: 'Courier New', monospace;
  font-size: 0.85em;
  background: rgba(0, 0, 0, 0.1);
  padding: 0.2em 0.4em;
  border-radius: 3px;
}

.message-content :deep(pre) {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 1rem;
  border-radius: 6px;
  overflow-x: auto;
  margin: 0.5rem 0;
}

.message-content :deep(pre code) {
  background: transparent;
  padding: 0;
  color: inherit;
}

.message-content :deep(blockquote) {
  border-left: 4px solid #007acc;
  padding-left: 1rem;
  margin: 0.5rem 0;
  color: #555;
  background: #f9f9f9;
  padding: 0.5rem 1rem;
  border-radius: 4px;
}

.message-content :deep(a) {
  color: #007acc;
  text-decoration: none;
}

.message-content :deep(a:hover) {
  text-decoration: underline;
}

.message-content :deep(strong) {
  font-weight: 600;
}

.message-content :deep(em) {
  font-style: italic;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
