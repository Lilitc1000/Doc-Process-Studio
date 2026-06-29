<template>
  <button
    class="base-button"
    :class="[`variant-${variant}`, `size-${size}`, { block }]"
    v-bind="$attrs"
  >
    <slot />
  </button>
</template>

<script setup lang="ts">
defineOptions({
  inheritAttrs: false,
});

withDefaults(
  defineProps<{
    variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
    size?: 'sm' | 'md' | 'lg';
    block?: boolean;
  }>(),
  {
    variant: 'secondary',
    size: 'md',
    block: false,
  },
);
</script>

<style scoped>
.base-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-sm);
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  min-height: 38px;
  padding: var(--space-sm) var(--space-md);
  background: var(--color-bg-secondary);
  color: var(--color-text-primary);
  cursor: pointer;
  font: inherit;
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  line-height: 1.2;
  transition:
    background-color var(--transition-smooth),
    border-color var(--transition-smooth),
    box-shadow var(--transition-smooth),
    color var(--transition-smooth),
    transform var(--transition-fast);
}

.base-button.block {
  width: 100%;
}

.base-button:focus-visible {
  outline: none;
  box-shadow:
    0 0 0 3px var(--color-primary-subtle),
    0 0 0 1px var(--color-primary);
}

.base-button:active:not(:disabled) {
  transform: scale(0.97);
}

.base-button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
  transform: none;
}

.base-button.size-sm {
  min-height: 32px;
  padding: var(--space-xs) var(--space-sm);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
}

.base-button.size-lg {
  min-height: 44px;
  padding: var(--space-sm) var(--space-lg);
  border-radius: var(--radius-lg);
  font-size: var(--text-base);
}

.base-button.variant-primary {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  box-shadow: var(--shadow-primary);
}

.base-button.variant-primary:hover:not(:disabled) {
  border-color: var(--color-primary-hover);
  background: var(--color-primary-hover);
  box-shadow: var(--shadow-primary-hover);
}

.base-button.variant-primary:active:not(:disabled) {
  background: #1e40af;
  border-color: #1e40af;
}

.base-button.variant-secondary {
  border-color: var(--color-border);
  background: var(--color-bg-primary);
  color: var(--color-text-primary);
}

.base-button.variant-secondary:hover:not(:disabled) {
  border-color: var(--color-border-hover);
  background: var(--color-bg-secondary);
}

.base-button.variant-secondary:active:not(:disabled) {
  background: var(--color-bg-tertiary);
}

.base-button.variant-danger {
  border-color: var(--color-danger);
  background: var(--color-danger);
  color: var(--color-text-inverse);
}

.base-button.variant-danger:hover:not(:disabled) {
  background: #b91c1c;
  border-color: #b91c1c;
}

.base-button.variant-danger:active:not(:disabled) {
  background: #991b1b;
  border-color: #991b1b;
}

.base-button.variant-ghost {
  border-color: transparent;
  background: transparent;
  color: var(--color-text-secondary);
}

.base-button.variant-ghost:hover:not(:disabled) {
  background: var(--color-bg-hover);
  color: var(--color-primary);
}

.base-button.variant-ghost:active:not(:disabled) {
  background: var(--color-bg-tertiary);
}
</style>
