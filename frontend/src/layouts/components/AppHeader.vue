<template>
  <header class="app-header">
    <base-button
      type="button"
      class="app-header-home"
      variant="ghost"
      size="sm"
      @click="$emit('go-home')"
    >
      <svg viewBox="0 0 24 24" class="app-header-home-icon" aria-hidden="true">
        <path
          d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z"
          fill="none"
          stroke="currentColor"
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="1.8"
        />
      </svg>
    </base-button>
    <base-button
      v-if="titleClickable"
      type="button"
      class="app-header-title app-header-title-btn"
      variant="ghost"
      size="sm"
      @click="$emit('title-click')"
    >
      {{ pageTitle }}
    </base-button>
    <span v-else class="app-header-title">{{ pageTitle }}</span>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import BaseButton from '../../components/base/BaseButton.vue';
import type { PageId } from '../../stores/app';

const props = defineProps<{
  pageId: PageId;
  titleClickable?: boolean;
}>();

defineEmits<{
  (e: 'go-home'): void;
  (e: 'title-click'): void;
}>();

const pageTitles: Record<PageId, string> = {
  home: '文档处理平台',
  chat: '对话',
  'incident-report': '事故报告',
  settings: '设置',
};

const pageTitle = computed(() => pageTitles[props.pageId] ?? '');
</script>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  padding: 0.7rem 1.15rem;
  border-bottom: 1px solid #e2e8f0;
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(12px);
  flex-shrink: 0;
}

.app-header-home,
.base-button.app-header-home {
  min-width: 2.2rem;
  min-height: 2.2rem;
  width: 2.2rem;
  height: 2.2rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  gap: 0;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: #fff;
  color: #475569;
  cursor: pointer;
  transition:
    border-color 0.2s ease,
    background 0.2s ease,
    color 0.2s ease,
    transform 0.2s ease;
}

.app-header-home:hover,
.base-button.app-header-home:hover:not(:disabled) {
  border-color: #93c5fd;
  background: #eff6ff;
  color: #2563eb;
  transform: translateY(-1px);
}

.app-header-home-icon {
  width: 1.15rem;
  height: 1.15rem;
}

.app-header-title {
  font-size: 0.95rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: 0.01em;
}

.app-header-title-btn,
.base-button.app-header-title-btn {
  min-height: 0;
  border: none;
  background: transparent;
  padding: 0.25rem 0.4rem;
  border-radius: 10px;
  cursor: pointer;
  transition:
    color 0.2s ease,
    background 0.2s ease;
}

.app-header-title-btn:hover,
.base-button.app-header-title-btn:hover:not(:disabled) {
  color: #1d4ed8;
  background: #eff6ff;
}

.app-header-title-btn:focus-visible,
.base-button.app-header-title-btn:focus-visible {
  outline: none;
  color: #1d4ed8;
  background: #eff6ff;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.2);
}
</style>
