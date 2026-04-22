<template>
  <div class="settings-page">
    <AppHeader page-id="settings" @go-home="$emit('go-home')" />
    <div class="settings-body">
      <div class="settings-content">
        <section class="settings-section">
          <h3 class="settings-section-title">模型配置</h3>
          <p class="settings-section-desc">
            配置对话与文档生成所使用的 AI 模型
          </p>

          <div ref="modelSelectorRef" class="selector-group">
            <label id="settings-model-label" class="selector-label"
              >聊天模型</label
            >
            <button
              type="button"
              class="selector-trigger"
              :class="{ open: isModelDropdownOpen }"
              :aria-expanded="isModelDropdownOpen"
              aria-haspopup="listbox"
              aria-labelledby="settings-model-label"
              @click="toggleModelDropdown"
              @keydown.enter.prevent="toggleModelDropdown"
              @keydown.space.prevent="toggleModelDropdown"
              @keydown.esc.prevent="closeAllDropdowns"
            >
              <span class="selector-trigger-text">{{
                appStore.selectedModel
              }}</span>
              <span class="selector-trigger-icon" aria-hidden="true">
                <svg viewBox="0 0 16 16" class="selector-trigger-icon-svg">
                  <path
                    d="M3.5 6.25L8 10.75L12.5 6.25"
                    fill="none"
                    stroke="currentColor"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                  />
                </svg>
              </span>
            </button>

            <Transition name="dropdown">
              <div
                v-if="isModelDropdownOpen"
                class="selector-dropdown"
                role="listbox"
                aria-labelledby="settings-model-label"
              >
                <button
                  v-for="model in appStore.availableModels"
                  :key="model"
                  type="button"
                  class="selector-option"
                  :class="{ active: model === appStore.selectedModel }"
                  @click="onSelectModel(model)"
                >
                  <span>{{ model }}</span>
                  <span
                    v-if="model === appStore.selectedModel"
                    class="selector-option-tag"
                  >
                    当前
                  </span>
                </button>
              </div>
            </Transition>
          </div>

          <div ref="rerankerSelectorRef" class="selector-group">
            <label id="settings-reranker-label" class="selector-label"
              >重排序模型</label
            >
            <button
              type="button"
              class="selector-trigger"
              :class="{ open: isRerankerDropdownOpen }"
              :aria-expanded="isRerankerDropdownOpen"
              aria-haspopup="listbox"
              aria-labelledby="settings-reranker-label"
              @click="toggleRerankerDropdown"
              @keydown.enter.prevent="toggleRerankerDropdown"
              @keydown.space.prevent="toggleRerankerDropdown"
              @keydown.esc.prevent="closeAllDropdowns"
            >
              <span class="selector-trigger-text">{{
                appStore.selectedRerankerModel
              }}</span>
              <span class="selector-trigger-icon" aria-hidden="true">
                <svg viewBox="0 0 16 16" class="selector-trigger-icon-svg">
                  <path
                    d="M3.5 6.25L8 10.75L12.5 6.25"
                    fill="none"
                    stroke="currentColor"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                  />
                </svg>
              </span>
            </button>

            <Transition name="dropdown">
              <div
                v-if="isRerankerDropdownOpen"
                class="selector-dropdown"
                role="listbox"
                aria-labelledby="settings-reranker-label"
              >
                <button
                  v-for="model in appStore.availableModels"
                  :key="`reranker-${model}`"
                  type="button"
                  class="selector-option"
                  :class="{ active: model === appStore.selectedRerankerModel }"
                  @click="onSelectRerankerModel(model)"
                >
                  <span>{{ model }}</span>
                  <span
                    v-if="model === appStore.selectedRerankerModel"
                    class="selector-option-tag"
                  >
                    当前
                  </span>
                </button>
              </div>
            </Transition>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useAppStore } from '../stores/app';
import AppHeader from '../components/AppHeader.vue';

defineEmits<{
  (e: 'go-home'): void;
}>();

const appStore = useAppStore();

const isModelDropdownOpen = ref(false);
const isRerankerDropdownOpen = ref(false);
const modelSelectorRef = ref<HTMLElement | null>(null);
const rerankerSelectorRef = ref<HTMLElement | null>(null);

const closeAllDropdowns = () => {
  isModelDropdownOpen.value = false;
  isRerankerDropdownOpen.value = false;
};

const toggleModelDropdown = () => {
  isModelDropdownOpen.value = !isModelDropdownOpen.value;
  if (isModelDropdownOpen.value) {
    isRerankerDropdownOpen.value = false;
  }
};

const toggleRerankerDropdown = () => {
  isRerankerDropdownOpen.value = !isRerankerDropdownOpen.value;
  if (isRerankerDropdownOpen.value) {
    isModelDropdownOpen.value = false;
  }
};

const onSelectModel = (model: string) => {
  appStore.selectedModel = model;
  if (!appStore.availableModels.includes(appStore.selectedRerankerModel)) {
    appStore.selectedRerankerModel = model;
  }
  closeAllDropdowns();
};

const onSelectRerankerModel = (model: string) => {
  appStore.selectedRerankerModel = model;
  closeAllDropdowns();
};

const handleClickOutside = (event: MouseEvent) => {
  const target = event.target as HTMLElement | null;
  if (target && !modelSelectorRef.value?.contains(target)) {
    isModelDropdownOpen.value = false;
  }
  if (target && !rerankerSelectorRef.value?.contains(target)) {
    isRerankerDropdownOpen.value = false;
  }
};

const handleWindowBlur = () => {
  closeAllDropdowns();
};

onMounted(() => {
  document.addEventListener('click', handleClickOutside);
  window.addEventListener('blur', handleWindowBlur);
});

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside);
  window.removeEventListener('blur', handleWindowBlur);
});

watch(
  () => appStore.availableModels,
  () => {
    closeAllDropdowns();
  },
);
</script>

<style scoped src="../styles/components/settings-page.css"></style>
