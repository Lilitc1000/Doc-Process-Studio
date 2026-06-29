<template>
  <header
    class="app-header"
    :class="[isHome ? 'app-header--home' : 'app-header--sub']"
  >
    <template v-if="!isHome">
      <div class="app-header-left">
        <button
          type="button"
          class="app-header-home"
          aria-label="返回首页"
          @click="$emit('go-home')"
        >
          <svg
            viewBox="0 0 24 24"
            class="app-header-home-icon"
            aria-hidden="true"
          >
            <path
              d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z"
              fill="none"
              stroke="currentColor"
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="1.8"
            />
          </svg>
        </button>
        <button
          v-if="titleClickable"
          type="button"
          class="app-header-title app-header-title-btn"
          @click="$emit('title-click')"
        >
          {{ pageTitle }}
        </button>
        <span v-else class="app-header-title">{{ pageTitle }}</span>
      </div>
    </template>
    <div class="app-header-right">
      <template v-if="authStore.isAuthenticated">
        <user-menu-dropdown
          :username="authStore.username"
          :avatar-color="authStore.avatarColor"
          @profile="showProfileModal = true"
          @logout="onLogout"
        />
      </template>
      <template v-else>
        <button
          type="button"
          class="app-header-login-btn"
          @click="router.push('/login')"
        >
          登录
        </button>
      </template>
    </div>
    <user-profile-modal
      :visible="showProfileModal"
      :user-info="authStore.userInfo"
      @close="showProfileModal = false"
    />
  </header>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import UserMenuDropdown from '@shared/components/UserMenuDropdown.vue';
import UserProfileModal from '@shared/components/UserProfileModal.vue';
import { useAuthStore } from '@modules/auth';
import type { PageId } from '@shared/stores/app';

const props = defineProps<{
  pageId: PageId;
  titleClickable?: boolean;
}>();

defineEmits<{
  (e: 'go-home'): void;
  (e: 'title-click'): void;
}>();

const router = useRouter();
const authStore = useAuthStore();
const showProfileModal = ref(false);

const isHome = computed(() => props.pageId === 'home');

const pageTitles: Record<PageId, string> = {
  home: '文档处理平台',
  chat: '对话',
  'incident-report': '事故报告',
  'knowledge-base': '知识库',
  settings: '设置',
};

const pageTitle = computed(() => pageTitles[props.pageId] ?? '');

async function onLogout() {
  await authStore.logout();
  router.push('/login');
}
</script>

<style scoped>
.app-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: var(--z-sticky);
  display: flex;
  align-items: center;
  justify-content: space-between;
  pointer-events: none;
}

.app-header--sub {
  margin: var(--space-sm) var(--space-md);
  padding: var(--space-sm) var(--space-md);
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(16px) saturate(180%);
  -webkit-backdrop-filter: blur(16px) saturate(180%);
  border: 1px solid rgba(226, 232, 240, 0.6);
  box-shadow: var(--shadow-sm);
  pointer-events: auto;
}

.app-header--home {
  padding: var(--space-md) var(--space-lg);
  pointer-events: none;
}

.app-header-left {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  min-width: 0;
}

.app-header-right {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  flex-shrink: 0;
  pointer-events: auto;
}

.app-header--home .app-header-right {
  margin-left: auto;
}

.app-header-home {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.85rem;
  height: 1.85rem;
  padding: 0;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition:
    background var(--transition-base),
    color var(--transition-base);
  flex-shrink: 0;
}

.app-header-home:hover {
  background: var(--color-primary-subtle);
  color: var(--color-primary);
}

.app-header-home:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px var(--color-primary-subtle);
  border-radius: var(--radius-sm);
}

.app-header-home-icon {
  width: 1.1rem;
  height: 1.1rem;
}

.app-header-title {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  letter-spacing: 0.01em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.app-header-title-btn {
  display: inline-flex;
  align-items: center;
  border: none;
  background: transparent;
  padding: var(--space-2xs) var(--space-sm);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition:
    color var(--transition-base),
    background var(--transition-base);
}

.app-header-title-btn:hover {
  color: var(--color-primary-hover);
  background: var(--color-primary-subtle);
}

.app-header-title-btn:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px var(--color-primary-subtle);
}

.app-header-login-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-xs) var(--space-lg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(8px);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition:
    border-color var(--transition-base),
    color var(--transition-base),
    background var(--transition-base);
}

.app-header-login-btn:hover {
  border-color: var(--color-border-focus);
  color: var(--color-primary);
  background: var(--color-primary-light);
}
</style>
