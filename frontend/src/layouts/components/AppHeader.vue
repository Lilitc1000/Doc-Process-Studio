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
import UserMenuDropdown from '../../components/business/UserMenuDropdown.vue';
import UserProfileModal from '../../components/business/UserProfileModal.vue';
import { useAuthStore } from '../../stores/auth';
import type { PageId } from '../../stores/app';

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
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: space-between;
  pointer-events: none;
}

.app-header--sub {
  margin: 0.6rem 0.75rem;
  padding: 0.45rem 0.75rem;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(16px) saturate(180%);
  -webkit-backdrop-filter: blur(16px) saturate(180%);
  box-shadow:
    0 1px 3px rgba(15, 23, 42, 0.06),
    0 4px 16px rgba(15, 23, 42, 0.04);
  pointer-events: auto;
}

.app-header--home {
  padding: 0.75rem 1rem;
  pointer-events: none;
}

.app-header-left {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
}

.app-header-right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
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
  border-radius: 10px;
  background: transparent;
  color: #475569;
  cursor: pointer;
  transition:
    background 0.2s ease,
    color 0.2s ease;
  flex-shrink: 0;
}

.app-header-home:hover {
  background: rgba(59, 130, 246, 0.08);
  color: #2563eb;
}

.app-header-home:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.3);
  border-radius: 10px;
}

.app-header-home-icon {
  width: 1.1rem;
  height: 1.1rem;
}

.app-header-title {
  font-size: 0.85rem;
  font-weight: 650;
  color: #0f172a;
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
  padding: 0.2rem 0.45rem;
  border-radius: 8px;
  cursor: pointer;
  transition:
    color 0.2s ease,
    background 0.2s ease;
}

.app-header-title-btn:hover {
  color: #1d4ed8;
  background: rgba(59, 130, 246, 0.08);
}

.app-header-title-btn:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.3);
}

.app-header-login-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.35rem 0.85rem;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(8px);
  font-size: 0.82rem;
  font-weight: 600;
  color: #475569;
  cursor: pointer;
  transition:
    border-color 0.2s ease,
    color 0.2s ease,
    background 0.2s ease;
}

.app-header-login-btn:hover {
  border-color: #93c5fd;
  color: #2563eb;
  background: rgba(239, 246, 255, 0.9);
}
</style>
