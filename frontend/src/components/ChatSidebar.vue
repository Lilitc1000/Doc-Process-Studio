<template>
  <aside class="chat-sidebar">
    <div class="sidebar-header">
      <h2>设置</h2>
    </div>

    <div class="sidebar-content">
      <div ref="processingModeSelectorRef" class="selector-group">
        <label id="processing-mode-label">文档处理方式</label>
        <button
          type="button"
          class="selector-trigger"
          :class="{ open: isProcessingModeOpen }"
          :aria-expanded="isProcessingModeOpen"
          aria-haspopup="listbox"
          aria-labelledby="processing-mode-label"
          :disabled="props.isLocked"
          @click="toggleProcessingModeDropdown"
          @keydown.enter.prevent="toggleProcessingModeDropdown"
          @keydown.space.prevent="toggleProcessingModeDropdown"
          @keydown.esc.prevent="closeAllDropdowns"
        >
          <span class="selector-trigger-text">
            {{ selectedProcessingMode }}
          </span>
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
              :disabled="props.isLocked"
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

      <div ref="modelSelectorRef" class="selector-group">
        <label id="model-select-label">选择模型</label>
        <button
          type="button"
          class="selector-trigger"
          :class="{ open: isModelDropdownOpen }"
          :aria-expanded="isModelDropdownOpen"
          aria-haspopup="listbox"
          aria-labelledby="model-select-label"
          :disabled="props.isLocked"
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
              :disabled="props.isLocked"
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
    </div>

    <div class="sidebar-footer">
      <button class="clear-btn" @click="$emit('clear-chat')">清空对话</button>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue';

const props = defineProps<{
  processingModes: readonly string[];
  selectedProcessingMode: string;
  models: readonly string[];
  selectedModel: string;
  messagesCount: number;
  isLocked?: boolean;
}>();

const emit = defineEmits<{
  (e: 'select-processing-mode', mode: string): void;
  (e: 'select-model', model: string): void;
  (e: 'clear-chat'): void;
}>();

const isProcessingModeOpen = ref(false);
const isModelDropdownOpen = ref(false);
const processingModeSelectorRef = ref<HTMLElement | null>(null);
const modelSelectorRef = ref<HTMLElement | null>(null);

const closeAllDropdowns = () => {
  isProcessingModeOpen.value = false;
  isModelDropdownOpen.value = false;
};

const toggleProcessingModeDropdown = () => {
  if (props.isLocked) {
    return;
  }
  isProcessingModeOpen.value = !isProcessingModeOpen.value;
  if (isProcessingModeOpen.value) {
    isModelDropdownOpen.value = false;
  }
};

const toggleModelDropdown = () => {
  if (props.isLocked) {
    return;
  }
  isModelDropdownOpen.value = !isModelDropdownOpen.value;
  if (isModelDropdownOpen.value) {
    isProcessingModeOpen.value = false;
  }
};

const onSelectProcessingMode = (mode: string) => {
  if (props.isLocked) {
    return;
  }
  emit('select-processing-mode', mode);
  closeAllDropdowns();
};

const onSelectModel = (model: string) => {
  if (props.isLocked) {
    return;
  }
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

watch(
  () => props.isLocked,
  (isLocked) => {
    if (isLocked) {
      closeAllDropdowns();
    }
  },
);
</script>

<style scoped>
.chat-sidebar {
  width: 280px;
  background: linear-gradient(
    180deg,
    rgba(248, 250, 252, 0.98),
    rgba(255, 255, 255, 0.94)
  );
  color: #0f172a;
  display: flex;
  flex-direction: column;
  min-height: 0;
  border-right: 1px solid #e2e8f0;
  backdrop-filter: blur(14px);
}

.sidebar-header {
  padding: 1.35rem 1.25rem 1rem;
  border-bottom: 1px solid #e2e8f0;
}

.sidebar-header h2 {
  margin: 0;
  font-size: 1.02rem;
  font-weight: 600;
  color: #0f172a;
  letter-spacing: 0.01em;
}

.sidebar-content {
  flex: 1;
  min-height: 0;
  padding: 1.1rem 1rem;
  overflow-y: auto;
}

.selector-group {
  position: relative;
  margin-bottom: 1.35rem;
}

.selector-group label {
  display: block;
  margin-bottom: 0.55rem;
  font-size: 0.78rem;
  font-weight: 600;
  color: #64748b;
  letter-spacing: 0.02em;
}

.selector-trigger {
  width: 100%;
  min-height: 44px;
  padding: 0.78rem 0.95rem;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.94);
  color: #0f172a;
  font-size: 0.9rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  box-shadow:
    0 10px 24px rgba(15, 23, 42, 0.05),
    inset 0 1px 0 rgba(255, 255, 255, 0.92);
  transition:
    border-color 0.2s ease,
    background 0.2s ease,
    box-shadow 0.2s ease,
    transform 0.2s ease;
}

.selector-trigger:hover {
  background: #f8fbff;
  border-color: #cbd5e1;
}

.selector-trigger:disabled {
  cursor: not-allowed;
  opacity: 0.6;
  background: #f8fafc;
  border-color: #e2e8f0;
}

.selector-trigger:focus-visible {
  outline: none;
  border-color: #93c5fd;
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.12);
}

.selector-trigger.open {
  border-color: #93c5fd;
  background: #f8fbff;
  box-shadow: 0 16px 36px rgba(59, 130, 246, 0.12);
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
  color: #475569;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  box-shadow: none;
  transition:
    transform 0.22s ease,
    background 0.22s ease,
    border-color 0.22s ease;
}

.selector-trigger-icon-svg {
  width: 0.95rem;
  height: 0.95rem;
  display: block;
}

.selector-trigger.open .selector-trigger-icon {
  transform: rotate(180deg);
  background: #eff6ff;
  border-color: #bfdbfe;
}

.selector-dropdown {
  position: absolute;
  top: calc(100% + 0.5rem);
  left: 0;
  right: 0;
  z-index: 20;
  padding: 0.45rem;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(12px);
  box-shadow:
    0 20px 40px rgba(15, 23, 42, 0.12),
    inset 0 1px 0 rgba(255, 255, 255, 0.8);
}

.selector-option {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.8rem 0.9rem;
  border: none;
  border-radius: 12px;
  background: transparent;
  color: #1e293b;
  font-size: 0.9rem;
  text-align: left;
  cursor: pointer;
  transition:
    background 0.18s ease,
    color 0.18s ease,
    transform 0.18s ease;
}

.selector-option:hover {
  background: #f8fafc;
  transform: translateX(2px);
}

.selector-option:disabled {
  cursor: not-allowed;
  opacity: 0.55;
  transform: none;
}

.selector-option.active {
  background: #eff6ff;
  color: #1d4ed8;
}

.selector-option-tag {
  padding: 0.18rem 0.45rem;
  border-radius: 999px;
  background: #dbeafe;
  color: #2563eb;
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
  border-top: 1px solid #e2e8f0;
}

.clear-btn {
  width: 100%;
  padding: 0.72rem 0.9rem;
  background: #fff7ed;
  color: #c2410c;
  border: 1px solid #fed7aa;
  border-radius: 14px;
  cursor: pointer;
  font-size: 0.88rem;
  font-weight: 600;
  transition:
    background-color 0.2s ease,
    border-color 0.2s ease,
    transform 0.2s ease;
}

.clear-btn:hover {
  background: #ffedd5;
  border-color: #fdba74;
  transform: translateY(-1px);
}
</style>
