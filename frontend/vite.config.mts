import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

export default defineConfig({
  plugins: [vue()],
  resolve: {
    extensions: ['.mjs', '.js', '.ts', '.vue']
  },
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
});
