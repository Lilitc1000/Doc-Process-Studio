<template>
  <div class="not-found-view">
    <div class="not-found-content">
      <h1 class="not-found-code">404</h1>
      <p class="not-found-message">页面不存在</p>
      <base-button variant="primary" @click="router.push('/')">
        返回首页
      </base-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router';
import BaseButton from '../components/base/BaseButton.vue';

const router = useRouter();
</script>

<style scoped>
.not-found-view {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 2rem;
}

.not-found-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.not-found-code {
  font-size: 6rem;
  font-weight: 700;
  color: var(--color-text-secondary, #6b7280);
  line-height: 1;
  margin: 0;
}

.not-found-message {
  font-size: 1.25rem;
  color: var(--color-text-tertiary, #9ca3af);
  margin: 0;
}
</style>
