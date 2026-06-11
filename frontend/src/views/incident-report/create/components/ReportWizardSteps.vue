<template>
  <div class="wizard-steps">
    <div
      v-for="(step, index) in steps"
      :key="step.key"
      :class="[
        'wizard-step',
        { active: currentStep === index, completed: currentStep > index },
      ]"
      @click="currentStep > index && $emit('go-to-step', index)"
    >
      <span class="step-number">{{ index + 1 }}</span>
      <span class="step-label">{{ step.label }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  steps: { key: string; label: string }[];
  currentStep: number;
}>();

defineEmits<{
  (e: 'go-to-step', index: number): void;
}>();
</script>

<style scoped>
.wizard-steps {
  display: flex;
  gap: 4px;
  margin-bottom: 24px;
  padding: 8px;
  background: var(--color-bg-secondary);
  border-radius: var(--radius-sm);
}

.wizard-step {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-xs);
  padding: var(--space-xs) var(--space-sm);
  border-radius: var(--radius-sm);
  font-size: 13px;
  color: var(--color-text-secondary);
  cursor: default;
  transition: all 0.2s;
}

.wizard-step.active {
  background: var(--color-primary);
  color: white;
}

.wizard-step.completed {
  color: var(--color-success);
  cursor: pointer;
}

.step-number {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  background: var(--color-bg-tertiary, #e5e7eb);
}

.wizard-step.active .step-number {
  background: rgba(255, 255, 255, 0.2);
}
</style>
