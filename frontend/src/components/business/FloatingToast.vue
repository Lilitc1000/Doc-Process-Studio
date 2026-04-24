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
    opacity 0.26s ease,
    transform 0.26s ease,
    filter 0.26s ease;
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
  gap: 0.8rem;
  padding: 0.85rem 1rem;
  border-radius: 18px;
  border: 1px solid rgba(255, 255, 255, 0.72);
  background: rgba(255, 255, 255, 0.92);
  color: #1f2937;
  backdrop-filter: blur(14px);
  box-shadow:
    0 18px 40px rgba(15, 23, 42, 0.14),
    0 6px 16px rgba(15, 23, 42, 0.08);
  pointer-events: none;
  z-index: 100;
}

.floating-toast-icon {
  width: 2rem;
  height: 2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: linear-gradient(135deg, #16a34a, #22c55e);
  color: #fff;
  flex-shrink: 0;
  box-shadow: 0 10px 18px rgba(34, 197, 94, 0.24);
}

.floating-toast-icon-svg {
  width: 1rem;
  height: 1rem;
}

.floating-toast-content {
  display: flex;
  flex-direction: column;
  gap: 0.08rem;
}

.floating-toast-title {
  font-size: 0.92rem;
  font-weight: 700;
  letter-spacing: 0.01em;
}

.floating-toast-description {
  font-size: 0.8rem;
  color: #5b6472;
}
</style>
