<template>
  <div class="chat-input">
    <div class="files-preview" v-if="files.length > 0">
      <button
        v-if="showNav"
        class="nav-btn left"
        @click="scrollLeft"
        title="向左滚动"
      >
        ◀
      </button>
      <div class="files-list" ref="filesContainerRef">
        <div v-for="(file, index) in files" :key="index" class="file-item">
          <span class="file-icon">📄</span>
          <div class="file-details">
            <span class="file-name">{{ file.name }}</span>
            <span class="file-size">{{ formattedSize(file) }}</span>
          </div>
          <span
            class="remove-file-btn"
            @click.stop="$emit('remove-file', index)"
            title="移除文件"
            >✕</span
          >
        </div>
      </div>
      <button
        v-if="showNav"
        class="nav-btn right"
        @click="scrollRight"
        title="向右滚动"
      >
        ▶
      </button>
      <button
        class="remove-all-btn"
        @click="$emit('clear-all-files')"
        title="移除所有文件"
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
        @change="onFileSelectChange"
      ></textarea>

      <div class="input-actions">
        <label class="file-input-label" title="上传文件">
          <span class="action-icon">📎</span>
          <input
            type="file"
            ref="fileInputRef"
            class="file-input"
            @change="onFileSelectChange"
            :accept="accept"
            multiple
          />
        </label>

        <button
          class="send-btn"
          :class="{ disabled: !canSend }"
          @click="onSend"
          :disabled="!canSend"
          title="发送消息 (Enter)"
        >
          <span class="send-icon">📤</span>
          <span class="send-text">发送</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted } from 'vue';

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
  (e: 'send'): void;
}>();

const localText = ref('');
const textareaRef = ref<HTMLTextAreaElement | null>(null);
const fileInputRef = ref<HTMLInputElement | null>(null);

const filesContainerRef = ref<HTMLDivElement | null>(null);
const showNav = ref(false);
const updateNav = () => {
  if (filesContainerRef.value) {
    showNav.value =
      filesContainerRef.value.scrollWidth > filesContainerRef.value.clientWidth;
  }
};
watch(
  () => props.files,
  () => {
    nextTick(() => updateNav());
  },
  { immediate: true },
);
const formattedSize = (file: File) => {
  const size = file.size;
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
};

const canSend = computed(() => {
  return (localText.value.trim() || props.files.length > 0) && !props.isLoading;
});
const scrollLeft = () => {
  if (filesContainerRef.value) {
    filesContainerRef.value.scrollBy({ left: -150, behavior: 'smooth' });
  }
};
const scrollRight = () => {
  if (filesContainerRef.value) {
    filesContainerRef.value.scrollBy({ left: 150, behavior: 'smooth' });
  }
};

watch(
  () => props.text,
  (newVal) => {
    localText.value = newVal;
  },
);

const onInput = () => {
  emit('update:text', localText.value);
};

const onSend = () => {
  if (canSend.value) {
    emit('send');
  }
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

const handleDrop = (e: DragEvent) => {
  e.preventDefault();
  if (
    e.dataTransfer &&
    e.dataTransfer.files &&
    e.dataTransfer.files.length > 0
  ) {
    emit('upload-files', Array.from(e.dataTransfer.files));
  }
};

const handleDragOver = (e: DragEvent) => {
  e.preventDefault();
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
  display: flex;
  flex-wrap: nowrap;
  overflow-x: hidden;
  gap: 0.5rem;
  width: 100%;
  flex: 1 1 auto;
  scroll-behavior: smooth;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex: 0 0 auto;
  padding: 0.4rem 0.8rem;
  background: #f5f5f5;
  border-radius: 20px;
  animation: fadeIn 0.3s ease-in;
  position: relative;
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
  top: 2px;
  right: 4px;
  font-size: 0.9rem;
  color: #888;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.2s;
}
.file-item:hover .remove-file-btn {
  opacity: 1;
}

.nav-btn {
  background: #e0e0e0;
  border: none;
  border-radius: 50%;
  width: 30px;
  height: 30px;
  font-size: 1rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #333;
  transition:
    background 0.2s,
    color 0.2s;
}
.nav-btn:hover {
  background: #c0c0c0;
  color: #000;
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
