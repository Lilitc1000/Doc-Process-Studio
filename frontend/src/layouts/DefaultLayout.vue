<template>
  <div class="app-layout" role="document">
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
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useUserSettingsStore } from '@modules/settings';
import { useCatalogLoader } from '@shared/composables/useCatalogLoader';
import AppHeader from './components/AppHeader.vue';

const route = useRoute();
const router = useRouter();
const viewRef = ref<any>(null);

const userSettingsStore = useUserSettingsStore();
const { loadAvailableModels } = useCatalogLoader();

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

onMounted(async () => {
  // 用户设置（含模型偏好）的真相源在后端，且"跟着用户走"。
  // 先拉设置、再让 catalog loader 依据它挑模型，顺序不能反 ——
  // 否则 loader 会因为拿不到偏好而把选择重置成第一个可用模型。
  //
  // 本组件的 onMounted 在子路由组件之后触发，因此即使 ChatView 已经先跑过一次
  // loadAvailableModels，这里的结果仍是最终生效的那一份。
  await userSettingsStore.loadSettings();
  await loadAvailableModels();
});
</script>

<style scoped>
.app-layout {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 100dvh;
  overflow: hidden;
}

.app-layout-content {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  padding-top: var(--space-3xl);
}

.app-layout-content--home {
  padding-top: 0;
}

@media (max-width: 640px) {
  .app-layout-content {
    padding-top: var(--space-3xl);
  }
}
</style>
