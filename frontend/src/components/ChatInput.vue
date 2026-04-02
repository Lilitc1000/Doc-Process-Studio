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
          <span class="action-icon">📎</span>
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
          <span class="send-icon">{{ props.isLoading ? '⏹' : '📤' }}</span>
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
  background: white;
  border-top: 1px solid #e0e0e0;
  padding: 1rem;
  gap: 0.75rem;
  --input-width: 600px; /* 可自行调节 */
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
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 220px), 1fr));
  gap: 0.5rem;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
  width: 100%;
  padding: 0.5rem 2.2rem 0.5rem 0.9rem;
  background: #f5f5f5;
  border-radius: 20px;
  animation: fadeIn 0.3s ease-in;
  position: relative;
  border: 1px solid #e4e4e4;
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
  padding: 0.4rem 0.8rem;
  background: #f44336;
  color: white;
  border: none;
  border-radius: 20px;
  cursor: pointer;
  font-size: 0.85rem;
  transition: all 0.2s;
}
.remove-all-btn:hover {
  background: #d32f2f;
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
}

textarea {
  flex: 1;
  min-height: 40px;
  max-height: 150px;
  padding: 0.75rem;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  resize: none;
  font-family: inherit;
  font-size: 0.95rem;
  line-height: 1.5;
  transition: border-color 0.2s;
}
textarea:focus {
  outline: none;
  border-color: #007acc;
  box-shadow: 0 0 0 2px rgba(0, 122, 204, 0.1);
}

.input-actions {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.file-input-label {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  background: #f5f5f5;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.file-input-label:hover {
  background: #e0e0e0;
}

.file-input-label:active {
  transform: scale(0.95);
}

.action-icon {
  font-size: 1.25rem;
}

.file-input {
  display: none;
}

.send-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0 1.25rem;
  height: 40px;
  background: #007acc;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 500;
  transition: all 0.2s;
}

.send-btn:hover:not(.disabled) {
  background: #005a9e;
  transform: translateY(-1px);
}

.send-btn.disabled {
  background: #ccc;
  cursor: not-allowed;
}

.send-btn.stopping {
  background: #d97706;
}

.send-btn.stopping:hover {
  background: #b45309;
  transform: none;
}

.send-icon {
  font-size: 1.2rem;
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
