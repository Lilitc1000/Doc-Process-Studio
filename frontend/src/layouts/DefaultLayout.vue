<template>
  <div class="app-layout">
    <AppHeader
      v-if="showHeader"
      :page-id="currentPageId"
      :title-clickable="isTitleClickable"
      @go-home="onGoHome"
      @title-click="onTitleClick"
    />
    <main class="app-layout-content">
      <router-view v-slot="{ Component, route: viewRoute }">
        <Transition name="page-switch" mode="out-in">
          <component :is="Component" :key="viewRoute.fullPath" ref="viewRef" />
        </Transition>
      </router-view>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import AppHeader from './components/AppHeader.vue';

const route = useRoute();
const router = useRouter();
const viewRef = ref<any>(null);

const currentPageId = computed(() => {
  const name = route.name as string;
  if (name === 'home') return 'home';
  if (name === 'chat') return 'chat';
  if (name === 'incident-report') return 'incident-report';
  if (name === 'settings') return 'settings';
  return 'home';
});

const showHeader = computed(() => currentPageId.value !== 'home');

const isTitleClickable = computed(() => {
  if (!showHeader.value) return false;
  if (currentPageId.value === 'chat') return true;
  if (currentPageId.value === 'incident-report') {
    const child = viewRef.value?.$?.exposed ?? viewRef.value;
    if (child && typeof child.isTitleClickable === 'boolean') {
      return child.isTitleClickable;
    }
    return true;
  }
  return false;
});

const onGoHome = () => {
  const child = viewRef.value?.$?.exposed ?? viewRef.value;
  if (child && typeof child.onGoHome === 'function') {
    child.onGoHome();
  } else {
    router.push({ name: 'home' });
  }
};

const onTitleClick = () => {
  const child = viewRef.value?.$?.exposed ?? viewRef.value;
  if (child && typeof child.onHeaderTitleClick === 'function') {
    child.onHeaderTitleClick();
  }
};
</script>

<style scoped>
.app-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

.app-layout-content {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}
</style>

<style>
.page-switch-enter-active,
.page-switch-leave-active {
  transition:
    opacity 0.3s ease,
    transform 0.3s ease,
    filter 0.3s ease;
}

.page-switch-enter-from {
  opacity: 0;
  transform: translateY(14px) scale(0.98);
  filter: blur(4px);
}

.page-switch-leave-to {
  opacity: 0;
  transform: translateY(-8px) scale(0.99);
  filter: blur(3px);
}
</style>
