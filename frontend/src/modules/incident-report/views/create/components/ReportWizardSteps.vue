<template>
  <div class="wizard-steps">
    <div
      v-for="(step, index) in steps"
      :key="step.key"
      :class="[
        'wizard-step',
        {
          active: currentStep === index,
          completed: currentStep > index,
          clickable: canJumpTo(index),
        },
      ]"
      :aria-current="currentStep === index ? 'step' : undefined"
      @click="jumpTo(index)"
    >
      <span class="step-number">
        <svg
          v-if="currentStep > index"
          class="step-check"
          viewBox="0 0 16 16"
          aria-hidden="true"
        >
          <path
            d="M13 4.5 6.5 11 3 7.5"
            fill="none"
            stroke="currentColor"
            stroke-width="2.2"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
        <template v-else>{{ index + 1 }}</template>
      </span>
      <span class="step-label">{{ step.label }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
// steps 用 readonly：两个向导页的步骤常量都是 as const 的只读数组
const props = defineProps<{
  steps: readonly { readonly key: string; readonly label: string }[];
  currentStep: number;
}>();

const emit = defineEmits<{
  (e: 'go-to-step', index: number): void;
}>();

/**
 * 可跳转规则与原先两个向导页内联实现保持一致：
 * 可回退到任意已完成的步骤，也可前进到紧邻的下一步。
 */
function canJumpTo(index: number): boolean {
  return props.currentStep > index || props.currentStep === index - 1;
}

function jumpTo(index: number) {
  if (canJumpTo(index)) emit('go-to-step', index);
}
</script>

<style scoped>
/* 步骤条状态设计：
   未完成 —— 灰边框空心圆 + 灰字，安静地待命
   已完成 —— 主色浅底圆 + 对勾，可点击回退，主色文字
   当前   —— 主色实心圆 + 白字，主色浅底胶囊 + 描边，视觉重心落在这里
   原先的问题是 active 用主色实心底、圆却用半透明白，数字与圆形对比度不足；
   非 active 的圆又是浅灰，与容器底色几乎融为一体。 */
.wizard-steps {
  display: flex;
  gap: var(--space-2xs);
  margin-bottom: var(--space-xl);
  padding: var(--space-2xs);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-lg);
}

.wizard-step {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-sm);
  padding: var(--space-sm) var(--space-md);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-secondary);
  background: transparent;
  cursor: default;
  transition:
    background 0.2s ease,
    color 0.2s ease,
    box-shadow 0.2s ease;
}

.wizard-step-label-only {
  font-size: var(--text-sm);
}

/* 已完成：可点击回退 */
.wizard-step.completed {
  color: var(--color-primary);
  cursor: pointer;
}

.wizard-step.completed:hover {
  background: var(--color-primary-subtle);
}

/* 当前步骤 */
.wizard-step.active {
  background: var(--color-primary-light);
  color: var(--color-primary);
  box-shadow: inset 0 0 0 1px var(--color-primary-lighter);
}

.step-number {
  flex: none;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  font-variant-numeric: tabular-nums;
  /* 未完成：空心，靠边框与背景区分 */
  color: var(--color-text-secondary);
  background: var(--color-bg-primary);
  border: 1.5px solid var(--color-border);
  transition:
    background 0.2s ease,
    border-color 0.2s ease,
    color 0.2s ease;
}

.wizard-step.completed .step-number {
  background: var(--color-primary-lighter);
  border-color: var(--color-primary-lighter);
  color: var(--color-primary);
}

.wizard-step.active .step-number {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: #fff;
}

.step-check {
  width: 12px;
  height: 12px;
}

.step-label {
  white-space: nowrap;
}

/* 窄屏隐藏文字标签，只留圆形序号，避免步骤条被压扁 */
@media (max-width: 640px) {
  .step-label {
    display: none;
  }
}
</style>
