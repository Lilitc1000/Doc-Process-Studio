<template>
  <div class="password-input-wrapper">
    <BaseInput
      ref="inputRef"
      :model-value="modelValue"
      :type="isVisible ? 'text' : 'password'"
      class="password-input-field"
      v-bind="$attrs"
      @update:model-value="$emit('update:modelValue', $event)"
    />
    <BaseButton
      type="button"
      variant="ghost"
      size="sm"
      class="password-toggle-btn"
      tabindex="-1"
      @click="isVisible = !isVisible"
    >
      <svg
        v-if="!isVisible"
        viewBox="0 0 24 24"
        class="password-toggle-icon"
        aria-hidden="true"
      >
        <path
          d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"
          fill="none"
          stroke="currentColor"
          stroke-width="1.8"
        />
        <circle
          cx="12"
          cy="12"
          r="3"
          fill="none"
          stroke="currentColor"
          stroke-width="1.8"
        />
      </svg>
      <svg
        v-else
        viewBox="0 0 24 24"
        class="password-toggle-icon"
        aria-hidden="true"
      >
        <path
          d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.8"
          stroke-linecap="round"
        />
        <line
          x1="1"
          y1="1"
          x2="23"
          y2="23"
          stroke="currentColor"
          stroke-width="1.8"
          stroke-linecap="round"
        />
      </svg>
    </BaseButton>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import BaseButton from './BaseButton.vue';
import BaseInput from './BaseInput.vue';

defineOptions({
  inheritAttrs: false,
});

defineProps<{
  modelValue?: string;
}>();

defineEmits<{
  (e: 'update:modelValue', value: string): void;
}>();

const isVisible = ref(false);
const inputRef = ref<InstanceType<typeof BaseInput> | null>(null);
</script>

<style scoped>
.password-input-wrapper {
  position: relative;
  width: 100%;
}

.password-input-field {
  padding-right: 2.5rem;
}

.password-toggle-btn {
  position: absolute;
  right: 0.35rem;
  top: 50%;
  transform: translateY(-50%);
  min-height: 0 !important;
  min-width: 0 !important;
  width: 2rem;
  height: 2rem;
  padding: 0 !important;
  border: none !important;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.password-toggle-icon {
  width: 1.1rem;
  height: 1.1rem;
}
</style>
