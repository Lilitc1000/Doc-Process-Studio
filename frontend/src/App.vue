<template>
  <main class="app">
    <h1>{{ title }}</h1>
    <p>后端健康检查：<code>/health</code></p>
  </main>
</template>

<script setup lang="ts">
const title = 'Hello from Vue3 + Vite';
</script>

<style scoped>
.app {
  margin: 2rem;
  font-family:
    system-ui,
    -apple-system,
    BlinkMacSystemFont,
    'Segoe UI',
    sans-serif;
}
</style>
