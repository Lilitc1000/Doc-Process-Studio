<template>
  <transition name="toast-fade">
    <div v-if="visible" class="floating-toast">
      <div class="floating-toast-icon" aria-hidden="true">
        <svg viewBox="0 0 20 20" class="floating-toast-icon-svg">
          <path
            d="M5 10.5L8.25 13.75L15 7"
            fill="none"
            stroke="currentColor"
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
          />
        </svg>
      </div>
      <div class="floating-toast-content">
        <span class="floating-toast-title">{{ title }}</span>
        <span class="floating-toast-description">{{ message }}</span>
      </div>
    </div>
  </transition>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    visible: boolean;
    title?: string;
    message: string;
  }>(),
  {
    title: '提示',
  },
);
</script>

<style scoped>
.toast-fade-enter-active,
.toast-fade-leave-active {
  transition:
    opacity var(--transition-smooth),
    transform var(--transition-smooth),
    filter var(--transition-smooth);
}

.toast-fade-enter-from,
.toast-fade-leave-to {
  opacity: 0;
  transform: translate(-50%, -10px) scale(0.96);
  filter: blur(6px);
}

.floating-toast {
  position: fixed;
  left: 50%;
  top: 1.25rem;
  transform: translateX(-50%);
  min-width: 240px;
  display: flex;
  align-items: center;
  gap: var(--space-lg);
  padding: var(--space-lg) var(--space-lg);
  border-radius: var(--radius-xl);
  border: 1px solid rgba(255, 255, 255, 0.72);
  background: rgba(255, 255, 255, 0.92);
  color: var(--color-text-primary);
  backdrop-filter: blur(14px);
  box-shadow: var(--shadow-float);
  pointer-events: none;
  z-index: var(--z-toast);
}

.floating-toast-icon {
  width: 2rem;
  height: 2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-full);
  background: linear-gradient(135deg, var(--color-success), #22c55e);
  color: var(--color-text-inverse);
  flex-shrink: 0;
  box-shadow: 0 8px 16px rgba(22, 163, 74, 0.24);
}

.floating-toast-icon-svg {
  width: 1rem;
  height: 1rem;
}

.floating-toast-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-2xs);
}

.floating-toast-title {
  font-size: var(--text-sm);
  font-weight: var(--font-bold);
  letter-spacing: 0.01em;
}

.floating-toast-description {
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
}
</style>
