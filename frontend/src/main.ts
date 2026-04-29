import { createApp } from 'vue';
import { createPinia } from 'pinia';
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate';
import router from './router';
import safeHtml from './directives/safe-html';
import App from './App.vue';
import './styles/base.css';
import './styles/transitions.css';

const pinia = createPinia();
pinia.use(piniaPluginPersistedstate);

const app = createApp(App);
app.use(pinia);
app.use(router);
app.directive('safe-html', safeHtml);
app.mount('#app');
