<template>
  <aside class="chat-sidebar">
    <div class="sidebar-header">
      <h2>⚙️ 设置</h2>
    </div>

    <div class="sidebar-content">
      <div class="selector-group" ref="processingModeSelectorRef">
        <label id="processing-mode-label">文档处理方式</label>
        <button
          type="button"
          class="selector-trigger"
          :class="{ open: isProcessingModeOpen }"
          :aria-expanded="isProcessingModeOpen"
          aria-haspopup="listbox"
          aria-labelledby="processing-mode-label"
          @click="toggleProcessingModeDropdown"
          @keydown.enter.prevent="toggleProcessingModeDropdown"
          @keydown.space.prevent="toggleProcessingModeDropdown"
          @keydown.esc.prevent="closeAllDropdowns"
        >
          <span class="selector-trigger-text">{{ selectedProcessingMode }}</span>
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
            v-if="isProcessingModeOpen"
            class="selector-dropdown"
            role="listbox"
            aria-labelledby="processing-mode-label"
          >
            <button
              v-for="mode in processingModes"
              :key="mode"
              type="button"
              class="selector-option"
              :class="{ active: mode === selectedProcessingMode }"
              @click="onSelectProcessingMode(mode)"
            >
              <span>{{ mode }}</span>
              <span
                v-if="mode === selectedProcessingMode"
                class="selector-option-tag"
              >
                当前
              </span>
            </button>
          </div>
        </Transition>
      </div>

      <div class="selector-group" ref="modelSelectorRef">
        <label id="model-select-label">选择模型</label>
        <button
          type="button"
          class="selector-trigger"
          :class="{ open: isModelDropdownOpen }"
          :aria-expanded="isModelDropdownOpen"
          aria-haspopup="listbox"
          aria-labelledby="model-select-label"
          @click="toggleModelDropdown"
          @keydown.enter.prevent="toggleModelDropdown"
          @keydown.space.prevent="toggleModelDropdown"
          @keydown.esc.prevent="closeAllDropdowns"
        >
          <span class="selector-trigger-text">{{ selectedModel }}</span>
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
            aria-labelledby="model-select-label"
          >
            <button
              v-for="model in models"
              :key="model"
              type="button"
              class="selector-option"
              :class="{ active: model === selectedModel }"
              @click="onSelectModel(model)"
            >
              <span>{{ model }}</span>
              <span v-if="model === selectedModel" class="selector-option-tag">
                当前
              </span>
            </button>
          </div>
        </Transition>
      </div>

      <div class="info-section">
        <h3>💡 提示</h3>
        <ul>
          <li>支持多种文档格式（PDF、Word、Excel、PPT）</li>
          <li>支持自然语言提问</li>
          <li>支持多轮对话</li>
          <li>上传文件后，AI 会自动分析内容</li>
        </ul>
      </div>

      <div class="info-section">
        <h3>📊 状态</h3>
        <p>模型：{{ selectedModel }}</p>
        <p>消息数：{{ messagesCount }}</p>
      </div>
    </div>

    <div class="sidebar-footer">
      <button class="clear-btn" @click="$emit('clear-chat')">清空对话</button>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue';

const props = defineProps<{
  models: string[];
  selectedModel: string;
  messagesCount: number;
}>();

const emit = defineEmits<{
  (e: 'select-model', model: string): void;
  (e: 'clear-chat'): void;
}>();

const processingModes = [
  '快速摘要',
  '智能问答',
  '结构化提取',
  '全文整理',
];

const selectedProcessingMode = ref(processingModes[0]);
const isProcessingModeOpen = ref(false);
const isModelDropdownOpen = ref(false);
const processingModeSelectorRef = ref<HTMLElement | null>(null);
const modelSelectorRef = ref<HTMLElement | null>(null);

const closeAllDropdowns = () => {
  isProcessingModeOpen.value = false;
  isModelDropdownOpen.value = false;
};

const toggleProcessingModeDropdown = () => {
  isProcessingModeOpen.value = !isProcessingModeOpen.value;
  if (isProcessingModeOpen.value) {
    isModelDropdownOpen.value = false;
  }
};

const toggleModelDropdown = () => {
  isModelDropdownOpen.value = !isModelDropdownOpen.value;
  if (isModelDropdownOpen.value) {
    isProcessingModeOpen.value = false;
  }
};

const onSelectProcessingMode = (mode: string) => {
  selectedProcessingMode.value = mode;
  closeAllDropdowns();
};

const onSelectModel = (model: string) => {
  emit('select-model', model);
  closeAllDropdowns();
};

