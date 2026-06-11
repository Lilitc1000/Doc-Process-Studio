<template>
  <textarea
    ref="textareaEl"
    :value="modelValue"
    class="base-textarea"
    v-bind="$attrs"
    @input="
      $emit('update:modelValue', ($event.target as HTMLTextAreaElement).value)
    "
  ></textarea>
</template>

<script setup lang="ts">
import { ref } from 'vue';

defineOptions({
  inheritAttrs: false,
});

defineProps<{
  modelValue?: string;
}>();

defineEmits<{
  (e: 'update:modelValue', value: string): void;
}>();

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
  padding: var(--space-sm) var(--space-md);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  background: var(--color-bg-primary);
  color: var(--color-text-primary);
  font: inherit;
  font-size: var(--text-sm);
  line-height: var(--leading-normal);
  resize: vertical;
  transition:
    border-color var(--transition-smooth),
    box-shadow var(--transition-smooth),
    background-color var(--transition-smooth);
}

.base-textarea::placeholder {
  color: var(--color-text-tertiary);
}

.base-textarea:hover:not(:disabled):not(:focus) {
  border-color: var(--color-border-hover);
}

.base-textarea:focus {
  outline: none;
  border-color: var(--color-border-focus);
  box-shadow: 0 0 0 3px var(--color-primary-subtle);
}

.base-textarea.invalid {
  border-color: var(--color-danger);
  background: var(--color-danger-light);
}

.base-textarea.invalid:focus {
  box-shadow: 0 0 0 3px rgba(220, 38, 38, 0.12);
}

.base-textarea:disabled {
  cursor: not-allowed;
  opacity: 0.5;
  background: var(--color-bg-disabled);
}
</style>
