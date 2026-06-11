<template>
  <div class="app-layout">
    <app-header
      :page-id="currentPageId"
      :title-clickable="isTitleClickable"
      @go-home="onGoHome"
      @title-click="onTitleClick"
    />
    <main
      class="app-layout-content"
      :class="{ 'app-layout-content--home': currentPageId === 'home' }"
    >
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
  if (name?.startsWith('incident-report')) return 'incident-report';
  if (name?.startsWith('knowledge-base')) return 'knowledge-base';
  if (name === 'settings') return 'settings';
  return 'home';
});

const isTitleClickable = computed(() => {
  if (currentPageId.value === 'home') return false;
  if (currentPageId.value === 'chat') return true;
  if (currentPageId.value === 'incident-report') {
    if (route.name === 'incident-report-list') return false;
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
  } else if (currentPageId.value === 'incident-report') {
    router.push({ name: 'incident-report-list' });
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
  padding-top: 3rem;
}

.app-layout-content--home {
  padding-top: 0;
}

@media (max-width: 640px) {
  .app-layout-content {
    padding-top: 2.75rem;
  }
}
</style>
