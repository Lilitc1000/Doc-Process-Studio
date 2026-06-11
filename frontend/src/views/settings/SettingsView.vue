<template>
  <section class="settings-page">
    <div class="settings-body">
      <div class="settings-content">
        <section class="settings-section">
          <h3 class="settings-section-title">模型配置</h3>
          <p class="settings-section-desc">
            配置文档生成与重排序所使用的 AI 模型
          </p>

          <div class="selector-group">
            <label id="settings-model-label" class="selector-label"
              >生成模型</label
            >
            <base-dropdown
              :model-value="appStore.selectedModel"
              :options="modelOptions"
              label-id="settings-model-label"
              @update:model-value="onSelectModel"
            />
          </div>

          <div class="selector-group">
            <label id="settings-reranker-label" class="selector-label"
              >重排序模型</label
            >
            <base-dropdown
              :model-value="appStore.selectedRerankerModel"
              :options="modelOptions"
              label-id="settings-reranker-label"
              @update:model-value="onSelectRerankerModel"
            />
          </div>
        </section>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useAppStore } from '../../stores/app';
import BaseDropdown from '../../components/base/BaseDropdown.vue';

const appStore = useAppStore();

const modelOptions = computed(() =>
  appStore.availableModels.map((model) => ({
    label: model,
    value: model,
  })),
);

const onSelectModel = (model: string) => {
  appStore.selectedModel = model;
  if (!appStore.availableModels.includes(appStore.selectedRerankerModel)) {
    appStore.selectedRerankerModel = model;
  }
};

const onSelectRerankerModel = (model: string) => {
  appStore.selectedRerankerModel = model;
};
</script>

<style scoped src="./styles/settings-page.css"></style>
