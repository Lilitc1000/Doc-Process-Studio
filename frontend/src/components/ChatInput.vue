<template>
  <div class="chat-input">
    <div v-if="files.length > 0" class="files-preview">
      <div ref="filesContainerRef" class="files-list">
        <div v-for="(file, index) in files" :key="index" class="file-item">
          <span class="file-icon">📄</span>
          <div class="file-details">
            <span class="file-name">{{ file.name }}</span>
            <span class="file-size">{{ formattedSize(file) }}</span>
          </div>
          <span
            class="remove-file-btn"
            title="移除文件"
            @click.stop="$emit('remove-file', index)"
          >
            ✕
          </span>
        </div>
      </div>
      <button
        class="remove-all-btn"
        title="移除所有文件"
        @click="$emit('clear-all-files')"
      >
        ✕ 移除所有文件
      </button>
    </div>
    <div class="input-area">
      <textarea
        ref="textareaRef"
        v-model="localText"
        placeholder="输入消息... (支持 Markdown)"
        @input="onInput"
        @keydown="onKeydown"
      ></textarea>

      <div class="input-actions">
        <label class="file-input-label" title="上传文件">
          <svg viewBox="0 0 16 16" class="action-icon-svg" aria-hidden="true">
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
            ref="fileInputRef"
            type="file"
            class="file-input"
            :accept="accept"
            multiple
            @change="onFileSelectChange"
          />
        </label>

        <button
          class="send-btn"
          :class="{
            disabled: !canSend && !props.isLoading,
            stopping: props.isLoading,
          }"
          :disabled="!canSend && !props.isLoading"
          :title="props.isLoading ? '停止生成' : '发送消息 (Enter)'"
          @click="props.isLoading ? onStop() : onSend()"
        >
          <svg
            v-if="props.isLoading"
            viewBox="0 0 16 16"
            class="send-icon-svg"
            aria-hidden="true"
          >
            <rect
              x="4.25"
              y="4.25"
              width="7.5"
              height="7.5"
              rx="1.4"
              fill="currentColor"
            />
          </svg>
          <svg
            v-else
            viewBox="0 0 16 16"
            class="send-icon-svg"
            aria-hidden="true"
          >
            <path
              d="M13.25 2.75L7.25 13.25L6.25 8.75L1.75 7.75L13.25 2.75z"
              fill="none"
              stroke="currentColor"
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="1.4"
            />
          </svg>
          <span class="send-text">{{ props.isLoading ? '停止' : '发送' }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue';

const props = defineProps<{
  text: string;
  files: File[];
  accept?: string;
  isLoading?: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:text', value: string): void;
  (e: 'upload-files', files: File[]): void;
  (e: 'clear-all-files'): void;
  (e: 'remove-file', index: number): void;
  (e: 'send'): void;
  (e: 'stop'): void;
}>();

const localText = ref('');
const textareaRef = ref<HTMLTextAreaElement | null>(null);
const fileInputRef = ref<HTMLInputElement | null>(null);
const filesContainerRef = ref<HTMLDivElement | null>(null);
const formattedSize = (file: File) => {
  const size = file.size;
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
};

const canSend = computed(() => {
  return (localText.value.trim() || props.files.length > 0) && !props.isLoading;
});

watch(
  () => props.text,
  (newVal) => {
    localText.value = newVal;
  },
  { immediate: true },
);

const onInput = () => {
  emit('update:text', localText.value);
};

const onSend = () => {
  if (canSend.value) {
    emit('send');
  }
};

const onStop = () => {
  emit('stop');
};

const onKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    onSend();
  }
};

const onFileSelectChange = (e: Event) => {
  const input = e.target as HTMLInputElement;
  if (input.files && input.files.length > 0) {
    emit('upload-files', Array.from(input.files));
    // 清空文件选择器，允许重复选择同一文件
    input.value = '';
    // 重置 localText 以触发重新渲染
    localText.value = '';
  }
};

onMounted(() => {
  if (textareaRef.value) {
    textareaRef.value.style.height = 'auto';
    textareaRef.value.style.height = textareaRef.value.scrollHeight + 'px';
  }
});
</script>

<style scoped>
.chat-input {
  width: 100%;
  display: flex;
  flex-direction: column;
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.94), #ffffff);
  border-top: 1px solid #e2e8f0;
  padding: 1rem 1.25rem 1.2rem;
  gap: 0.75rem;
  --input-width: 600px; /* 可自行调节 */
  backdrop-filter: blur(10px);
}

