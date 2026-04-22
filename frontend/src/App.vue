<template>
  <Transition name="page-switch" mode="out-in">
    <HomePage
      v-if="appStore.activePageId === 'home'"
      key="home"
      @navigate="onNavigate"
    />
    <ChatPage
      v-else-if="appStore.activePageId === 'chat'"
      key="chat"
      @go-home="onGoHome"
    />
    <IncidentReportPage
      v-else-if="appStore.activePageId === 'incident-report'"
      key="incident-report"
    />
    <SettingsPage
      v-else-if="appStore.activePageId === 'settings'"
      key="settings"
      @go-home="onGoHome"
    />
  </Transition>
</template>

<script setup lang="ts">
import { useAppStore } from './stores/app';
import type { PageId } from './stores/app';
import ChatPage from './pages/ChatPage.vue';
import HomePage from './pages/HomePage.vue';
import IncidentReportPage from './pages/IncidentReportPage.vue';
import SettingsPage from './pages/SettingsPage.vue';

const appStore = useAppStore();

const onNavigate = (pageId: PageId) => {
  appStore.activePageId = pageId;
};

const onGoHome = () => {
  appStore.activePageId = 'home';
};
</script>

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
