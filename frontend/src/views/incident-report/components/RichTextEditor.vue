<template>
  <div class="rich-text-editor">
    <div v-if="editor" class="editor-toolbar">
      <button
        type="button"
        class="toolbar-btn"
        :class="{ active: editor.isActive('bold') }"
        title="加粗"
        @click="editor.chain().focus().toggleBold().run()"
      >
        <strong>B</strong>
      </button>
      <button
        type="button"
        class="toolbar-btn"
        :class="{ active: editor.isActive('italic') }"
        title="斜体"
        @click="editor.chain().focus().toggleItalic().run()"
      >
        <em>I</em>
      </button>
      <button
        type="button"
        class="toolbar-btn"
        :class="{ active: editor.isActive('underline') }"
        title="下划线"
        @click="editor.chain().focus().toggleUnderline().run()"
      >
        <u>U</u>
      </button>
      <span class="toolbar-divider" />
      <button
        type="button"
        class="toolbar-btn toolbar-btn-wide"
        :class="{ active: editor.isActive('bulletList') }"
        title="无序列表"
        @click="editor.chain().focus().toggleBulletList().run()"
      >
        • 列表
      </button>
      <button
        type="button"
        class="toolbar-btn toolbar-btn-wide"
        :class="{ active: editor.isActive('orderedList') }"
        title="有序列表"
        @click="editor.chain().focus().toggleOrderedList().run()"
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
        <svg
          viewBox="0 0 20 20"
          width="14"
          height="14"
          fill="none"
          stroke="currentColor"
          stroke-width="1.5"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <rect x="2.5" y="3.5" width="15" height="13" rx="2" />
          <circle cx="7" cy="8" r="1.5" />
          <path d="M2.5 14L7 10L10 12.5L13 9.5L17.5 14" />
        </svg>
      </button>
      <button
        type="button"
        class="toolbar-btn"
        title="清除格式"
        @click="editor.chain().focus().clearNodes().unsetAllMarks().run()"
      >
        <svg
          viewBox="0 0 20 20"
          width="14"
          height="14"
          fill="none"
          stroke="currentColor"
          stroke-width="1.8"
          stroke-linecap="round"
        >
          <path d="M5 5L15 15M15 5L5 15" />
        </svg>
      </button>
    </div>
    <editor-content :editor="editor" class="editor-content" />
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
import { ref, onBeforeUnmount, watch } from 'vue';
import { useEditor, EditorContent } from '@tiptap/vue-3';
import StarterKit from '@tiptap/starter-kit';
import Underline from '@tiptap/extension-underline';
import Image from '@tiptap/extension-image';
import Placeholder from '@tiptap/extension-placeholder';

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

const fileInputRef = ref<HTMLInputElement | null>(null);

const editor = useEditor({
  extensions: [
    StarterKit,
    Underline,
    Image,
    Placeholder.configure({
      placeholder: props.placeholder,
    }),
  ],
  content: props.modelValue,
  onUpdate: ({ editor: ed }) => {
    emit('update:modelValue', ed.getHTML());
  },
});

watch(
  () => props.modelValue,
  (newVal) => {
    if (editor.value && editor.value.getHTML() !== newVal) {
      editor.value.commands.setContent(newVal || '');
    }
  },
);

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
    editor.value?.chain().focus().setImage({ src: imgSrc }).run();
  };
  reader.readAsDataURL(file);
  target.value = '';
};

onBeforeUnmount(() => {
  editor.value?.destroy();
});
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
  transition:
    background-color 0.15s,
    color 0.15s;
}

.toolbar-btn.toolbar-btn-wide {
  width: auto;
  padding: 0 8px;
  white-space: nowrap;
}

.toolbar-btn:hover {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}

.toolbar-btn.active {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
  font-weight: 600;
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
  color: var(--color-text-primary);
}

.editor-content :deep(.tiptap) {
  outline: none;
  min-height: 100px;
}

.editor-content :deep(.tiptap p.is-editor-empty:first-child::before) {
  content: attr(data-placeholder);
  color: var(--color-text-tertiary);
  pointer-events: none;
  float: left;
  height: 0;
}

.editor-content :deep(.tiptap img) {
  max-width: 100%;
  height: auto;
  border-radius: 4px;
  margin: 4px 0;
}

.editor-content :deep(.tiptap ul),
.editor-content :deep(.tiptap ol) {
  padding-left: 1.5em;
}

.editor-content :deep(.tiptap li) {
  margin: 2px 0;
}
</style>
