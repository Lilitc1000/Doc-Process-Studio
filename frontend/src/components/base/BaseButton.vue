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
  gap: 0.4rem;
  border: 1px solid transparent;
  border-radius: 12px;
  min-height: 38px;
  padding: 0.45rem 0.72rem;
  background: #f8fafc;
  color: #334155;
  cursor: pointer;
  font: inherit;
  font-size: 0.82rem;
  line-height: 1.2;
  transition:
    background-color 0.2s ease,
    border-color 0.2s ease,
    box-shadow 0.2s ease,
    color 0.2s ease,
    transform 0.2s ease;
}

.base-button.block {
  width: 100%;
}

.base-button:focus-visible {
  outline: none;
  box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.2);
}

.base-button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
  transform: none;
}

.base-button.size-sm {
  min-height: 34px;
  padding: 0.35rem 0.62rem;
  border-radius: 10px;
  font-size: 0.78rem;
}

.base-button.size-lg {
  min-height: 42px;
  padding: 0.52rem 0.9rem;
  border-radius: 13px;
  font-size: 0.86rem;
}

.base-button.variant-primary {
  border-color: #2563eb;
  background: #2563eb;
  color: #fff;
}

.base-button.variant-primary:hover:not(:disabled) {
  border-color: #1d4ed8;
  background: #1d4ed8;
}

.base-button.variant-secondary {
  border-color: #dbe3ee;
  background: #f8fafc;
  color: #334155;
}

.base-button.variant-secondary:hover:not(:disabled) {
  border-color: #bfdbfe;
  background: #eff6ff;
  color: #1d4ed8;
}

.base-button.variant-danger {
  border-color: #fca5a5;
  background: #ef4444;
  color: #fff;
}

.base-button.variant-danger:hover:not(:disabled) {
  border-color: #f87171;
  background: #dc2626;
}

.base-button.variant-ghost {
  border-color: transparent;
  background: transparent;
  color: #475569;
}

.base-button.variant-ghost:hover:not(:disabled) {
  border-color: #dbe3ee;
  background: #f8fafc;
  color: #1d4ed8;
}
</style>
