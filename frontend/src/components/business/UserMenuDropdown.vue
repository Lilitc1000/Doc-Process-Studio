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
    box-shadow 0.2s ease,
    transform 0.2s ease;
}

.user-menu-trigger:hover,
.base-button.user-menu-trigger:hover:not(:disabled) {
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.2);
  transform: scale(1.05);
}

.user-menu-panel {
  position: absolute;
  top: calc(100% + 0.5rem);
  right: 0;
  z-index: 9999;
  min-width: 160px;
  padding: 0.35rem;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  backdrop-filter: blur(12px);
  box-shadow:
    0 10px 24px rgba(15, 23, 42, 0.1),
    inset 0 1px 0 rgba(255, 255, 255, 0.8);
}

.user-menu-item,
.base-button.user-menu-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  padding: 0.55rem 0.75rem;
  border: none;
  border-radius: 8px;
  background: transparent;
  font-size: 0.85rem;
  color: #1e293b;
  cursor: pointer;
  text-align: left;
  transition:
    background 0.18s ease,
    color 0.18s ease;
}

.user-menu-item:hover,
.base-button.user-menu-item:hover:not(:disabled) {
  background: #f8fafc;
}

.user-menu-item-danger:hover,
.base-button.user-menu-item-danger:hover:not(:disabled) {
  background: #fef2f2;
  color: #dc2626;
}

.user-menu-item-icon {
  font-size: 0.9rem;
}

.user-menu-divider {
  height: 1px;
  background: #e2e8f0;
  margin: 0.25rem 0.5rem;
}
</style>
