<template>
  <div ref="rootRef" class="base-dropdown">
    <button
      ref="triggerRef"
      type="button"
      class="base-dropdown-trigger"
      :class="{ open: isOpen, disabled }"
      :disabled="disabled"
      :aria-expanded="isOpen"
      aria-haspopup="listbox"
      @click="toggle"
      @keydown.enter.prevent="toggle"
      @keydown.space.prevent="toggle"
      @keydown.esc.prevent="close"
    >
      <span
        class="base-dropdown-trigger-text"
        :class="{ placeholder: !hasSelectedOption }"
      >
        {{ displayLabel }}
      </span>
      <span
        class="base-dropdown-trigger-icon"
        :class="{ open: isOpen }"
        aria-hidden="true"
      >
        <svg viewBox="0 0 16 16" class="base-dropdown-trigger-icon-svg">
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

    <!-- 面板传送到 body：
         原先面板是 absolute 定位，落在表格单元格内，会被任何设置了
         overflow: hidden/auto 的祖先（例如内容区容器）裁掉 ——
         表现为"点开只能看到列表最上面一小段"。传送到 body 后按视口坐标
         固定定位，就再也不受祖先裁剪与层级叠加的影响。 -->
    <Teleport to="body">
      <transition name="dropdown">
        <div
          v-if="isOpen"
          ref="panelRef"
          class="base-dropdown-panel"
          :style="panelStyle"
          role="listbox"
          :aria-labelledby="labelId"
        >
          <button
            v-for="option in options"
            :key="option.value"
            type="button"
            class="base-dropdown-option"
            :class="{ active: option.value === modelValue }"
            @click="onSelect(option.value)"
          >
            <span>{{ option.label }}</span>
            <span
              v-if="option.value === modelValue"
              class="base-dropdown-option-tag"
            >
              当前
            </span>
          </button>
        </div>
      </transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from 'vue';

export interface DropdownOption {
  label: string;
  value: string;
}

const props = withDefaults(
  defineProps<{
    modelValue: string;
    options: readonly DropdownOption[];
    placeholder?: string;
    disabled?: boolean;
    labelId?: string;
    panelMinWidth?: string;
  }>(),
  {
    placeholder: '请选择',
    disabled: false,
    labelId: undefined,
    panelMinWidth: undefined,
  },
);

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void;
}>();

const rootRef = ref<HTMLElement | null>(null);
const triggerRef = ref<HTMLElement | null>(null);
const panelRef = ref<HTMLElement | null>(null);
const isOpen = ref(false);
/** 传送到 body 后面板改用 fixed 定位，坐标在打开时按触发器位置计算 */
const panelStyle = ref<Record<string, string>>({});

const displayLabel = computed(() => {
  const match = props.options.find((o) => o.value === props.modelValue);
  return match ? match.label : props.placeholder;
});
const hasSelectedOption = computed(() => {
  return props.options.some((option) => option.value === props.modelValue);
});

const toggle = () => {
  if (props.disabled) return;
  isOpen.value = !isOpen.value;
};

const close = () => {
  isOpen.value = false;
};

const onSelect = (value: string) => {
  emit('update:modelValue', value);
  close();
};

/** 按触发器当前视口位置刷新面板坐标 */
const syncPanelPosition = () => {
  if (!isOpen.value) return;
  const rect = triggerRef.value?.getBoundingClientRect();
  if (!rect) return;

  const minWidth = props.panelMinWidth ? parseFloat(props.panelMinWidth) : 0;
  const width = Math.max(rect.width, Number.isFinite(minWidth) ? minWidth : 0);
  // 距离视口底部不足时向上翻转，避免面板被视口截断
  const estimatedHeight = Math.min(240, (props.options?.length ?? 0) * 44 + 16);
  const flipUp = rect.bottom + estimatedHeight + 12 > window.innerHeight;

  panelStyle.value = {
    top: flipUp
      ? `${Math.max(8, rect.top - estimatedHeight - 6)}px`
      : `${rect.bottom + 6}px`,
    left: `${rect.left}px`,
    minWidth: `${width}px`,
    maxWidth: `${Math.max(width, 220)}px`,
  };
};

const handleClickOutside = (event: MouseEvent) => {
  const target = event.target as HTMLElement | null;
  if (!target) return;
  // 面板已传送到 body，不在 rootRef 内部，要单独判断，否则点选项会先被当成"点外面"
  if (rootRef.value?.contains(target)) return;
  if (panelRef.value?.contains(target)) return;
  close();
};

const handleWindowBlur = () => {
  close();
};

