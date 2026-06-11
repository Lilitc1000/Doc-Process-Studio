<template>
  <input
    :value="modelValue"
    class="base-input"
    v-bind="$attrs"
    @input="
      $emit('update:modelValue', ($event.target as HTMLInputElement).value)
    "
  />
</template>

<script setup lang="ts">
defineOptions({
  inheritAttrs: false,
});

defineProps<{
  modelValue?: string;
}>();

defineEmits<{
  (e: 'update:modelValue', value: string): void;
}>();
</script>

<style scoped>
.base-input {
  width: 100%;
  min-height: 40px;
  padding: var(--space-sm) var(--space-md);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  background: var(--color-bg-primary);
  color: var(--color-text-primary);
  font: inherit;
  font-size: var(--text-sm);
  line-height: var(--leading-normal);
  transition:
    border-color var(--transition-smooth),
    box-shadow var(--transition-smooth),
    background-color var(--transition-smooth);
}

.base-input::placeholder {
  color: var(--color-text-tertiary);
}

.base-input:hover:not(:disabled):not(:focus) {
  border-color: var(--color-border-hover);
}

.base-input:focus {
  outline: none;
  border-color: var(--color-border-focus);
  box-shadow: 0 0 0 3px var(--color-primary-subtle);
}

.base-input.invalid {
  border-color: var(--color-danger);
  background: var(--color-danger-light);
}

.base-input.invalid:focus {
  box-shadow: 0 0 0 3px rgba(220, 38, 38, 0.12);
}

.base-input:disabled {
  cursor: not-allowed;
  opacity: 0.5;
  background: var(--color-bg-disabled);
}
</style>
