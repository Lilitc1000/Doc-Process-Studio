<template>
  <header class="app-header">
    <button type="button" class="app-header-home" @click="$emit('go-home')">
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
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { PageId } from '../stores/app';

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

<style scoped src="../styles/components/app-header.css"></style>
