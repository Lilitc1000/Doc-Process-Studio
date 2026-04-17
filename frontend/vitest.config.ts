import { defineConfig } from 'vitest/config';
import vue from '@vitejs/plugin-vue';
import { createPinia } from 'pinia';

const vuePlugin = vue() as never;

export default defineConfig({
  plugins: [vuePlugin],
  test: {
    environment: 'happy-dom',
    include: ['tests/**/*.test.ts'],
    setupFiles: ['./tests/setup.ts'],
  },
});
