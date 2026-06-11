<template>
  <section class="not-found-view">
    <div class="not-found-content">
      <h1 class="not-found-code">404</h1>
      <p class="not-found-message">页面不存在</p>
      <base-button variant="primary" @click="router.push('/')">
        返回首页
      </base-button>
    </div>
  </section>
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
  padding: var(--space-2xl);
  background:
    radial-gradient(circle at 8% 12%, rgba(37, 99, 235, 0.06), transparent 42%),
    radial-gradient(
      circle at 88% 80%,
      rgba(14, 165, 233, 0.04),
      transparent 38%
    ),
    linear-gradient(180deg, #f8fafc 0%, var(--color-bg-page) 100%);
}

.not-found-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-lg);
  padding: var(--space-3xl) var(--space-2xl);
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-card), var(--shadow-inset);
  backdrop-filter: blur(8px);
}

.not-found-code {
  font-size: 5rem;
  font-weight: var(--font-extrabold);
  color: var(--color-primary-lighter);
  line-height: 1;
  margin: 0;
  letter-spacing: -0.03em;
}

.not-found-message {
  font-size: var(--text-lg);
  color: var(--color-text-secondary);
  margin: 0;
}
</style>
