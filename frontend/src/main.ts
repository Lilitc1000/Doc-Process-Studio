import { createApp } from 'vue';
import { createPinia } from 'pinia';
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate';
import router from './router';
import { safeHtml, logger } from '@shared';
import App from './App.vue';
import './styles/base.css';
import './styles/transitions.css';

window.addEventListener('unhandledrejection', (event) => {
  logger.error('未捕获的 Promise 异常', {
    context: 'global',
    error: event.reason,
  });
});

const pinia = createPinia();
pinia.use(piniaPluginPersistedstate);

const app = createApp(App);

app.config.errorHandler = (err, instance, info) => {
  logger.error('Vue 组件错误', {
    context: 'vue',
    error: err,
    component: instance?.$options?.name ?? instance?.$options?.__name,
    info,
  });
};

app.use(pinia);
app.use(router);
app.directive('safe-html', safeHtml);
app.mount('#app');
