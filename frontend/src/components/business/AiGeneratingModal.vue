<template>
  <teleport to="body">
    <transition name="ai-gen-fade">
      <div v-if="visible" class="ai-gen-mask" @click.self="$emit('stop')">
        <div class="ai-gen-dialog">
          <div class="ai-gen-icon-wrap">
            <svg
              class="ai-gen-thinking-icon"
              viewBox="0 0 48 48"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <circle
                class="ai-gen-orbit ai-gen-orbit-outer"
                cx="24"
                cy="24"
                r="20"
                stroke="currentColor"
                stroke-width="2"
                stroke-dasharray="6 4"
              />
              <circle
                class="ai-gen-orbit ai-gen-orbit-inner"
                cx="24"
                cy="24"
                r="12"
                stroke="currentColor"
                stroke-width="2"
                stroke-dasharray="4 3"
              />
              <circle
                class="ai-gen-core"
                cx="24"
                cy="24"
                r="5"
                fill="currentColor"
              />
              <circle
                class="ai-gen-dot ai-gen-dot-1"
                cx="24"
                cy="4"
                r="2.5"
                fill="currentColor"
              />
              <circle
                class="ai-gen-dot ai-gen-dot-2"
                cx="24"
                cy="4"
                r="2.5"
                fill="currentColor"
              />
            </svg>
          </div>

          <div class="ai-gen-text">
            <span class="ai-gen-label">{{ label }}</span>
            <span class="ai-gen-dots">
              <span class="ai-gen-dot-anim">.</span>
              <span class="ai-gen-dot-anim">.</span>
              <span class="ai-gen-dot-anim">.</span>
            </span>
          </div>

          <base-button
            type="button"
            variant="secondary"
            size="sm"
            class="ai-gen-stop-btn"
            @click="$emit('stop')"
          >
            停止生成
          </base-button>
        </div>
      </div>
    </transition>
  </teleport>
</template>

<script setup lang="ts">
import BaseButton from '../base/BaseButton.vue';

defineProps<{
  visible: boolean;
  label?: string;
}>();

defineEmits<{
  (e: 'stop'): void;
}>();
</script>

<style scoped>
.ai-gen-mask {
  position: fixed;
  inset: 0;
  z-index: 200;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(15, 23, 42, 0.42);
  backdrop-filter: blur(4px);
}

.ai-gen-dialog {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-lg);
  padding: var(--space-2xl) var(--space-3xl);
  border-radius: var(--radius-xl);
  background: #ffffff;
  box-shadow:
    0 24px 48px rgba(15, 23, 42, 0.22),
    0 8px 16px rgba(15, 23, 42, 0.12);
  min-width: 280px;
}

.ai-gen-icon-wrap {
  width: 56px;
  height: 56px;
  color: #6366f1;
}

.ai-gen-thinking-icon {
  width: 100%;
  height: 100%;
}

.ai-gen-orbit {
  transform-origin: center;
}

.ai-gen-orbit-outer {
  animation: ai-gen-spin 3s linear infinite;
}

.ai-gen-orbit-inner {
  animation: ai-gen-spin-reverse 2s linear infinite;
}

.ai-gen-core {
  animation: ai-gen-pulse 1.6s ease-in-out infinite;
}

.ai-gen-dot-1 {
  animation: ai-gen-orbit-dot 3s linear infinite;
  transform-origin: 24px 24px;
}

.ai-gen-dot-2 {
  animation: ai-gen-orbit-dot 2s linear infinite reverse;
  transform-origin: 24px 24px;
}

@keyframes ai-gen-spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

@keyframes ai-gen-spin-reverse {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(-360deg);
  }
}

@keyframes ai-gen-pulse {
  0%,
  100% {
    opacity: 0.6;
    transform: scale(1);
  }
  50% {
    opacity: 1;
    transform: scale(1.15);
  }
}

@keyframes ai-gen-orbit-dot {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.ai-gen-text {
  display: flex;
  align-items: baseline;
  gap: var(--space-2xs);
  font-size: 1rem;
  color: #1e293b;
  font-weight: 500;
}

.ai-gen-label {
  white-space: nowrap;
}

.ai-gen-dots {
  display: inline-flex;
  gap: var(--space-2xs);
}

.ai-gen-dot-anim {
  animation: ai-gen-dot-blink 1.4s ease-in-out infinite;
}

.ai-gen-dot-anim:nth-child(2) {
  animation-delay: 0.2s;
}

.ai-gen-dot-anim:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes ai-gen-dot-blink {
  0%,
  60%,
  100% {
    opacity: 0.2;
  }
  30% {
    opacity: 1;
  }
}

.ai-gen-stop-btn,
.base-button.ai-gen-stop-btn {
  margin-top: var(--space-xs);
  border: 1px solid #e2e8f0;
  background: #ffffff;
  color: #475569;
  border-radius: var(--radius-sm);
  min-height: 2rem;
  padding: 0 1rem;
  font-size: 0.82rem;
  cursor: pointer;
  transition:
    background-color 0.18s ease,
    border-color 0.18s ease,
    color 0.18s ease;
}

.ai-gen-stop-btn:hover,
.base-button.ai-gen-stop-btn:hover {
  background: #fef2f2;
  border-color: #fca5a5;
  color: #b91c1c;
}

.ai-gen-fade-enter-active,
.ai-gen-fade-leave-active {
  transition:
    opacity 0.2s ease,
    transform 0.2s ease;
}

.ai-gen-fade-enter-from,
.ai-gen-fade-leave-to {
  opacity: 0;
  transform: scale(0.96);
}
</style>
