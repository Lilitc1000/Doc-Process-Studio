<template>
  <input v-bind="$attrs" class="base-input" />
</template>

<script setup lang="ts">
defineOptions({
  inheritAttrs: false,
});
</script>

<style scoped>
.base-input {
  width: 100%;
  min-height: 40px;
  padding: 0.62rem 0.72rem;
  border-radius: 12px;
  border: 1px solid #dbe3ee;
  background: #fff;
  color: inherit;
  font: inherit;
  line-height: 1.45;
  transition:
    border-color 0.2s ease,
    box-shadow 0.2s ease,
    background-color 0.2s ease;
}

.base-input:focus {
  outline: none;
  border-color: #93c5fd;
  box-shadow: 0 0 0 4px rgba(147, 197, 253, 0.35);
}

.base-input.invalid {
  border-color: #ef4444;
  background: #fff8f8;
}

.base-input:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}
</style>