const handleClickOutside = (event: MouseEvent) => {
  const target = event.target as Node | null;

  if (
    target &&
    !processingModeSelectorRef.value?.contains(target) &&
    !modelSelectorRef.value?.contains(target)
  ) {
    closeAllDropdowns();
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
</script>

<style scoped>
.chat-sidebar {
  width: 280px;
  background: #1e1e1e;
  color: #e0e0e0;
  display: flex;
  flex-direction: column;
  min-height: 0;
  border-right: 1px solid #333;
}

.sidebar-header {
  padding: 1.5rem;
  border-bottom: 1px solid #333;
}

.sidebar-header h2 {
  margin: 0;
  font-size: 1.2rem;
  font-weight: 600;
  color: #fff;
}

.sidebar-content {
  flex: 1;
  min-height: 0;
  padding: 1rem;
  overflow-y: auto;
}

.selector-group {
  position: relative;
  margin-bottom: 2rem;
}

.selector-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-size: 0.9rem;
  color: #aaa;
}

.selector-trigger {
  width: 100%;
  min-height: 44px;
  padding: 0.75rem 0.9rem;
  border: 1px solid #444;
  border-radius: 12px;
  background: #2d2d2d;
  color: #fff;
  font-size: 0.9rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  transition:
    border-color 0.2s ease,
    background 0.2s ease,
    box-shadow 0.2s ease,
    transform 0.2s ease;
}

.selector-trigger:hover {
  background: #343434;
  border-color: #555;
}

.selector-trigger:focus-visible {
  outline: none;
  border-color: #007acc;
  box-shadow: 0 0 0 3px rgba(0, 122, 204, 0.15);
}

.selector-trigger.open {
  border-color: #007acc;
  background: #32363a;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.24);
}

.selector-trigger-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.selector-trigger-icon {
  width: 2rem;
  height: 2rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border-radius: 999px;
  color: #d8f1ff;
  background: transparent;
  box-shadow: none;
  transition:
    transform 0.22s ease,
    background 0.22s ease,
    box-shadow 0.22s ease;
}

.selector-trigger-icon-svg {
  width: 0.95rem;
  height: 0.95rem;
  display: block;
}

.selector-trigger.open .selector-trigger-icon {
  transform: rotate(180deg);
  background: transparent;
  box-shadow: none;
}

.selector-dropdown {
  position: absolute;
  top: calc(100% + 0.5rem);
  left: 0;
  right: 0;
  z-index: 20;
  padding: 0.45rem;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 14px;
  background: rgba(28, 28, 28, 0.96);
  backdrop-filter: blur(12px);
  box-shadow:
    0 18px 40px rgba(0, 0, 0, 0.32),
    inset 0 1px 0 rgba(255, 255, 255, 0.04);
}

.selector-option {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.8rem 0.9rem;
  border: none;
  border-radius: 10px;
  background: transparent;
  color: #f3f3f3;
  font-size: 0.9rem;
  text-align: left;
  cursor: pointer;
  transition:
    background 0.18s ease,
    color 0.18s ease,
    transform 0.18s ease;
}

.selector-option:hover {
  background: rgba(255, 255, 255, 0.08);
  transform: translateX(2px);
}

.selector-option.active {
  background: rgba(0, 122, 204, 0.16);
  color: #cfeeff;
}

.selector-option-tag {
  padding: 0.18rem 0.45rem;
  border-radius: 999px;
  background: rgba(0, 122, 204, 0.18);
  color: #8fcfff;
  font-size: 0.72rem;
  flex-shrink: 0;
}

.dropdown-enter-active,
.dropdown-leave-active {
  transition:
    opacity 0.18s ease,
    transform 0.18s ease;
  transform-origin: top center;
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-8px) scale(0.98);
}

.info-section {
  margin-bottom: 2rem;
}

.info-section h3 {
  margin: 0 0 0.75rem 0;
  font-size: 0.9rem;
  color: #007acc;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.info-section ul {
  margin: 0;
  padding-left: 1.2rem;
  font-size: 0.85rem;
  color: #bbb;
}

.info-section li {
  margin-bottom: 0.5rem;
  line-height: 1.4;
}

.info-section p {
  margin: 0 0 0.5rem 0;
  font-size: 0.85rem;
  color: #bbb;
}

.sidebar-footer {
  padding: 1rem;
  border-top: 1px solid #333;
}

.clear-btn {
  width: 100%;
  padding: 0.6rem;
  background: #d32f2f;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.85rem;
  transition: background 0.2s;
}

.clear-btn:hover {
  background: #b71c1c;
}
</style>
