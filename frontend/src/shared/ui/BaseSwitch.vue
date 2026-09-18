<template>
  <button
    type="button"
    role="switch"
    :aria-checked="modelValue ? 'true' : 'false'"
    :disabled="disabled"
    class="base-switch"
    :class="{ 'base-switch--on': modelValue }"
    @click="toggle"
  >
    <span class="base-switch-track" aria-hidden="true">
      <span class="base-switch-thumb"></span>
    </span>
    <span v-if="label" class="base-switch-label">{{ label }}</span>
  </button>
</template>

<script setup lang="ts">
defineOptions({
  inheritAttrs: false,
});

const props = withDefaults(
  defineProps<{
    modelValue: boolean;
    label?: string;
    disabled?: boolean;
  }>(),
  {
    label: '',
    disabled: false,
  },
);

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void;
}>();

const toggle = () => {
  if (props.disabled) return;
  emit('update:modelValue', !props.modelValue);
};
</script>

<style scoped>
.base-switch {
  display: inline-flex;
  align-items: center;
  gap: var(--space-sm);
  padding: 0;
  border: none;
  background: transparent;
  cursor: pointer;
  font: inherit;
}

.base-switch:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.base-switch-track {
  position: relative;
  width: 2.5rem;
  height: 1.375rem;
  border-radius: var(--radius-full);
  border: 1px solid var(--color-border);
  background: var(--color-bg-tertiary);
  transition:
    background-color var(--transition-smooth),
    border-color var(--transition-smooth);
}

.base-switch-thumb {
  position: absolute;
  top: 50%;
  left: 2px;
  width: 1rem;
  height: 1rem;
  border-radius: var(--radius-full);
  background: var(--color-bg-primary);
  box-shadow: var(--shadow-xs);
  transform: translateY(-50%);
  transition: transform var(--transition-smooth);
}

.base-switch--on .base-switch-track {
  border-color: var(--color-primary);
  background: var(--color-primary);
}

.base-switch--on .base-switch-thumb {
  transform: translate(1.125rem, -50%);
}

.base-switch:focus-visible .base-switch-track {
  outline: none;
  border-color: var(--color-border-focus);
  box-shadow: 0 0 0 3px var(--color-primary-subtle);
}

.base-switch-label {
  font-size: var(--text-sm);
  color: var(--color-text-primary);
}
</style>
