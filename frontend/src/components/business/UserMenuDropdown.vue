<template>
  <div ref="dropdownRef" class="user-menu-dropdown">
    <base-button
      type="button"
      class="user-menu-trigger"
      variant="ghost"
      size="sm"
      @click="toggle"
      @keydown.esc.prevent="close"
    >
      <user-avatar :username="username" :color="avatarColor" size="md" />
    </base-button>
    <Transition name="fade-slide-up">
      <div v-if="isOpen" class="user-menu-panel">
        <base-button
          type="button"
          class="user-menu-item"
          variant="ghost"
          @click="onProfileClick"
        >
          <span class="user-menu-item-icon">👤</span>
          <span>用户信息</span>
        </base-button>
        <div class="user-menu-divider" />
        <base-button
          type="button"
          class="user-menu-item user-menu-item-danger"
          variant="ghost"
          @click="onLogoutClick"
        >
          <span class="user-menu-item-icon">🚪</span>
          <span>退出登录</span>
        </base-button>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue';
import BaseButton from '../base/BaseButton.vue';
import UserAvatar from './UserAvatar.vue';

defineProps<{
  username: string;
  avatarColor: string;
}>();

const emit = defineEmits<{
  (e: 'profile'): void;
  (e: 'logout'): void;
}>();

const dropdownRef = ref<HTMLElement | null>(null);
const isOpen = ref(false);

const toggle = () => {
  isOpen.value = !isOpen.value;
};

const close = () => {
  isOpen.value = false;
};

const onProfileClick = () => {
  close();
  emit('profile');
};

const onLogoutClick = () => {
  close();
  emit('logout');
};

const handleClickOutside = (event: MouseEvent) => {
  const target = event.target as HTMLElement | null;
  if (target && !dropdownRef.value?.contains(target)) {
    close();
  }
};

onMounted(() => {
  document.addEventListener('click', handleClickOutside);
});

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside);
});
</script>

<style scoped>
.user-menu-dropdown {
  position: relative;
}

.user-menu-trigger,
.base-button.user-menu-trigger {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  cursor: pointer;
  padding: 0;
  border-radius: 50%;
  transition:
    box-shadow var(--transition-smooth),
    transform var(--transition-smooth);
}

.user-menu-trigger:hover,
.base-button.user-menu-trigger:hover:not(:disabled) {
  box-shadow: 0 0 0 3px var(--color-primary-subtle);
  transform: scale(1.05);
}

.user-menu-panel {
  position: absolute;
  top: calc(100% + 0.5rem);
  right: 0;
  z-index: var(--z-dropdown);
  min-width: 160px;
  padding: var(--space-xs);
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  backdrop-filter: blur(12px);
  box-shadow: var(--shadow-float);
}

.user-menu-item,
.base-button.user-menu-item {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  width: 100%;
  padding: var(--space-sm) var(--space-md);
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  cursor: pointer;
  text-align: left;
  transition:
    background var(--transition-base),
    color var(--transition-base);
}

.user-menu-item:hover,
.base-button.user-menu-item:hover:not(:disabled) {
  background: var(--color-bg-hover);
}

.user-menu-item-danger:hover,
.base-button.user-menu-item-danger:hover:not(:disabled) {
  background: var(--color-danger-light);
  color: var(--color-danger);
}

.user-menu-item-icon {
  font-size: 0.9rem;
}

.user-menu-divider {
  height: 1px;
  background: var(--color-border);
  margin: var(--space-xs) var(--space-sm);
}
</style>
