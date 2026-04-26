<template>
  <div class="rich-text-editor">
    <div class="editor-toolbar">
      <button
        type="button"
        class="toolbar-btn"
        title="加粗"
        @click="execCommand('bold')"
      >
        <strong>B</strong>
      </button>
      <button
        type="button"
        class="toolbar-btn"
        title="斜体"
        @click="execCommand('italic')"
      >
        <em>I</em>
      </button>
      <button
        type="button"
        class="toolbar-btn"
        title="下划线"
        @click="execCommand('underline')"
      >
        <u>U</u>
      </button>
      <span class="toolbar-divider" />
      <button
        type="button"
        class="toolbar-btn"
        title="无序列表"
        @click="execCommand('insertUnorderedList')"
      >
        • 列表
      </button>
      <button
        type="button"
        class="toolbar-btn"
        title="有序列表"
        @click="execCommand('insertOrderedList')"
      >
        1. 列表
      </button>
      <span class="toolbar-divider" />
      <button
        type="button"
        class="toolbar-btn"
        title="插入图片"
        @click="triggerImageUpload"
      >
        📷
      </button>
      <button
        type="button"
        class="toolbar-btn"
        title="清除格式"
        @click="execCommand('removeFormat')"
      >
        ✕
      </button>
    </div>
    <div
      ref="editorRef"
      class="editor-content"
      contenteditable
      :data-placeholder="placeholder"
      @input="handleInput"
      @blur="handleBlur"
    />
    <input
      ref="fileInputRef"
      type="file"
      accept="image/*"
      style="display: none"
      @change="handleImageUpload"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue';

const props = withDefaults(
  defineProps<{
    modelValue?: string;
    placeholder?: string;
  }>(),
  {
    modelValue: '',
    placeholder: '请输入内容...',
  },
);

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void;
}>();

const editorRef = ref<HTMLDivElement | null>(null);
const fileInputRef = ref<HTMLInputElement | null>(null);

const execCommand = (command: string) => {
  document.execCommand(command, false);
  editorRef.value?.focus();
};

const handleInput = () => {
  if (editorRef.value) {
    emit('update:modelValue', editorRef.value.innerHTML);
  }
};

const handleBlur = () => {
  if (editorRef.value) {
    emit('update:modelValue', editorRef.value.innerHTML);
  }
};

const triggerImageUpload = () => {
  fileInputRef.value?.click();
};

const handleImageUpload = (event: Event) => {
  const target = event.target as HTMLInputElement;
  const file = target.files?.[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = (e) => {
    const imgSrc = e.target?.result as string;
    document.execCommand('insertImage', false, imgSrc);
    handleInput();
  };
  reader.readAsDataURL(file);
  target.value = '';
};

onMounted(() => {
  if (editorRef.value && props.modelValue) {
    editorRef.value.innerHTML = props.modelValue;
  }
});

watch(
  () => props.modelValue,
  (newVal) => {
    if (editorRef.value && editorRef.value.innerHTML !== newVal) {
      editorRef.value.innerHTML = newVal || '';
    }
  },
);
</script>

<style scoped>
.rich-text-editor {
  border: 1px solid var(--color-border);
  border-radius: 6px;
  overflow: hidden;
}

.editor-toolbar {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 4px 8px;
  background: var(--color-bg-secondary);
  border-bottom: 1px solid var(--color-border);
  flex-wrap: wrap;
}

.toolbar-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  color: var(--color-text-secondary);
  transition: background-color 0.15s;
}

.toolbar-btn:hover {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}

.toolbar-divider {
  width: 1px;
  height: 20px;
  background: var(--color-border);
  margin: 0 4px;
}

.editor-content {
  min-height: 120px;
  max-height: 400px;
  overflow-y: auto;
  padding: 10px 12px;
  font-size: 14px;
  line-height: 1.6;
  outline: none;
  color: var(--color-text-primary);
}

.editor-content:empty::before {
  content: attr(data-placeholder);
  color: var(--color-text-tertiary);
  pointer-events: none;
}

.editor-content img {
  max-width: 100%;
  height: auto;
  border-radius: 4px;
  margin: 4px 0;
}
</style>