.files-preview {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
  overflow: hidden;
}
.files-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
  width: min(100%, 220px);
  padding: 0.5rem 2.2rem 0.5rem 0.9rem;
  background: #f8fafc;
  border-radius: 18px;
  animation: fadeIn 0.3s ease-in;
  position: relative;
  border: 1px solid #e2e8f0;
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.04);
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.remove-file-btn {
  position: absolute;
  top: 50%;
  right: 0.45rem;
  width: 1.15rem;
  height: 1.15rem;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.72rem;
  color: #fff;
  background: #9ca3af;
  border-radius: 999px;
  cursor: pointer;
  opacity: 0;
  transform: translateY(-50%);
  transition:
    opacity 0.2s,
    background-color 0.2s;
}
.file-item:hover .remove-file-btn {
  opacity: 1;
}
.remove-file-btn:hover {
  background: #6b7280;
}

.remove-all-btn {
  margin-top: 0.5rem;
  align-self: flex-start;
  padding: 0.45rem 0.85rem;
  background: #fff5f5;
  color: #c2410c;
  border: 1px solid #fed7d7;
  border-radius: 999px;
  cursor: pointer;
  font-size: 0.85rem;
  transition:
    background-color 0.2s ease,
    border-color 0.2s ease,
    transform 0.2s ease;
}
.remove-all-btn:hover {
  background: #fee2e2;
  border-color: #fecaca;
  transform: translateY(-1px);
}

.file-icon {
  font-size: 1.25rem;
}

.file-details {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  min-width: 0;
  flex: 1;
}

.file-name {
  font-size: 0.85rem;
  color: #333;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 200px;
}

.file-size {
  font-size: 0.75rem;
  color: #666;
}

.input-area {
  display: flex;
  gap: 0.75rem;
  align-items: flex-end;
  padding: 0.78rem 0.82rem 0.82rem;
  border: 1px solid #e2e8f0;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow:
    0 18px 40px rgba(15, 23, 42, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.9);
}

textarea {
  flex: 1;
  min-height: 40px;
  max-height: 150px;
  padding: 0.35rem 0.4rem 0.25rem;
  border: none;
  border-radius: 0;
  resize: none;
  background: transparent;
  font-family: inherit;
  font-size: 0.95rem;
  line-height: 1.5;
  color: #0f172a;
}
textarea:focus {
  outline: none;
  box-shadow: none;
}

textarea::placeholder {
  color: #94a3b8;
}

.input-actions {
  display: flex;
  gap: 0.6rem;
  align-items: center;
  padding-left: 0.2rem;
}

.file-input-label {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  background: #f8fafc;
  color: #475569;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  cursor: pointer;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.04);
  transition:
    transform 0.2s ease,
    background-color 0.2s ease,
    border-color 0.2s ease,
    color 0.2s ease;
}

.file-input-label:hover {
  background: #eff6ff;
  border-color: #bfdbfe;
  color: #2563eb;
}

.file-input-label:active {
  transform: translateY(1px);
}

.action-icon-svg,
.send-icon-svg {
  width: 1.1rem;
  height: 1.1rem;
  display: block;
}

.file-input {
  display: none;
}

.send-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.48rem;
  padding: 0 1rem;
  min-width: 44px;
  height: 44px;
  background: linear-gradient(135deg, #2563eb, #1d4ed8);
  color: white;
  border: none;
  border-radius: 14px;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 600;
  box-shadow: 0 12px 24px rgba(37, 99, 235, 0.24);
  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease,
    filter 0.2s ease,
    background 0.2s ease;
}

.send-btn:hover:not(.disabled) {
  transform: translateY(-1px);
  box-shadow: 0 14px 28px rgba(37, 99, 235, 0.28);
  filter: saturate(1.05);
}

.send-btn.disabled {
  background: #cbd5e1;
  box-shadow: none;
  cursor: not-allowed;
}

.send-btn.stopping {
  background: linear-gradient(135deg, #f59e0b, #d97706);
  box-shadow: 0 12px 24px rgba(217, 119, 6, 0.22);
}

.send-btn.stopping:hover {
  transform: none;
}

.send-text {
  display: none;
}

@media (min-width: 480px) {
  .send-text {
    display: inline;
  }
}
</style>
