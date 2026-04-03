<template>
  <div class="chat-input">
    <div v-if="files.length > 0" class="files-preview">
      <div ref="filesContainerRef" class="files-list">
        <div v-for="(file, index) in files" :key="index" class="file-item">
          <span class="file-icon">📄</span>
          <div class="file-details">
            <span class="file-name">{{ file.name }}</span>
            <span class="file-size">{{ formatFileSize(file) }}</span>
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
import { computed, onMounted, ref, watch } from 'vue';
import { formatFileSize } from '../utils/file';

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

const resizeTextarea = () => {
  if (!textareaRef.value) {
    return;
  }

  textareaRef.value.style.height = 'auto';
  textareaRef.value.style.height = `${textareaRef.value.scrollHeight}px`;
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
  resizeTextarea();
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
  }
};

watch(localText, () => {
  resizeTextarea();
});

onMounted(() => {
  resizeTextarea();
});
</script>

<style scoped src="../styles/components/chat-input.css"></style>