onMounted(() => {
  document.addEventListener('click', handleClickOutside);
  window.addEventListener('blur', handleWindowBlur);
  // 捕获阶段：内容区自身滚动时也要跟着走
  window.addEventListener('scroll', syncPanelPosition, true);
  window.addEventListener('resize', syncPanelPosition);
});

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside);
  window.removeEventListener('blur', handleWindowBlur);
  window.removeEventListener('scroll', syncPanelPosition, true);
  window.removeEventListener('resize', syncPanelPosition);
});

watch(isOpen, (open) => {
  if (open) void nextTick(syncPanelPosition);
});

watch(
  () => props.options,
  () => {
    close();
  },
);
</script>

<style scoped>
.base-dropdown {
  position: relative;
}

.base-dropdown-trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  /* 用固定高度而不是 min-height：min-height 会被内部行盒（中文 + 0.9rem 字号）
     顶到 42px，与并排的 40px 按钮差 2px。内容是单行不换行的文字 + 图标，
     固定高度不会裁切 */
  height: 40px;
  padding: var(--space-sm) var(--space-md);
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid #e2e8f0;
  border-radius: var(--radius-md);
  font-size: 0.9rem;
  line-height: 1.2;
  color: #0f172a;
  cursor: pointer;
  box-shadow:
    0 10px 24px rgba(15, 23, 42, 0.05),
    inset 0 1px 0 rgba(255, 255, 255, 0.92);
  transition:
    border-color 0.2s ease,
    box-shadow 0.2s ease,
    background 0.2s ease;
  gap: var(--space-sm);
}

.base-dropdown-trigger:hover:not(:disabled):not(.open) {
  border-color: #cbd5e1;
  background: #f8fbff;
}

.base-dropdown-trigger:focus-visible {
  outline: none;
  border-color: #93c5fd;
  box-shadow:
    0 16px 36px rgba(59, 130, 246, 0.12),
    0 0 0 4px rgba(37, 99, 235, 0.2);
}

.base-dropdown-trigger.open {
  border-color: #93c5fd;
  background: #f8fbff;
  box-shadow: 0 16px 36px rgba(59, 130, 246, 0.12);
}

.base-dropdown-trigger.disabled {
  opacity: 0.6;
  cursor: not-allowed;
  box-shadow: none;
}

.base-dropdown-trigger-text {
  flex: 1;
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.base-dropdown-trigger-text.placeholder {
  color: #64748b;
}

.base-dropdown-trigger-icon {
  width: 1.5rem;
  height: 1.5rem;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-full);
  color: #475569;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  pointer-events: none;
  transition:
    transform 0.22s ease,
    background 0.22s ease,
    border-color 0.22s ease;
}

.base-dropdown-trigger-icon.open {
  transform: rotate(180deg);
  background: #eff6ff;
  border-color: #bfdbfe;
}

.base-dropdown-trigger-icon-svg {
  width: 0.95rem;
  height: 0.95rem;
  display: block;
}

/* 面板传送到 body，因此用 fixed + JS 计算出的视口坐标；
   z-index 要高于页面里所有固定层（顶栏 / 弹窗遮罩之下但常规内容之上）。 */
.base-dropdown-panel {
  position: fixed;
  top: 0;
  left: 0;
  z-index: 1000;
  padding: var(--space-sm);
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid #e2e8f0;
  border-radius: var(--radius-lg);
  backdrop-filter: blur(12px);
  box-shadow:
    0 20px 40px rgba(15, 23, 42, 0.12),
    inset 0 1px 0 rgba(255, 255, 255, 0.8);
  transform-origin: top center;
  will-change: transform, opacity;
  max-height: 240px;
  overflow-y: auto;
}

.base-dropdown-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-md);
  width: 100%;
  padding: var(--space-lg) var(--space-lg);
  border: none;
  border-radius: var(--radius-md);
  background: transparent;
  font-size: 0.9rem;
  color: #1e293b;
  cursor: pointer;
  text-align: left;
  transition:
    background 0.18s ease,
    color 0.18s ease,
    transform 0.18s ease;
}

.base-dropdown-option:hover {
  background-color: #f8fafc;
  transform: translateX(2px);
}

.base-dropdown-option.active {
  background-color: #eff6ff;
  color: #1d4ed8;
}

.base-dropdown-option-tag {
  padding: var(--space-2xs) var(--space-sm);
  border-radius: var(--radius-full);
  background: #dbeafe;
  color: #2563eb;
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.02em;
}

.dropdown-enter-active,
.dropdown-leave-active {
  transition:
    opacity 0.18s ease,
    transform 0.18s ease;
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
</style>
