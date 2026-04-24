<template>
  <textarea ref="textareaEl" v-bind="$attrs" class="base-textarea"></textarea>
</template>

<script setup lang="ts">
import { ref } from 'vue';

defineOptions({
  inheritAttrs: false,
});

const textareaEl = ref<HTMLTextAreaElement | null>(null);

const getTextareaEl = () => {
  return textareaEl.value;
};

defineExpose({
  getTextareaEl,
});
</script>

<style scoped>
.base-textarea {
  width: 100%;
  min-height: 90px;
  padding: 0.62rem 0.72rem;
  border-radius: 12px;
  border: 1px solid #dbe3ee;
  background: #fff;
  color: inherit;
  font: inherit;
  line-height: 1.45;
  resize: vertical;
  transition:
    border-color 0.2s ease,
    box-shadow 0.2s ease,
    background-color 0.2s ease;
}

.base-textarea:focus {
  outline: none;
  border-color: #93c5fd;
  box-shadow: 0 0 0 4px rgba(147, 197, 253, 0.35);
}

.base-textarea.invalid {
  border-color: #ef4444;
  background: #fff8f8;
}

.base-textarea:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}
</style>
