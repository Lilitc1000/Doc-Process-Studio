<template>
  <teleport to="body">
    <transition name="confirm-fade">
      <div v-if="modelValue" class="confirm-overlay" @click.self="handleCancel">
        <div class="confirm-dialog">
          <div class="confirm-header">
            <h4 class="confirm-title">{{ title }}</h4>
          </div>
          <div class="confirm-body">
            <p>{{ message }}</p>
          </div>
          <div class="confirm-footer">
            <base-button variant="secondary" size="sm" @click="handleCancel">
              <svg
                viewBox="0 0 20 20"
                width="14"
                height="14"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
              >
                <path d="M5 5L15 15M15 5L5 15" />
              </svg>
              {{ cancelText }}
            </base-button>
            <base-button
              :variant="confirmVariant"
              size="sm"
              @click="handleConfirm"
            >
              <svg
                viewBox="0 0 20 20"
                width="14"
                height="14"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path d="M4 10.5L8 14.5L16 5.5" />
              </svg>
              {{ confirmText }}
            </base-button>
          </div>
        </div>
      </div>
    </transition>
  </teleport>
</template>

<script setup lang="ts">
import BaseButton from './BaseButton.vue';

withDefaults(
  defineProps<{
    modelValue: boolean;
    title?: string;
    message?: string;
    confirmText?: string;
    cancelText?: string;
    confirmVariant?: 'primary' | 'danger';
  }>(),
  {
    title: '确认操作',
    message: '确定要执行此操作吗？',
    confirmText: '确定',
    cancelText: '取消',
    confirmVariant: 'primary',
  },
);

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void;
  (e: 'confirm'): void;
  (e: 'cancel'): void;
}>();

const handleConfirm = () => {
  emit('update:modelValue', false);
  emit('confirm');
};

const handleCancel = () => {
  emit('update:modelValue', false);
  emit('cancel');
};
</script>

<style scoped>
.confirm-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(15, 23, 42, 0.4);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: var(--z-modal);
}

.confirm-dialog {
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-modal);
  min-width: 360px;
  max-width: 480px;
  overflow: hidden;
}

.confirm-header {
  padding: var(--space-xl) var(--space-xl) 0;
}

.confirm-title {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
}

.confirm-body {
  padding: var(--space-md) var(--space-xl) var(--space-xl);
}

.confirm-body p {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  line-height: var(--leading-relaxed);
}

.confirm-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-sm);
  padding: var(--space-md) var(--space-xl);
  border-top: 1px solid var(--color-border);
  background: var(--color-bg-secondary);
}

.confirm-fade-enter-active,
.confirm-fade-leave-active {
  transition: opacity var(--transition-smooth);
}

.confirm-fade-enter-from,
.confirm-fade-leave-to {
  opacity: 0;
}
</style>
