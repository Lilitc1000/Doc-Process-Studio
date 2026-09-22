<template>
  <div class="rich-text-editor">
    <div v-if="editor" class="editor-toolbar">
      <button
        type="button"
        class="toolbar-btn"
        :class="{ active: activeMarks.bold }"
        title="加粗"
        @click="editor.chain().focus().toggleBold().run()"
      >
        <strong>B</strong>
      </button>
      <button
        type="button"
        class="toolbar-btn"
        :class="{ active: activeMarks.italic }"
        title="斜体"
        @click="editor.chain().focus().toggleItalic().run()"
      >
        <em>I</em>
      </button>
      <button
        type="button"
        class="toolbar-btn"
        :class="{ active: activeMarks.underline }"
        title="下划线"
        @click="editor.chain().focus().toggleUnderline().run()"
      >
        <u>U</u>
      </button>
      <span class="toolbar-divider" />
      <button
        type="button"
        class="toolbar-btn toolbar-btn-wide"
        :class="{ active: activeMarks.bulletList }"
        title="无序列表"
        @click="editor.chain().focus().toggleBulletList().run()"
      >
        • 列表
      </button>
      <button
        type="button"
        class="toolbar-btn toolbar-btn-wide"
        :class="{ active: activeMarks.orderedList }"
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

/**
 * 工具栏激活态。
 *
 * 原先直接在模板里写 `editor.isActive('bold')`：useEditor 返回的是同一个
 * 编辑器实例引用，引用不变就意味着 Vue 不会重新渲染，于是按钮状态只在
 * 首次渲染时求值一次并就此卡住 —— 表现为"加粗按钮莫名常亮"，
 * 看上去像"点一下就自动切换了加粗"，其实文本内容并没有被加粗。
 * 这里改成用编辑器事件驱动一个响应式对象。
 */
const activeMarks = ref({
  bold: false,
  italic: false,
  underline: false,
  bulletList: false,
  orderedList: false,
});

const syncActiveMarks = () => {
  const ed = editor.value;
  if (!ed) return;
  activeMarks.value = {
    bold: ed.isActive('bold'),
    italic: ed.isActive('italic'),
    underline: ed.isActive('underline'),
    bulletList: ed.isActive('bulletList'),
    orderedList: ed.isActive('orderedList'),
  };
};

const editor = useEditor({
  extensions: [
    StarterKit,
    Image.configure({ allowBase64: true }),
    Placeholder.configure({
      placeholder: props.placeholder,
    }),
  ],
  content: props.modelValue,
  onUpdate: ({ editor: ed }) => {
    emit('update:modelValue', ed.getHTML());
    syncActiveMarks();
  },
  onTransaction: syncActiveMarks,
  onSelectionUpdate: syncActiveMarks,
  onFocus: syncActiveMarks,
  onBlur: syncActiveMarks,
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
  border-radius: var(--radius-sm);
  overflow: hidden;
  transition:
    border-color 0.15s ease,
    box-shadow 0.15s ease;
}

/* 聚焦反馈交给外层容器表达。
   原先编辑区内部的 contenteditable 会命中全局 `:focus-visible`（蓝色光圈 + 圆角），
   看起来就像"编辑器莫名多了一圈蓝框"。 */
.rich-text-editor:focus-within {
  border-color: var(--color-primary);
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
  padding: 12px 14px;
  font-size: 14px;
  line-height: 1.6;
  color: var(--color-text-primary);
}

.editor-content :deep(.tiptap) {
  outline: none;
  min-height: 100px;
  /* contenteditable 上的光标：默认光标会让人以为这里不可编辑 */
  cursor: text;
}

/* 显式关掉全局 :focus-visible 的蓝色光圈，由外层容器统一表达聚焦 */
.editor-content :deep(.tiptap:focus),
.editor-content :deep(.tiptap:focus-visible) {
  outline: none;
  box-shadow: none;
}

/* 段落默认外边距（约 1em）会让一次 Enter 看起来像"空出了一整行" */
.editor-content :deep(.tiptap p) {
  margin: 0;
}

/* 选中图片等节点时，ProseMirror 默认给一圈亮蓝轮廓，换成主色更协调 */
.editor-content :deep(.tiptap .ProseMirror-selectednode) {
  outline: 2px solid var(--color-primary);
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
